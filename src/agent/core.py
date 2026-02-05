from typing import Dict, Any, List, Optional
import json
import os
import random
from pydantic import BaseModel, Field
try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

from ..tools.base import BaseTool

# --- Output Schema ---
class Quantity(BaseModel):
    unit: str = Field(..., description="Unit of measurement (e.g., 'lbs/acre', 'kg/ha', 'mm')")
    value: Optional[float] = Field(None, description="Numerical value")

class Ingredient(BaseModel):
    name: str = Field(..., description="Name of input (e.g., 'Corn Nitrogen Application')")
    quantity: Quantity = Field(..., description="Amount required")
    stage: str = Field(..., description="Growth stage for application")

class Instruction(BaseModel):
    step: int = Field(..., description="Step number")
    description: str = Field(..., description="Detailed instruction")

class Task(BaseModel):
    task: str = Field(..., description="Short task name")
    ingredient: Optional[str] = Field(None, description="Name of related ingredient if any")

class TimetableEntry(BaseModel):
    period: str = Field(..., description="Time period (e.g., 'Day 1', 'Week 4')")
    tasks: List[Task] = Field(..., description="List of tasks for this period")

class Recipe(BaseModel):
    name: str = Field(..., description="Descriptive title of the recipe")
    ingredients: List[Ingredient] = Field(..., description="List of inputs needed")
    instructions: List[Instruction] = Field(..., description="Step-by-step guide")
    timetable: List[TimetableEntry] = Field(..., description="Chronological schedule")

class AgronomyRecipe(BaseModel):
    recipe: Recipe = Field(..., description="The complete agronomy recipe")

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
        
        self.model_path = model_path
        self.llm = None
        
        if self.model_path:
            print(f"Loading local model from {self.model_path}...")
            if Llama:
                self.llm = Llama(
                    model_path=self.model_path,
                    n_ctx=4096,
                    n_threads=4, # Adjust based on CPU
                    verbose=False
                )
                print("[OK] Local model loaded.")
            else:
                print("[!] llama-cpp-python not installed. Cannot load local model.")
        
        # Initialize HuggingFace Client (Fallback)
        print("Initializing HuggingFace Inference Client (Fallback)...")
        
        # Try to get token from env, otherwise fail later or ask
        self.token = os.environ.get("HF_TOKEN")
        
        if self.token:
             if InferenceClient:
                self.client = InferenceClient(token=self.token)
             else:
                print("huggingface_hub is not installed.")
        else:
             print("[!] HF_TOKEN environment variable not set. Will rely on local model if available.")

    def _select_cross_domain_example(self, user_query: str) -> Dict[str, Any]:
        """
        Select a golden example from a DIFFERENT crop than mentioned in the query.
        This prevents the model from copying facts while learning the output format.
        """
        if not self.golden_examples:
            # Fallback default example
            return {
                "recipe": {
                    "name": "Tomato Seedling Care Schedule",
                    "ingredients": [
                        {
                            "name": "Water",
                            "quantity": {"unit": "mm/week", "value": 25},
                            "stage": "Seedling"
                        }
                    ],
                    "instructions": [
                        {"step": 1, "description": "Keep soil consistently moist but not waterlogged."}
                    ],
                    "timetable": [
                        {
                            "period": "Week 1",
                            "tasks": [{"task": "Water daily", "ingredient": "Water"}]
                        }
                    ]
                }
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
        Dynamically plan based on available tools.
        If we have search, use it.
        """
        plan = []
        if "search_tool" in self.tools:
            plan.append("search_tool")
        if "retriever_tool" in self.tools:
            plan.append("retriever_tool")
        return plan

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
            "- EXTRACT FACTS from the Context below.\n"
            "- 'ingredients': List all inputs (fertilizer, water) with specific QUANTITY and UNIT.\n"
            "- 'instructions': Step-by-step application guide.\n"
            "- 'timetable': Link tasks to specific periods (Day X, Week Y).\n"
            "- IMPORTANT: Output ONLY valid JSON matching the Example structure.\n"
        )
        
        user_message = (
            f"Context:\n{retrieved_context}\n"
            f"User Query: {user_query}\n\n"
            "Generate the detailed JSON recipe."
        )

        # 5. Inference
        print("  > Synthesizing Answer...")
        
        try:
            # 1. Try HuggingFace API First
            if self.token and self.client:
                print("  > Using HuggingFace API...")
                try:
                    response = self.client.chat_completion(
                        model="microsoft/Phi-3-mini-4k-instruct", 
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message}
                        ],
                        temperature=0.0,
                        max_tokens=1024,
                        response_format={"type": "json_object"} 
                    )
                    content = response.choices[0].message.content
                except Exception as e:
                    print(f"  > HF API Failed: {e}")
                    if not self.llm:
                        raise e # Re-raise if no fallback
                    print("  > Falling back to Local Model...")
                    content = None # Signal to try fallback

            # 2. Key Fallback: Local Model
            if (not self.token or not self.client or content is None) and self.llm:
                print("  > Using Local Model (Llama CPP)...")
                response = self.llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.0,
                    # max_tokens=1024, # LlamaCPP uses max_tokens differently or defaults
                    response_format={"type": "json_object"}
                )
                content = response["choices"][0]["message"]["content"]
            
            elif (not self.token or not self.client) and not self.llm:
                 return {
                    "error": "NO_INFERENCE_ENGINE",
                    "message": "Neither HuggingFace Token nor Local Model available."
                }
        except Exception as e:
            print(f"  > Error during inference: {e}")
            return {
                "error": "INFERENCE_FAILED",
                "details": str(e)
            }
            
        # Skip original Hf logic since we handled it above
        if False:
             pass

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
            # Fallback: Return raw output if schema validation fails
            # This ensures the user sees the answer even if the model didn't follow strict JSON
            print(f"  > Schema Validation Failed: {e}")
            try:
                # Try to return it as a dict if it was valid JSON but wrong schema
                return json.loads(content)
            except:
                # Return as raw text wrapper
                return {
                    "raw_answer": content,
                    "validation_error": str(e)
                }
