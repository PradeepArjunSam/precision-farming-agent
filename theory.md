# Precision Farming Agent: Theory, Architecture & Retrospective

## 1. High-Level Architecture
The system is designed as a **Single-Crop Agentic RAG (Retrieval Augmented Generation)** system. It does not rely on the LLM's internal training data for facts. Instead, it acts as a reasoning engine that synthesizes strict, retrieved context.

### The Flow
1.  **User Query** ("How much light do tomatoes need?")
2.  **Agent Runtime** (The Brain) receives the query.
3.  **Planner** determines tools needed (e.g., `RetrieverTool`).
4.  **Tool Execution**:
    *   `RetrieverTool` searches the local ChromaDB vector store.
    *   Returns chunks of verified text (e.g., from `fao.org`).
5.  **Context Augmentation**: The verified text is injected into the System Prompt.
6.  **MCP Enforcement**: The prompt enforces strict rules (e.g., "Yield refusal if context is empty").
7.  **LLM Inference**: Mistral 7B (Quantized) generates the answer.
8.  **Schema Validation**: Pydantic ensures the output is valid JSON.

## 2. Core Concepts & Code

### A. The Agent Runtime (The "Brain")
The Agent is not just the LLM. It is the control loop that manages tools and context.

**Code Example (`src/agent/core.py`):**
```python
def execute(self, query):
    # 1. Plan
    tools_to_use = self.plan(query) 
    
    # 2. Retrieve Context (RAG)
    context = ""
    for tool in tools_to_use:
        results = tool.run(query)
        context += format_results(results)

    # 3. Dynamic Few-Shot Injection (The "Tuning")
    # We inject a perfect JSON example to guide the model's format
    system_prompt = f"Use this format: {CROSS_DOMAIN_EXAMPLE}"
    
    # 4. Generate with Strict Schema
    response = self.llm.create_chat_completion(
        messages=[{"role": "user", "content": f"Context: {context}\nQuery: {query}"}],
        response_format={"type": "json_object", "schema": AgronomyRecipe.schema()}
    )
```

### B. Model Context Protocol (MCP)
MCP is the set of rules that "locks" the LLM. We don't just ask the model to "be helpful". We bind it with strict constraints.

**The Constraints:**
1.  **Context Lock**: "Answer ONLY using the provided Context."
2.  **Refusal**: "If context is empty, return 'DATA_NOT_AVAILABLE'."
3.  **Schema Lock**: output **must** match the `AgronomyRecipe` JSON structure.

### C. Prompt Fine-Tuning (Cross-Domain Few-Shot)
Instead of training the model (expensive), we "tune" the prompt.
To prevent **Hallucination** (copying numbers from the example), we use **Cross-Domain Examples**.

*   **User Query**: "Tomato Light Requirements"
*   **Injected Example**: A perfect recipe for *Corn*.
*   **Result**: The model sees the *structure* of the Corn recipe (JSON keys) but knows the *content* (Corn facts) doesn't match the query (Tomato). It is forced to look at the **Retrieved Context** for the actual numbers.

## 3. Challenges & Solutions (Retrospective)

### Issue 1: Hardware Constraints (No GPU)
*   **Problem**: The user has a powerful CPU but no NVIDIA GPU. Traditional Fine-Tuning (LoRA) was impossible.
*   **Solution**: We switched to **Quantized Inference** (`llama.cpp` / GGUF format) which runs efficiently on CPU. We replaced "Weight Fine-Tuning" with "Prompt Fine-Tuning" (Few-Shot Learning).

### Issue 2: "Generic" Answers
*   **Problem**: The base Mistral model produced valid JSON but generic content (e.g., "Provide adequate light").
*   **Solution**: We implemented **Schema Enforcement** (via `response_format` in `llama-cpp-python`) and are adding **Dynamic Few-Shot Examples** to force it to be specific (e.g., "Provide 14-16h light").

### Issue 3: Hallucination Risk
*   **Problem**: Providing an example answer might cause the model to lazily copy-paste the numbers.
*   **Solution**: **Cross-Domain Prompting**. Giving a "Corn" example for a "Tomato" question forces the model to decouple the *Format* from the *Facts*.




# Theory: Prompt Fine-Tuning (In-Context Learning) vs. Model Fine-Tuning

## 1. The Problem
We want the Agent to output **highly specific, expert-level agronomy recipes**.
Currently, the model produces valid JSON, but the content can be generic (e.g., "Provide light" vs "Provide 14-16h light at 400 µmol/m²/s").

## 2. Approach A: Traditional Fine-Tuning (Weight Updates)
This involves training the neural network to permanently change its internal weights.
- **Process**: Feed thousands of (Question, Ideal Answer) pairs. Run backpropagation.
- **Hardware Requirement**: High-VRAM GPUs (e.g., NVIDIA A100/H100 or RTX 4090).
- **Cost**: High computational cost.
- **Status**: **Impossible** on the current machine (CPU only).

## 3. Approach B: Prompt Fine-Tuning (In-Context Learning)
This involves providing the "pattern" of a perfect answer inside the prompt itself at runtime.
- **Process**: 
    1. Create a "Golden Dataset" of 5-10 perfect expert examples.
    2. When the user asks a question (e.g., about "Watering"), the Agent finds the most similar "Golden Example" (e.g., a perfect answering about "Irrigation").
    3. The Agent inserts this example into the System Prompt: *"Answer the user's question following the style of this example: [Golden Example]"*.
- **Mechanism**: LLMs are "few-shot learners". They are excellent at pattern matching. If they see one perfect example in the context, they mimic the tone, structure, and depth immediately.
- **Hardware Requirement**: None (Works on CPU).
- **Effectiveness**: For style and format alignment, this is often 90% as effective as full fine-tuning.

## 4. Our Implementation Plan
We will implement **Dynamic Few-Shot Prompting**:
1.  **Store**: Create a JSON file `src/data/golden_examples.json`.
2.  **Retrieve**: When `agent.execute(query)` runs, we check the query topic.
3.  **Inject**: We dynamically replace the `EXAMPLE OUTPUT` in the system prompt with the most relevant Golden Example.

## 5. The Risk: Will it Hallucinate?
**User Concern**: "Won't giving a made-up example cause the model to just make up similar numbers?"

**The Danger**: Yes, if not careful. An LLM might see a "perfect example" with specific numbers (e.g., "Water 5L per plant") and lazily copy those numbers even if they don't apply to the user's specific context.

**The Mitigation**:
1.  **Strict Separation**: The System Prompt must explicitly state: *"Use the **format** of the example, but derive **facts** ONLY from the provided Context."*
2.  **Generic Examples**: We can use examples about a *different* crop (e.g., "Example for Wheat" when asking about "Tomato") to prevent copy-pasting. The model learns the *structure* (JSON fields) but cannot copy the *content*.
3.  **Refusal Priority**: The instruction "Refuse if Context is empty" must take precedence over "Follow the example".

## 6. Implementation Strategy
We will use **Cross-Domain Examples**:
- If User asks about **Tomato**, we show a Golden Example for **Corn**.
- This forces the model to use the *Tomato Context* (Retrieved) to fill the structure, because copying "Corn" facts would be obviously wrong.


