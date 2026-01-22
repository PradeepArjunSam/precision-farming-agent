from typing import Dict, Any, List, Optional
import json
import os
import random
from pydantic import BaseModel, Field
try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

from ..tools.base import BaseTool

# --- Output Schema ---
class AgronomyRecipe(BaseModel):
    crop: str = Field(..., description="Name of the crop")
    growth_stage: str = Field(..., description="Stage of growth (e.g., Seedling, Vegetative)")
    recommended_actions: List[str] = Field(..., description="List of specific actions to take")
    environmental_parameters: Dict[str, str] = Field(..., description="Key-value pairs of required conditions (e.g., 'Temp': '20-25C')")
    source_citations: List[str] = Field(..., description="List of sources used")
    confidence_score: float = Field(..., description="Confidence from 0.0 to 1.0")

class AgentRuntime:
    def __init__(self, tools: list[BaseTool], model_path: str = None):
        self.tools = {tool.name: tool for tool in tools}
        
        # Load golden examples for dynamic few-shot prompting
        examples_path = os.path.join(os.path.dirname(__file__), "..", "data", "golden_examples.json")
        try:
            with open(examples_path, 'r') as f:
                self.golden_examples = json.load(f)["examples"]
            print(f"Loaded {len(self.golden_examples)} golden examples for few-shot prompting")
        except FileNotFoundError:
            print(f"Warning: Golden examples not found at {examples_path}, using default example")
            self.golden_examples = []
        
        # Initialize HuggingFace Client
        print("Initializing HuggingFace Inference Client...")
        
        # Try to get token from env, otherwise fail later or ask
        self.token = os.environ.get("HF_TOKEN")
        
        if not self.token:
            print("[!] HF_TOKEN environment variable not set.")
            # We will handle this by checking in execute() or just letting it fail with a clear message
        else:
            print("[OK] HF_TOKEN found.")

        if InferenceClient:
            self.client = InferenceClient(token=self.token)
        else:
            raise RuntimeError("huggingface_hub is not installed. Please run `pip install huggingface_hub`")

    def _select_cross_domain_example(self, user_query: str) -> Dict[str, Any]:
        """
        Select a golden example from a DIFFERENT crop than mentioned in the query.
        This prevents the model from copying facts while learning the output format.
        """
        if not self.golden_examples:
            # Fallback default example
            return {
                "crop": "Tomato",
                "growth_stage": "Seedling",
                "recommended_actions": ["Provide 14-16 hours of light", "Keep soil moist"],
                "environmental_parameters": {"Light": "14-16h", "Temp": "20-25C"},
                "source_citations": ["fao.org/tomato"],
                "confidence_score": 0.95
            }
        
        # Extract crop names from query (simple keyword matching)
        query_lower = user_query.lower()
        mentioned_crops = [ex["crop"].lower() for ex in self.golden_examples if ex["crop"].lower() in query_lower]
        
        # Filter examples from different crops
        cross_domain_examples = [
            ex for ex in self.golden_examples 
            if ex["crop"].lower() not in mentioned_crops
        ]
        
        # If all crops are mentioned (unlikely), just pick randomly
        if not cross_domain_examples:
            cross_domain_examples = self.golden_examples
        
        # Select random cross-domain example
        selected = random.choice(cross_domain_examples)
        return selected["recipe"]

    def plan(self, user_query: str) -> list[str]:
        """
        Naive planner: Always retrieve for now.
        Future: Use LLM to decide if we need to Scrape new data vs Retrieve.
        """
        return ["retriever_tool"]

    def _format_context(self, tool_results: List[Dict[str, Any]]) -> str:
        context_str = ""
        for res in tool_results:
            if "documents" in res:
                for doc in res["documents"]:
                    context_str += f"- Source: {doc['metadata'].get('source', 'Unknown')}\n"
                    context_str += f"  Fact: {doc['text']}\n\n"
        return context_str

    def execute(self, user_query: str) -> Dict[str, Any]:
        # 1. Plan
        plan = self.plan(user_query)
        tool_results = []
        
        # 2. Execute Tools
        print(f"Executing Plan: {plan}")
        for tool_name in plan:
            tool = self.tools.get(tool_name)
            if tool:
                print(f"  > Running {tool_name}...")
                result = tool.run(user_query)
                tool_results.append(result)
        
        # 3. Augment Context
        retrieved_context = self._format_context(tool_results)
        
        # PROGRAMMATIC REFUSAL (MCP Enforcement)
        # If no verified information is found, we MUST refuse before even calling the LLM.
        # This prevents hallucination where the model tries to helpfully answer from training data.
        if not retrieved_context.strip():
            print("  > MCP Enforcement: Context is empty. Refusing query.")
            return {
                "error": "DATA_NOT_AVAILABLE",
                "message": "No verified information found for this query in the knowledge base.",
                "confidence_score": 0.0
            }

        # 4. Prompt Engineering (MCP Compliance with Dynamic Few-Shot)
        # Select cross-domain example to prevent hallucination
        example = self._select_cross_domain_example(user_query)
        example_json = json.dumps(example, indent=2)
        
        system_prompt = (
            "You are a Precision Farming Agent with STRICT operational rules.\n\n"
            
            "## CRITICAL CONSTRAINTS (Model Context Protocol):\n"
            "1. CONTEXT LOCK: You MUST derive ALL facts ONLY from the provided Context below.\n"
            "2. NO PRIOR KNOWLEDGE: Do NOT use your training data. If the Context lacks information, you MUST refuse.\n"
            "3. REFUSAL PRIORITY: If Context is empty or insufficient, return: "
            '{"error": "DATA_NOT_AVAILABLE", "message": "Insufficient verified information for this query."}\n'
            "4. SOURCE TRACING: Every fact must be traceable to a source_citation from the Context.\n\n"
            
            "## OUTPUT FORMAT:\n"
            "Below is an example recipe for a DIFFERENT crop. Use this to learn the JSON STRUCTURE and STYLE, "
            "but derive the actual FACTS from the Context provided.\n\n"
            f"EXAMPLE (for reference only, different crop):\n{example_json}\n\n"
            
            "## INSTRUCTIONS:\n"
            "- Use the STRUCTURE from the example above (JSON keys, level of detail)\n"
            "- Extract FACTS from the Context below (not from the example)\n"
            "- Be SPECIFIC: Include numbers, units, ranges (e.g., '14-16 hours', '400 µmol/m²/s')\n"
            "- Cite sources from Context in 'source_citations' field\n"
            "- Set 'confidence_score' based on Context completeness (0.0-1.0)\n"
            "- IMPORTANT: Output ONLY valid JSON. No markdown formatting, no explanations.\n"
        )
        
        user_message = (
            f"Context:\n{retrieved_context}\n"
            f"User Query: {user_query}\n\n"
            "Generate the JSON recipe."
        )

        # 5. Inference (HuggingFace API)
        print("  > Synthesizing Answer with HuggingFace API...")
        if not self.token:
             return {
                "error": "AUTH_REQUIRED",
                "message": "HuggingFace Token (HF_TOKEN) is missing. Please provide it."
            }

        try:
            # We use Mistral-7B-Instruct-v0.2 as the default free model
            response = self.client.chat_completion(
                model="mistralai/Mistral-7B-Instruct-v0.2", 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.0,
                max_tokens=1024,
                response_format={"type": "json_object"} # Try to enforce JSON
            )
            content = response.choices[0].message.content
        except Exception as e:
            print(f"  > Error during inference: {e}")
            return {
                "error": "INFERENCE_FAILED",
                "details": str(e)
            }
        
        # 6. Schema Validation
        try:
            # Clean up potential markdown code blocks if the model adds them
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            data = json.loads(content)
            recipe = AgronomyRecipe(**data)
            return recipe.model_dump()
        except Exception as e:
            return {
                "error": "SCHEMA_VIOLATION",
                "raw_output": content,
                "details": str(e)
            }
