# Agent4Compliance - Setup and Usage Guide

## 🚀 Quick Start

### 1. Build Précis Engine

```bash
cd /path/to/precis
dune clean && dune build
```

### 2. Install Python Dependencies

```bash
pip install anthropic streamlit pandas
```

Or use the requirements file:

```bash
# requirements.txt
anthropic>=0.18.0
streamlit>=1.31.0
pandas>=2.0.0
```

```bash
pip install -r requirements.txt
```

### 3. Set Environment Variables

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

## 📖 Usage Guide

### Option 1: Command Line Test Script

**Basic Usage:**
```bash
python experiment_runner.py \
  --query "Can a hospital share patient data with researchers?" \
  --experiment all \
  --regulation HIPAA
```

**Run Specific Experiment:**
```bash
python experiment_runner.py \
  --query "Is consent required for treatment?" \
  --experiment agent4compliance \
  --output results.json
```

**Available Experiments:**
- `baseline_no_context` - Direct LLM
- `baseline_with_context` - LLM + Context
- `rag` - Retrieval + LLM
- `agent4compliance` - Full Pipeline
- `all` - Run all experiments

### Option 2: Streamlit UI

```bash
streamlit run streamlit_app.py
```

Then open http://localhost:8501 in your browser

**Features:**
- Interactive query input
- Visual experiment selection
- Real-time results display
- Side-by-side comparison
- Download results as JSON

### Option 3: Comprehensive Test Suite

**Run All Tests:**
```bash
python test_suite.py \
  --regulations HIPAA GDPR \
  --experiments all \
  --output test_results.json
```

**Quick Test (First 3 queries):**
```bash
python test_suite.py --quick
```

**Test Specific Experiments:**
```bash
python test_suite.py \
  --experiments baseline_no_context agent4compliance \
  --regulations HIPAA
```

## 📊 Output Files

### JSON Results (`results.json`)
```json
{
  "agent4compliance": {
    "experiment": "agent4compliance",
    "query": "Can a hospital...",
    "retrieved_policies": ["HIPAA-164.502-a-1"],
    "logic_formula": "forall hospital...",
    "precis_result": {...},
    "explanation": "Yes, hospitals can...",
    "steps": [...],
    "duration": 3.45
  }
}
```

### CSV Report (`test_results.csv`)
| Query | Category | Experiment | Status | Duration | Answer |
|-------|----------|------------|--------|----------|--------|
| Can... | Disclosure | Agent4Compliance | Success | 3.45 | Yes... |

## 🧪 Experiment Descriptions

### 1. Baseline (No Context)
```
Input: NL Query
  ↓
LLM (No external knowledge)
  ↓
Output: Answer
```

**Command:**
```bash
python experiment_runner.py \
  --query "Your question" \
  --experiment baseline_no_context
```

### 2. Baseline (With Context)
```
Input: NL Query + All Rules
  ↓
LLM (Full rule database)
  ↓
Output: Answer
```

**Command:**
```bash
python experiment_runner.py \
  --query "Your question" \
  --experiment baseline_with_context
```

### 3. RAG (Retrieval Augmented)
```
Input: NL Query
  ↓
Retrieve Relevant Policies (Top-K)
  ↓
LLM (Query + Retrieved policies)
  ↓
Output: Answer
```

**Command:**
```bash
python experiment_runner.py \
  --query "Your question" \
  --experiment rag
```

### 4. Agent4Compliance (Full Pipeline)
```
Input: NL Query
  ↓
Step 1: Retrieve Relevant Policies
  ↓
Step 2: LLM1 - Translate NL → Logic
  ↓
Step 3: Précis - Formal Verification
  ↓
Step 4: LLM2 - Logic → NL Explanation
  ↓
Output: Verified Answer + Citations
```

**Command:**
```bash
python experiment_runner.py \
  --query "Your question" \
  --experiment agent4compliance
```

## 🔧 Advanced Usage

### Custom Policy Database

Modify `data/type_system.txt`, `data/facts.txt`, etc.:

```bash
# Reload policies
./precis reload HIPAA
```

### Custom Précis Path

```bash
python experiment_runner.py \
  --query "Your question" \
  --precis-path /path/to/precis
```

### Batch Testing

```python
# custom_test.py
from experiment_runner import *

queries = [
    "Can hospitals share data?",
    "Is consent required?",
    "Must entities have privacy officers?"
]

runner = ExperimentRunner(precis, llm, retriever)

for query in queries:
    result = runner.run_agent4compliance(query)
    print(f"Q: {query}")
    print(f"A: {result['explanation']}\n")
```

## 📈 Comparing Experiments

### Performance Metrics

| Metric | Baseline No Ctx | Baseline Ctx | RAG | Agent4Compliance |
|--------|-----------------|--------------|-----|------------------|
| **Speed** | ⚡⚡⚡ Fastest | ⚡⚡ Fast | ⚡ Medium | 🐌 Slowest |
| **Accuracy** | 🎯 Low | 🎯🎯 Medium | 🎯🎯🎯 High | 🎯🎯🎯🎯 Highest |
| **Traceability** | ❌ None | ❌ None | ⚠️ Limited | ✅ Full |
| **Formal Proof** | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **Complexity** | Simple | Simple | Medium | Complex |

### When to Use Each

**Baseline (No Context):**
- Quick prototyping
- General knowledge questions
- When rules aren't available

**Baseline (With Context):**
- When all rules are relevant
- Small rule databases
- Simple queries

**RAG:**
- Large rule databases
- When only few rules are relevant
- Performance-critical applications

**Agent4Compliance:**
- High-stakes decisions
- Need formal verification
- Require legal traceability
- Explainability is critical

## 🐛 Troubleshooting

### Error: "Précis executable not found"
```bash
# Check if built
ls precis

# Rebuild if needed
dune build
```

### Error: "ANTHROPIC_API_KEY not found"
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Error: "Module not found"
```bash
pip install anthropic streamlit pandas
```

### Slow Performance
```bash
# Use quick test
python test_suite.py --quick

# Or run specific experiments
python experiment_runner.py \
  --experiment baseline_no_context
```

## 📝 Example Queries

### HIPAA
- "Can a hospital disclose patient information to a business associate?"
- "Is authorization required for using PHI for treatment?"
- "Must every covered entity have a privacy officer?"
- "Can PHI be disclosed for public health activities?"
- "Is patient consent required for facility directories?"

### GDPR
- "Is consent required for processing personal data?"
- "Can data subjects request erasure of their data?"
- "What are the lawful bases for processing?"

### SOX
- "Must companies maintain internal controls?"
- "What are the requirements for financial disclosures?"

## 🔬 Research Use

### Collecting Results for Analysis

```bash
# Run all experiments on all test queries
python test_suite.py \
  --regulations HIPAA GDPR \
  --output research_results.json

# Generates:
# - research_results.json (detailed)
# - research_results.csv (for analysis)
```

### Analyzing Results

```python
import pandas as pd

# Load results
df = pd.read_csv('research_results.csv')

# Group by experiment
grouped = df.groupby('Experiment').agg({
    'Duration': ['mean', 'std'],
    'Status': lambda x: (x == 'Success').sum()
})

print(grouped)
```

## 📚 Directory Structure

```
project/
├── src/                          # OCaml Précis engine
├── policies/                     # Policy files
│   ├── hipaa.policy
│   ├── gdpr.policy
│   └── sox.policy
├── data/                         # System configuration
│   ├── type_system.txt
│   ├── domain.txt
│   ├── facts.txt
│   └── functions.txt
├── experiment_runner.py          # Core experiment logic
├── streamlit_app.py             # Web UI
├── test_suite.py                # Comprehensive tests
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🎯 Next Steps

1. **Run the Streamlit UI** for interactive exploration
2. **Run test suite** to collect baseline data
3. **Compare results** across experiments
4. **Customize queries** for your specific use case
5. **Extend with new regulations** by adding `.policy` files

## 💡 Tips

- Start with `--quick` mode for fast iteration
- Use Streamlit UI for demos and exploration
- Use test suite for systematic evaluation
- Check `precis inspect` to verify system state
- Monitor API usage with Claude dashboard
