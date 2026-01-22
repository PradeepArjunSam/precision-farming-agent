# Precision Farming Agent - Testing & Validation Guide

## Quick Start

### 1. Run Integration Tests
```bash
python test_agent.py
```
Tests the complete agent flow with multiple queries and validates:
- Schema compliance
- MCP enforcement (refusal behavior)
- Output specificity
- Source citations

### 2. Run Performance Benchmark
```bash
python benchmark.py
```
Measures:
- Model initialization time
- Average query response time
- Success rate

### 3. Test Individual Components
```bash
# Test scraper
python test_scraper.py

# Test retriever
python test_retriever.py
```

## Test Queries

### Expected to Succeed (Data Available)
- "What are the light requirements for tomato seedlings?"
- "How should I water wheat during the tillering stage?"
- "What fertilizer does corn need during vegetative growth?"

### Expected to Refuse (No Data)
- "How do I grow purple alien vegetables on Mars?"
- "What is the capital of France?" (non-agricultural)

## Validation Checklist

### ✓ Schema Compliance
All responses must include:
- `crop` (string)
- `growth_stage` (string)
- `recommended_actions` (array of strings)
- `environmental_parameters` (object)
- `source_citations` (array of strings)
- `confidence_score` (float 0.0-1.0)

### ✓ MCP Enforcement
- Agent refuses when context is empty
- No hallucinated facts from model training data
- All facts traceable to retrieved context

### ✓ Output Quality
- Actions contain specific numbers/units (e.g., "14-16 hours", "400 µmol/m²/s")
- Not generic (avoid "provide adequate light")
- Multiple actionable recommendations

### ✓ Cross-Domain Examples
- Check logs to see which golden example was selected
- Should be from a different crop than the query

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Initialization | <30s | One-time cost |
| Query Response | 10-15s | Acceptable for CPU inference |
| Success Rate | >90% | For queries with available data |

## Troubleshooting

### Slow Inference
1. Check `n_threads` in `core.py` (should match CPU cores)
2. Consider reducing `n_ctx` from 4096 to 2048
3. Try Q3 quantization instead of Q4

### Generic Answers
1. Verify golden examples are loaded (check logs)
2. Ensure ChromaDB has sufficient data
3. Check if cross-domain example is being used

### Schema Violations
1. Check if `response_format` is supported by llama-cpp-python version
2. Verify Pydantic schema matches expected output
3. Review system prompt clarity

## Next Steps

After validation:
1. Document any issues found
2. Tune parameters based on benchmark results
3. Add more golden examples for better coverage
4. Consider expanding test suite with edge cases
