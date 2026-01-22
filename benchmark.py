"""
Performance Benchmark Script for Precision Farming Agent
Measures inference time, retrieval speed, and overall response latency
"""
import sys
import os
import time
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.core import AgentRuntime
from src.tools.scraper import ScraperTool
from src.tools.retriever import RetrieverTool

def benchmark_agent():
    """Run performance benchmarks on the agent"""
    print("="*70)
    print("  PRECISION FARMING AGENT - PERFORMANCE BENCHMARK")
    print("="*70)
    
    # Initialize
    print("\n[1/4] Initializing agent...")
    start_init = time.time()
    
    scraper = ScraperTool(whitelist=["fao.org", "usda.gov"])
    retriever = RetrieverTool(db_path="D:\\precision_farming\\data\\chroma")
    agent = AgentRuntime(
        tools=[scraper, retriever],
        model_path="D:\\precision_farming\\models\\mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    )
    
    init_time = time.time() - start_init
    print(f"✓ Initialization time: {init_time:.2f}s")
    
    # Benchmark queries
    test_queries = [
        "What are the light requirements for tomato seedlings?",
        "How should I irrigate wheat during tillering?",
        "What fertilizer does corn need?"
    ]
    
    print(f"\n[2/4] Running {len(test_queries)} benchmark queries...")
    
    timings = []
    for i, query in enumerate(test_queries, 1):
        print(f"\n  Query {i}/{len(test_queries)}: {query[:50]}...")
        
        start = time.time()
        result = agent.execute(query)
        elapsed = time.time() - start
        
        timings.append({
            "query": query,
            "time": elapsed,
            "success": "error" not in result
        })
        
        print(f"  ⏱️  Time: {elapsed:.2f}s | Status: {'✓' if timings[-1]['success'] else '✗'}")
    
    # Calculate statistics
    print("\n[3/4] Calculating statistics...")
    successful_times = [t["time"] for t in timings if t["success"]]
    
    if successful_times:
        avg_time = sum(successful_times) / len(successful_times)
        min_time = min(successful_times)
        max_time = max(successful_times)
        
        print(f"\n  Average response time: {avg_time:.2f}s")
        print(f"  Fastest response: {min_time:.2f}s")
        print(f"  Slowest response: {max_time:.2f}s")
    
    # Performance report
    print("\n[4/4] Performance Report")
    print("="*70)
    print(f"Model Load Time: {init_time:.2f}s")
    print(f"Average Query Time: {avg_time:.2f}s" if successful_times else "N/A")
    print(f"Success Rate: {len(successful_times)}/{len(timings)} ({len(successful_times)/len(timings)*100:.0f}%)")
    
    # Recommendations
    print("\n📊 Performance Analysis:")
    if avg_time > 15:
        print("  ⚠️  Response time is slow (>15s). Consider:")
        print("     - Increasing n_threads in core.py")
        print("     - Using a smaller quantization (Q3 vs Q4)")
        print("     - Reducing n_ctx if not needed")
    elif avg_time > 10:
        print("  ℹ️  Response time is acceptable for batch processing")
    else:
        print("  ✓ Response time is good for this hardware")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    benchmark_agent()
