# NL to LTL Translation System - Setup Guide

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **OCaml and Dune** (for LTL verification tool)
3. **NuSMV** (model checker)
4. **SySLite2** (formula synthesis tool)
5. **Claude API Key** (for LLM interactions)

### Installation Steps

#### 1. Clone and Setup OCaml Tool

```bash
# Navigate to OCaml tool directory
cd LTL/corrected_version/ltlutils/

# Compile the OCaml tool
./compile-project

# Or manually:
dune clean
dune build

# Test it works
echo -e "generate_random_formula\n" | dune exec ./bin/main.exe
```

#### 2. Install NuSMV

```bash
# On macOS
brew install nusmv

# On Ubuntu/Debian
sudo apt-get install nusmv

# Verify installation
which nusmv
nusmv -h
```

#### 3. Setup Python Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 4. Setup SySLite (if not already installed)

```bash
# Ensure SySLite's Driver.py is accessible
# Default location: ./src/Driver.py
# Update Config.SYSLITE_SCRIPT if different
```

#### 5. Configure Claude API

```bash
# Create .env file in project root
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
```

### Running the Application

```bash
# Start Streamlit app
streamlit run app.py

# Or with custom port
streamlit run app.py --server.port 8501
```

## 📁 Project Structure

```
nl-to-ltl-system/
├── app.py                          # Main Streamlit application
├── ocaml_interface.py             # OCaml tool wrapper
├── syslite_interface.py           # SySLite tool wrapper
├── requirements.txt               # Python dependencies
├── .env                           # API keys (create this)
├── README.md                      # This file
│
├── LTL/                           # OCaml LTL Tool
│   └── corrected_version/
│       └── ltlutils/
│           ├── bin/
│           │   └── main.exe       # Compiled binary
│           └── compile-project    # Build script
│
└── src/                           # SySLite
    └── Driver.py                  # SySLite synthesis script
```

## 🎯 Usage Guide

### Baseline/Workflow Mode

#### Step 1: Extract Atomic Propositions
1. Enter your natural language requirement
2. Click "Extract APs"
3. Review extracted propositions

#### Step 2: Generate Formulas
1. Generate formulas using both strategies:
   - **Detailed Strategy**: Direct LTL translation
   - **Python Strategy**: AST-based approach
2. Review generated formulas

#### Step 3: Generate Traces
1. Click "Generate All Traces"
2. System creates traces for all 4 truth table cases:
   - ✗D ✗P: Rejected by both formulas
   - ✗D ✓P: Accepted by Python only
   - ✓D ✗P: Accepted by Detailed only
   - ✓D ✓P: Accepted by both formulas

#### Step 4: Provide Feedback
1. For each trace, specify: "Should this satisfy your requirement?"
2. System checks alignment with formulas
3. View alignment results

#### Step 5: Refinement (if needed)
1. If formulas don't align, choose refinement:
   - **LLM Repair**: Re-prompt Claude with mismatches
   - **SySLite Synthesis**: Learn from positive/negative traces
2. New formulas are evaluated against all traces
3. Repeat until alignment achieved

### Agentic Mode (Coming Soon)

Autonomous AI agents will:
- Extract APs independently
- Generate and validate formulas
- Create and evaluate traces
- Refine until success
- Provide transparent reasoning

## 🔧 Testing the Tools Independently

### Test OCaml Tool

```bash
cd LTL/corrected_version/ltlutils/

# Create test input file
cat > test_input.txt << EOF
check_trace_satisfaction
G(p -> F(q))
[p=true,q=false]; [p=false,q=true]; [p=false,q=false]; ...
equiv
G(a)
!F(!a)
positive_trace_gen
G(a -> b)
EOF

# Run test
dune exec ./bin/main.exe < test_input.txt
```

### Test SySLite

```bash
# Create test trace file
cat > test.trace << EOF
failure,alarm
---
1,1;0,1;0,0
1,0;0,1;0,1;1,1::1
---
1,0;1,0
0,0;1,0;1,1
---
!,F,G,X
---
&,|,=>
EOF

# Run synthesis
python3 ./src/Driver.py -l ltl -n 5 -r result.txt -a bv_sygus -dict -t test.trace
```

### Test Python Modules

```python
# Test OCaml interface
from ocaml_interface import OCamlLTLInterface

ocaml = OCamlLTLInterface()
formula = "G(a -> F(b))"

# Generate traces
pos_trace = ocaml.generate_positive_trace(formula)
neg_trace = ocaml.generate_negative_trace(formula)

print(f"Positive: {pos_trace.raw_format}")
print(f"Negative: {neg_trace.raw_format}")

# Check satisfaction
print(f"Pos satisfies: {ocaml.check_trace_satisfaction(formula, pos_trace)}")
print(f"Neg satisfies: {ocaml.check_trace_satisfaction(formula, neg_trace)}")
```

```python
# Test SySLite interface
from syslite_interface import SySLiteInterface

syslite = SySLiteInterface()

# Create trace file
aps = ['failure', 'alarm']
positive_traces = [{
    'states': [
        {'failure': True, 'alarm': True},
        {'failure': False, 'alarm': False}
    ],
    'loop_index': None
}]
negative_traces = [{
    'states': [
        {'failure': True, 'alarm': False},
        {'failure': True, 'alarm': False}
    ],
    'loop_index': 1
}]

trace_content = syslite.create_trace_file(
    aps=aps,
    positive_traces=positive_traces,
    negative_traces=negative_traces
)

# Run synthesis
result = syslite.synthesize(trace_content, max_formulas=5)
print(f"Success: {result.success}")
print(f"Formulas: {result.formulas}")
```

## 🐛 Troubleshooting

### OCaml Tool Issues

**Problem**: "OCaml binary not found"
```bash
cd LTL/corrected_version/ltlutils/
dune clean
dune build
```

**Problem**: "NuSMV not found"
```bash
# Install NuSMV
brew install nusmv  # macOS
sudo apt-get install nusmv  # Linux
```

### SySLite Issues

**Problem**: "Driver.py not found"
- Update `Config.SYSLITE_SCRIPT` in app.py
- Ensure SySLite is in correct directory

**Problem**: "Synthesis timeout"
- Increase timeout parameter
- Reduce formula complexity
- Simplify traces

### Streamlit Issues

**Problem**: Port already in use
```bash
streamlit run app.py --server.port 8502
```

**Problem**: Module not found
```bash
pip install -r requirements.txt --upgrade
```

## 📊 Understanding Trace Formats

### OCaml NuSMV Format
```
[[var |=> value, ...]];[[...]];...
```

Example:
```
[[a |=> true, b |=> false]];[[a |=> false, b |=> true]];...
```

### SySLite Format
```
val1,val2;val1,val2;...::loop_index
```

Example:
```
1,0;0,1;0,0::1
```
- States: `1,0` then `0,1` then `0,0`
- Loop from index 1: `0,1;0,0` repeats

### Conversion Example

**NuSMV**:
```
A
Loop starts: B
C
```

**SySLite**:
```
A; B::1; C
```

## 🎓 Key Concepts

### Truth Table (2x2)

| Detailed (D) | Python (P) | Meaning |
|--------------|------------|---------|
| ✗ | ✗ | Both reject trace |
| ✗ | ✓ | Python accepts, Detailed rejects |
| ✓ | ✗ | Detailed accepts, Python rejects |
| ✓ | ✓ | Both accept trace |

### Alignment

A formula is **aligned** with user intent if:
- For every trace: `formula_satisfaction == user_feedback`

### Refinement

When formulas don't align:
1. **LLM Repair**: Re-prompt with mismatches
2. **SySLite Synthesis**: Learn from labeled traces

## 📝 Next Steps

1. **Phase 1**: Get baseline mode fully working
   - AP extraction with Claude API
   - Formula generation with both strategies
   - Trace generation and evaluation
   - Basic refinement

2. **Phase 2**: Implement agentic mode
   - Setup CrewAI agents
   - Define agent roles and tools
   - Implement autonomous workflow

3. **Phase 3**: Enhancements
   - Better UI/UX
   - Export results
   - Session history
   - Performance optimization

## 📞 Support

For issues or questions:
1. Check OCaml tool output: `dune exec ./bin/main.exe < input.txt`
2. Verify SySLite: `python3 ./src/Driver.py -h`
3. Test modules independently (see Testing section)
4. Review Streamlit logs in terminal

## 🎉 You're Ready!

Start the app and begin translating natural language to LTL:

```bash
streamlit run app.py
```

Navigate to `http://localhost:8501` and select **Baseline Mode** to begin!
