"""
End-to-End Integration Test for Precision Farming Agent
Tests the complete flow: Query -> Retrieval -> LLM -> JSON Validation
"""
import os
# Disable TensorFlow to avoid Keras 3 compatibility issues
os.environ['USE_TF'] = '0'
os.environ['USE_TORCH'] = '1'
# Set HF Token provided by user (Ensure this is set in your environment)
# os.environ['HF_TOKEN'] = "your_token_here"

import sys
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.core import AgentRuntime
from src.tools.scraper import ScraperTool
from src.tools.retriever import RetrieverTool

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_query(agent, query, test_name):
    """Test a single query and validate the response"""
    print_section(f"TEST: {test_name}")
    print(f"Query: {query}\n")
    
    try:
        result = agent.execute(query)
        
        # Check if error response
        if "error" in result:
            print(f"[X] REFUSAL: {result.get('message', 'Unknown error')}")
            return False
        
        # Validate schema compliance
        required_fields = ["crop", "growth_stage", "recommended_actions", 
                          "environmental_parameters", "source_citations", "confidence_score"]
        
        missing_fields = [field for field in required_fields if field not in result]
        if missing_fields:
            print(f"[X] SCHEMA VIOLATION: Missing fields: {missing_fields}")
            return False
        
        # Check for specificity (not generic)
        actions = result.get("recommended_actions", [])
        if not actions:
            print("[!] WARNING: No recommended actions provided")
        else:
            # Check if actions contain numbers (indicator of specificity)
            has_numbers = any(any(char.isdigit() for char in action) for action in actions)
            if not has_numbers:
                print("[!] WARNING: Actions may be too generic (no numerical values)")
        
        # Validate confidence score
        confidence = result.get("confidence_score", 0)
        if not (0 <= confidence <= 1):
            print(f"[!] WARNING: Confidence score out of range: {confidence}")
        
        # Display results
        print("[OK] VALID RESPONSE\n")
        print(json.dumps(result, indent=2))
        
        # Quality metrics
        print("\n--- Quality Metrics ---")
        print(f"Actions Count: {len(actions)}")
        print(f"Parameters Count: {len(result.get('environmental_parameters', {}))}")
        print(f"Sources Count: {len(result.get('source_citations', []))}")
        print(f"Confidence Score: {confidence}")
        
        return True
        
    except Exception as e:
        print(f"[X] EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print_section("INITIALIZING PRECISION FARMING AGENT")
    
    # Initialize Tools
    print("Setting up tools...")
    scraper = ScraperTool(whitelist=["fao.org", "usda.gov"])
    retriever = RetrieverTool(db_path="D:\\precision_farming\\data\\chroma")
    
    # Initialize Agent
    print("Loading agent runtime...")
    agent = AgentRuntime(
        tools=[scraper, retriever]
    )
    
    print("\n[OK] Agent initialized successfully!")
    
    # Test Suite
    test_cases = [
        {
            "query": "What are the light requirements for tomato seedlings?",
            "name": "Tomato Light Requirements (Should have data)"
        },
        {
            "query": "How should I water wheat during the tillering stage?",
            "name": "Wheat Irrigation (Should have data)"
        },
        {
            "query": "What fertilizer does corn need during vegetative growth?",
            "name": "Corn Fertilization (Should have data)"
        },
        {
            "query": "How do I grow purple alien vegetables on Mars?",
            "name": "Invalid Query (Should refuse - no data)"
        }
    ]
    
    # Run tests
    results = []
    for test_case in test_cases:
        success = test_query(agent, test_case["query"], test_case["name"])
        results.append({
            "test": test_case["name"],
            "passed": success
        })
        input("\nPress Enter to continue to next test...")
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    
    for result in results:
        status = "[OK] PASS" if result["passed"] else "[X] FAIL"
        print(f"{status}: {result['test']}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    # Final validation
    print_section("VALIDATION CHECKLIST")
    print("[*] Schema Compliance: Check if all responses have required fields")
    print("[*] MCP Enforcement: Check if invalid queries are refused")
    print("[*] Specificity: Check if actions contain numerical values")
    print("[*] Source Citations: Check if sources are provided")
    print("[*] Cross-Domain Examples: Check if different crop examples are used")

if __name__ == "__main__":
    main()
