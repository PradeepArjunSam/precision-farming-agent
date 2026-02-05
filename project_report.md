# Precision Farming Agent - System Report

## 1. Capabilities
The Precision Farming Agent is a local-first, autonomous AI assistant designed for agronomy planning.

*   **Autonomous Data Collection**:
    *   Uses `duckduckgo-search` to find information on any crop (not limited to pre-trained data).
    *   **Strict Whitelist Enforcement**: Filters searches to trusted domains (e.g., `site:fao.org`, `site:usda.gov`) to ensure data reliability.
*   **Intelligent Synthesis**:
    *   **Local Inference**: Uses `Mistral-7B` (via `llama.cpp`) for privacy and offline capability.
    *   **Detailed Schemas**: Generates highly structured JSON outputs including:
        *   `Ingredients` (Inputs with units)
        *   `Instructions` (Step-by-step guides)
        *   `Timetable` (Chronological schedule of tasks)
*   **Robust Error Handling**:
    *   Includes a fallback mechanism to handle strict JSON validation failures, ensuring the user always receives the raw model output even if the schema is imperfect.
*   **Interface**:
    *   Provides a clean, chat-based web interface using **Streamlit**.

## 2. Limitations
*   **Inference Speed**: Local model inference on CPU (via `llama.cpp`) can be slow (30-60s per query) compared to cloud APIs.
*   **Schema strictness**: Smaller local models (7B parameters) struggle to perfectly adhere to complex nested JSON schemas 100% of the time, occasionally triggering the fallback mechanism.
*   **Search Depth**: The current search tool fetches the top 3 results. For very niche crops, this might effectively produce "no data" if the top results are irrelevant.
*   **Frontend Interactivity**: The Streamlit interface is synchronous; it blocks while the agent is "thinking", offering limited real-time feedback during the scrape-and-search process.

## 3. Improvements
*   **Model Upgrade**: Switch to a quantized `Mixtral-8x7B` or fine-tune a model specifically for JSON function calling to improve schema compliance.
*   **Async Search**: Implement asynchronous web scraping to fetch more results (e.g., top 10) in parallel without slowing down the system.
*   **UI Experience**: Add a "verbose" mode in the UI so users can see the specific sources being scraped in real-time.
*   **PDF/Report Export**: Add a feature to export the generated "Agronomy Recipe" to a formatted PDF or Excel file for field use.
