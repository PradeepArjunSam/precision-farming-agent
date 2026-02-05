import streamlit as st
import sys
import os
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.core import AgentRuntime
from src.tools.scraper import ScraperTool
from src.tools.retriever import RetrieverTool

from src.tools.search import SearchTool

# Config
load_dotenv()
st.set_page_config(page_title="Precision Farming Agent", page_icon="🌾")

# Initialize Agent (Cached to prevent reloading on interaction)
@st.cache_resource
def get_agent():
    print("Initializing Agent Runtime...")
    scraper = ScraperTool(whitelist=["fao.org", "usda.gov"])
    retriever = RetrieverTool(db_path="data/chroma")
    search = SearchTool()
    
    # Use local model as default path (Core will handle priority logic)
    agent = AgentRuntime(
        tools=[scraper, retriever, search],
        model_path="models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    )
    return agent

try:
    agent = get_agent()
except Exception as e:
    st.error(f"Failed to initialize agent: {e}")
    st.stop()

# UI Layout
st.title("🌾 Precision Farming Agent")
st.markdown("Ask about crop requirements, diseases, or fertilizer recommendations.")

# Session State for Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            # Check if content is JSON string to pretty print
            try:
                content_json = json.loads(message["content"])
                st.json(content_json)
            except:
                st.markdown(message["content"])
        else:
            st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("What would you like to know?"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate Response
    with st.chat_message("assistant"):
        with st.status("Thinking...", expanded=True) as status:
            st.write("Processing query...")
            try:
                # Capture standard output to show tool usage (optional hack)
                # For now just run execution
                result = agent.execute(prompt)
                
                status.update(label="Complete!", state="complete", expanded=False)
                
                # Format result
                if isinstance(result, dict):
                    st.json(result)
                    # Convert to string for storage
                    response_str = json.dumps(result, indent=2)

                    # --- VERBOSE LOGS EXPANDER ---
                    with st.expander("Show Research Logs (Verified Sources)"):
                        st.write("The agent checked the following sources:")
                        # If result has source_citations (from schema)
                        if isinstance(result, dict):
                            sources = result.get("recipe", {}).get("source_citations", [])
                            # Or if it's the raw result before parsing
                            if not sources:
                                sources = result.get("source_citations", [])
                            
                            if sources:
                                for s in sources:
                                    st.write(f"- {s}")
                            else:
                                st.write("No external web sources were cited in the final output.")
                else:
                    st.markdown(str(result))
                    response_str = str(result)
                    
                st.session_state.messages.append({"role": "assistant", "content": response_str})
                
            except Exception as e:
                status.update(label="Error", state="error")
                st.error(f"An error occurred: {e}")
