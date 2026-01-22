# Precision Farming Agent - Quick Reference

## 🚀 Quick Start

### Run the Agent
```bash
python src/main.py "What are the light requirements for tomato seedlings?"
```

### Run Tests
```bash
# Integration tests
python test_agent.py

# Performance benchmark
python benchmark.py

# Component tests
python test_scraper.py
python test_retriever.py
```

---

## 📁 Project Structure

```
precision_farming/
├── src/
│   ├── agent/
│   │   └── core.py              # Agent runtime with few-shot prompting
│   ├── data/
│   │   └── golden_examples.json # Expert recipe examples
│   ├── tools/
│   │   ├── scraper.py           # Web scraping tool
│   │   └── retriever.py         # ChromaDB retrieval tool
│   └── main.py                  # Entry point
├── test_agent.py                # Integration tests
├── benchmark.py                 # Performance tests
├── TESTING.md                   # Testing guide
└── theory.md                    # Architecture documentation
```

---

## 🎯 Key Features

### 1. Dynamic Few-Shot Prompting
- **5 golden examples** covering different crops
- **Cross-domain selection** prevents hallucination
- **Automatic example injection** based on query

### 2. Model Context Protocol (MCP)
- Context lock: Facts only from retrieved data
- Refusal behavior: Returns error if no data
- Source tracing: All facts cited

### 3. Schema Validation
- Pydantic ensures valid JSON output
- Required fields enforced
- Confidence scoring

---

## 📊 System Prompt Structure

```
## CRITICAL CONSTRAINTS
1. CONTEXT LOCK
2. NO PRIOR KNOWLEDGE
3. REFUSAL PRIORITY
4. SOURCE TRACING

## OUTPUT FORMAT
[Dynamic cross-domain example]

## INSTRUCTIONS
- Use structure from example
- Extract facts from context
- Be specific with numbers/units
```

---

## 🧪 Test Queries

### ✅ Should Succeed
- "What are the light requirements for tomato seedlings?"
- "How should I water wheat during tillering?"
- "What fertilizer does corn need?"

### ❌ Should Refuse
- "How do I grow alien vegetables on Mars?"
- "What is the capital of France?"

---

## ⚙️ Configuration

### Agent Parameters (core.py)
```python
n_ctx=4096      # Context window
n_threads=4     # CPU threads (adjust to your CPU)
temperature=0.0 # Deterministic output
```

### Performance Tuning
- **Faster inference**: Increase `n_threads`, use Q3 quantization
- **Better quality**: Increase `n_ctx`, use Q4/Q5 quantization
- **Lower memory**: Decrease `n_ctx`, use Q3 quantization

---

## 📈 Expected Performance

| Metric | Target |
|--------|--------|
| Initialization | ~20-30s |
| Query Response | ~10-15s |
| Success Rate | >90% |

---

## 🔍 Validation Checklist

- ✅ Schema compliance (all fields present)
- ✅ MCP enforcement (refusal when no data)
- ✅ Output specificity (numbers + units)
- ✅ Source citations included
- ✅ Confidence scores 0.0-1.0

---

## 🐛 Troubleshooting

### Slow Inference
- Check `n_threads` matches CPU cores
- Try Q3 quantization
- Reduce `n_ctx` to 2048

### Generic Answers
- Verify golden examples loaded
- Check ChromaDB has data
- Review system prompt

### Schema Violations
- Update llama-cpp-python
- Check Pydantic version
- Review response_format support

---

## 📚 Documentation

- **TESTING.md** - Comprehensive testing guide
- **theory.md** - Architecture and concepts
- **explanations.md** - Multi-audience explanations
- **walkthrough.md** - Implementation details

---

## 🎓 How Cross-Domain Prompting Works

1. User asks about **Tomato**
2. System detects "Tomato" in query
3. System selects **Corn** example (different crop)
4. LLM learns **structure** from Corn example
5. LLM extracts **facts** from Tomato context
6. Output: Tomato recipe with Corn-level detail

**Result**: Prevents hallucination while ensuring specificity!
