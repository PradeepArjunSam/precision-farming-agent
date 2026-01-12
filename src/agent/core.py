from typing import Dict, Any, List, Optional
import json
from pydantic import BaseModel, Field
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None # Handle missing dependency gracefully for linting

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
    def __init__(self, tools: list[BaseTool], model_path: str):
        self.tools = {tool.name: tool for tool in tools}
        self.model_path = model_path
        print(f"Loading Model from {model_path}...")
        if Llama:
            self.llm = Llama(
                model_path=model_path,
                n_ctx=4096,      # Context window
                n_threads=4,     # CPU threads
                verbose=False
            )
        else:
            raise RuntimeError("llama-cpp-python is not installed.")

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
        
        if not retrieved_context.strip():
            return {
                "error": "DATA_NOT_AVAILABLE",
                "message": "No verified information found for this query."
            }

        # 4. Prompt Engineering (MCP Compliance)
        system_prompt = (
            "You are a Precision Farming Agent. "
            "Your goal is to generate an agronomy recipe based ONLY on the provided Context. "
            "Refuse to answer if the Context is insufficient. "
            "Do not use prior knowledge. "
            "Output must be valid JSON conforming EXACTLY to the schema below. "
            "SCHEMA: {crop: str, growth_stage: str, recommended_actions: [str], environmental_parameters: {key: value}, source_citations: [str], confidence_score: float}\n"
            "EXAMPLE OUTPUT:\n"
            "{\n"
            '  "crop": "Tomato",\n'
            '  "growth_stage": "Seedling",\n'
            '  "recommended_actions": ["Provide 14-16 hours of light", "Keep soil moist"],\n'
            '  "environmental_parameters": {"Light": "14-16h", "Temp": "20-25C"},\n'
            '  "source_citations": ["fao.org/tomato"],\n'
            '  "confidence_score": 0.95\n'
            "}"
        )
        
        user_message = (
            f"Context:\n{retrieved_context}\n"
            f"User Query: {user_query}\n\n"
            "Generate the JSON recipe."
        )

        # 5. Inference
        print("  > Synthesizing Answer with LLM...")
        try:
            response = self.llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.0,
                response_format={
                    "type": "json_object",
                    "schema": AgronomyRecipe.model_json_schema()
                },
                max_tokens=1024
            )
            content = response["choices"][0]["message"]["content"]
        except Exception as e:
            # Fallback if schema arg is not supported by this version runtime
            print(f"  > Warning: Schema enforcement failed ({e}), retrying with grammar/prompt only.")
            response = self.llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
                max_tokens=1024
            )
            content = response["choices"][0]["message"]["content"]
        
        # 6. Schema Validation
        try:
            data = json.loads(content)
            recipe = AgronomyRecipe(**data)
            return recipe.model_dump()
        except Exception as e:
            return {
                "error": "SCHEMA_VIOLATION",
                "raw_output": content,
                "details": str(e)
            }
