import streamlit as st
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
import streamlit as st
import pandas as pd
import os
import subprocess
from pathlib import Path
import tempfile
from typing import List, Dict, Tuple, Optional
import re
class TraceType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"

@dataclass
class Trace:
    """Trace data structure"""
    case_name: str
    trace_type: TraceType
    states: List[Dict[str, bool]]
    loop_index: int
    raw_format: str
    is_satisfiable: bool
    detailed_sat: bool
    python_sat: bool
@dataclass
class TraceArtifact:
    case: str                  # "!D&!P", "D&!P", ...
    constraint: str            # pretty string: ¬D ∧ ¬P
    trace: str | None          # formatted trace
    raw: str                   # raw NuSMV output
    satisfiable: bool

@dataclass
class SemanticJudgment:
    llm_label: bool          # True = satisfies
    user_label: bool | None  # None = no override
    overridden: bool = False
@dataclass
class JudgmentRow:
    constraint: str
    trace_id: str
    trace: dict
    D: bool
    P: bool
    R: bool
    semantic: SemanticJudgment

CONSTRAINTS = {
    "!D&!P": {"negate_D": True, "negate_P": True},
    "!D&P": {"negate_D": True, "negate_P": False},
    "D&!P": {"negate_D": False, "negate_P": True},
    "D&P": {"negate_D": False, "negate_P": False}
}
class SySLiteWrapper:
    def __init__(self, syslite_path: str = "./SySLite2"):
        self.syslite_path = syslite_path
    
    def synthesize(self, positive_traces: List[str], negative_traces: List[str],
                   aps: List[str], size: int = 5) -> Tuple[List[str], str, str]:
        """
        Run SySLite synthesis
        
        Args:
            positive_traces: List of traces in SySLite format (e.g., "1,0;0,1::1")
            negative_traces: List of traces in SySLite format
            aps: Atomic propositions
            size: Formula size bound
            
        Returns:
            Tuple of (formulas, stdout, stderr) for debugging
        """
        # Create trace file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.trace') as f:
            # Write atomic propositions
            f.write(",".join(aps) + "\n")
            f.write("---\n")
            
            # Write positive traces
            for trace in positive_traces:
                f.write(trace + "\n")
            f.write("---\n")
            
            # Write negative traces
            for trace in negative_traces:
                f.write(trace + "\n")
            
            trace_file = f.name
        
        # Read trace file content for debugging
        with open(trace_file, 'r') as f:
            trace_file_content = f.read()
        
        try:
            # Run SySLite
            result = subprocess.run(
                [
                    "python3", "./src/Driver.py",
                    "-l", "ltl",
                    "-n", str(size),
                    "-r", "result.txt",
                    "-a", "bv_sygus",
                    "-dict",
                    "-t", trace_file
                ],
                capture_output=True,
                text=True,
                cwd=self.syslite_path,
                timeout=120
            )
            
            stdout = result.stdout
            stderr = result.stderr
            
            # Parse output - check BOTH stdout AND stderr (SySLite logs to stderr!)
            formulas = []
            combined_output = stdout + "\n" + stderr
            
            for line in combined_output.split('\n'):
                if "Found Formula" in line:
                    # Extract formula after "Found Formula"
                    formula = line.split("Found Formula")[1].strip()
                    formulas.append(formula)
            
            # Add trace file content to debug output
            debug_output = f"=== TRACE FILE CONTENT ===\n{trace_file_content}\n\n"
            debug_output += f"=== STDOUT ===\n{stdout}\n\n"
            debug_output += f"=== STDERR ===\n{stderr}\n\n"
            debug_output += f"=== PARSED FORMULAS ===\n"
            for i, f in enumerate(formulas):
                debug_output += f"{i+1}. {f}\n"
            
            return formulas, debug_output, trace_file
            
        except Exception as e:
            error_msg = f"SySLite error: {str(e)}"
            st.error(error_msg)
            return [], error_msg, trace_file
        finally:
            # Keep trace file for debugging
            pass  # Don't delete so user can inspect it
def normalize_syslite_formula(raw: str) -> Optional[str]:
    """
    Convert SySLite Boolean / temporal skeleton into clean LTL.

    Returns:
        Normalized LTL string, or None if semantically vacuous.
    """

    if not raw or raw.strip().upper() in {"TRUE", "X(TRUE)", "G(TRUE)"}:
        return None

    f = raw.strip()

    # --- Rule 1: Boolean lifting ---
    replacements = {
        r"\|\(([^,]+),([^)]+)\)": r"(\1 | \2)",
        r"&\(([^,]+),([^)]+)\)": r"(\1 & \2)",
        r"=>\(([^,]+),([^)]+)\)": r"(\1 -> \2)",
    }

    for pattern, repl in replacements.items():
        f = re.sub(pattern, repl, f)

    # --- Rule 2: Remove redundant parentheses ---
    f = f.strip()

    # --- Rule 3: Detect temporal operators ---
    has_temporal = any(op in f for op in ["G(", "F(", "U", "X("])

    # --- Rule 4: Lift to G if purely Boolean ---
    if not has_temporal:
        f = f"G({f})"

    # --- Rule 5: Structural validation ---
    if not any(tok in f for tok in ["G(", "F(", "U", "->", "&", "|"]):
        return None

    return f

def convert_ast_to_standard_ltl(formula: str) -> str:
    """
    Convert AST-style formulas to standard LTL notation
    
    Examples:
    - data_saved -> data_saved
    - &(data_saved,app_terminating) -> (data_saved & app_terminating)
    - =>(app_terminating,data_saved) -> (app_terminating -> data_saved)
    - X(!(data_saved)) -> X(!data_saved)
    - F(&(data_saved,app_terminating)) -> F(data_saved & app_terminating)
    """
    # If it's already standard LTL (contains G, F, X, U without prefix notation), return as is
    if not any(op in formula for op in ['&(', '|(', '=>(', '!(', 'U(']):
        return formula
    
    # Replace AST operators with standard notation
    result = formula
    
    # Handle nested operations recursively
    import re
    
    # Replace =>(...) with (... -> ...)
    while '=>(' in result:
        match = re.search(r'=>\(([^,]+),([^)]+)\)', result)
        if match:
            left, right = match.groups()
            result = result.replace(match.group(0), f"({left.strip()} -> {right.strip()})")
        else:
            break
    
    # Replace &(...) with (... & ...)
    while '&(' in result:
        match = re.search(r'&\(([^,]+),([^)]+)\)', result)
        if match:
            left, right = match.groups()
            result = result.replace(match.group(0), f"({left.strip()} & {right.strip()})")
        else:
            break
    
    # Replace |(...) with (... | ...)
    while '|(' in result:
        match = re.search(r'\|\(([^,]+),([^)]+)\)', result)
        if match:
            left, right = match.groups()
            result = result.replace(match.group(0), f"({left.strip()} | {right.strip()})")
        else:
            break
    
    # Replace U(...) with (... U ...)
    while 'U(' in result and result.index('U(') > 0 and result[result.index('U(')-1] not in ['G', 'F', 'X']:
        match = re.search(r'(?<![GFX])U\(([^,]+),([^)]+)\)', result)
        if match:
            left, right = match.groups()
            result = result.replace(match.group(0), f"({left.strip()} U {right.strip()})")
        else:
            break
    
    # Replace !(X) with !X for simpler cases
    result = re.sub(r'!\(([^)]+)\)', r'!(\1)', result)
    
    return result

def generate_truth_table_constraints(formulas: Dict[str, str], max_formulas: int = 5) -> List[Dict]:
    """
    Recursively generate all 2^n truth table combinations for n formulas
    
    Args:
        formulas: Dictionary of {label: formula_string}
                 e.g., {"D": "G(armed -> F(alarm))", "P": "G(...)", "F": "..."}
        max_formulas: Maximum number of formulas to prevent explosion (default 5)
    
    Returns:
        List of constraint dictionaries with formula combinations
        
    Example:
        With 2 formulas (D, P): Returns 2^2 = 4 combinations
        With 3 formulas (D, P, F): Returns 2^3 = 8 combinations
    """
    formula_labels = list(formulas.keys())
    n = len(formula_labels)
    
    if n > max_formulas:
        raise ValueError(f"Too many formulas ({n}). Maximum is {max_formulas} to prevent 2^{n} explosion")
    
    if n == 0:
        return []
    
    # Generate all 2^n binary combinations
    num_combinations = 2 ** n
    constraints = []
    
    for i in range(num_combinations):
        # Convert number to binary representation
        binary = format(i, f'0{n}b')
        
        # Build constraint name and formula
        constraint_parts = []
        formula_parts = []
        negation_flags = {}
        
        for j, label in enumerate(formula_labels):
            is_negated = (binary[j] == '0')  # 0 = negated, 1 = not negated
            
            if is_negated:
                constraint_parts.append(f"!{label}")
                formula_parts.append(f"!({formulas[label]})")
            else:
                constraint_parts.append(label)
                formula_parts.append(f"({formulas[label]})")
            
            negation_flags[label] = is_negated
        
        # Create constraint name: "!D&!P&F"
        constraint_name = "&".join(constraint_parts)
        
        # Create combined formula: "!(D) & !(P) & (F)"
        combined_formula = " & ".join(formula_parts)
        
        constraints.append({
            "name": constraint_name,
            "formula": combined_formula,
            "negation_flags": negation_flags,
            "binary": binary
        })
    
    return constraints

def normalize_syslite_ltl(formula: str) -> str:
    f = formula.strip()

    # U(FALSE, φ)  →  F φ
    f = re.sub(r'U\s*\(\s*FALSE\s*,\s*(.*?)\)', r'F(\1)', f)

    # !!φ → φ
    f = re.sub(r'!\s*!\s*', '', f)

    # !(a & b) → (!a | !b)
    f = re.sub(
        r'!\s*\(\s*(\w+)\s*&\s*(\w+)\s*\)',
        r'(!\1 | !\2)',
        f
    )

    # (a -> X(a)) keep as-is (already standard)

    return f


def extract_aps(nl_requirement: str):
    """Extract atomic propositions using Claude"""
    with st.spinner("Extracting atomic propositions..."):
        try:
            aps, explanation = st.session_state.claude_helper.extract_atomic_propositions(nl_requirement)
            st.session_state.aps = aps
            st.session_state.aps_explanation = explanation
            st.rerun()
        except Exception as e:
            st.error(f"Error: {str(e)}")

def generate_detailed_formula():
    """Generate formula using detailed strategy"""
    if st.session_state.claude_helper is None:
        st.error("⚠️ Please initialize Claude API first")
        return
    
    with st.spinner("Generating detailed formula..."):
        try:
            formula, explanation = st.session_state.claude_helper.generate_detailed_formula(
                st.session_state.nl_requirement,
                st.session_state.aps
            )
            st.session_state.detailed_formula = formula
            st.session_state.detailed_explanation = explanation
            st.rerun()
        except Exception as e:
            st.error(f"Error: {str(e)}")

def generate_python_formula():
    """Generate formula using Python strategy"""
    if st.session_state.claude_helper is None:
        st.error("⚠️ Please initialize Claude API first")
        return
    
    with st.spinner("Generating Python formula..."):
        try:
            python_ast, std_ltl, explanation = st.session_state.claude_helper.generate_python_formula(
                st.session_state.nl_requirement,
                st.session_state.aps
            )
            st.session_state.python_formula = std_ltl  # Use standard LTL version
            st.session_state.python_explanation = f"Python AST: {python_ast}\n\n{explanation}"
            st.rerun()
        except Exception as e:
            st.error(f"Error: {str(e)}")

def build_constraint_formula(detailed: str, python: str, flags: Dict) -> str:
    """Build constraint formula based on negation flags"""
    d_part = f"!({detailed})" if flags["negate_D"] else f"({detailed})"
    p_part = f"!({python})" if flags["negate_P"] else f"({python})"
    return f"{d_part} & {p_part}"


def generate_nusmv_model(formula: str, aps: List[str] = None) -> str:
    """Generate NuSMV model for trace generation"""
    if aps is None:
        # Extract APs from session state if available
        aps = st.session_state.get("aps", [])
    
    if not aps:
        raise ValueError("Atomic propositions must be provided")
    """Generate NuSMV model for trace generation"""
    var_declarations = "\n".join([f"{ap} : boolean;" for ap in aps])
    var_assignments = "\n".join([
        f"init({ap}) := {{TRUE, FALSE}};\nnext({ap}) := {{TRUE, FALSE}};"
        for ap in aps
    ])
    
    return f"""MODULE main
VAR
{var_declarations}

ASSIGN
{var_assignments}

LTLSPEC !({formula})
"""


def run_nusmv(model_content: str) -> Dict:
    """Run NuSMV and return results"""
    ocaml_path = "./LTL/corrected_version/ltlutils"
    
    # Write model file
    model_file = os.path.join(ocaml_path, "query.smv")
    with open(model_file, 'w') as f:
        f.write(model_content)
    
    try:
        # Run NuSMV
        result = subprocess.run(
            ["nusmv", model_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout
        
        # Check satisfiability
        if "is true" in output:
            return {
                "satisfiable": False,
                "trace": None,
                "raw": output
            }
        elif "is false" in output:
            return {
                "satisfiable": True,
                "trace": output,
                "raw": output
            }
        else:
            return {
                "satisfiable": False,
                "trace": None,
                "raw": output
            }
            
    except Exception as e:
        return {
            "satisfiable": False,
            "trace": None,
            "raw": f"Error: {str(e)}"
        }

def nusmv_trace_to_canonical(raw_output: str, ap_list: list[str]) -> str | None:
    """
    Converts NuSMV counterexample output into canonical trace format.
    Returns None if no trace exists.
    """

    if "no counterexample found" in raw_output.lower():
        return None

    states = []
    current = {}

    for line in raw_output.splitlines():
        line = line.strip()

        # New state
        if line.startswith("-> State"):
            if current:
                states.append(current)
            current = {}

        # AP assignment
        for ap in ap_list:
            m = re.search(rf"{ap}\s*=\s*(TRUE|FALSE)", line)
            if m:
                current[ap] = (m.group(1) == "TRUE")

    if current:
        states.append(current)

    if not states:
        return None

    # Render canonical format
    rendered = []
    for s in states:
        rendered.append(
            "[" + ", ".join(f"{k}={'true' if v else 'false'}" for k, v in s.items()) + "]"
        )

    return "; ".join(rendered)

def trace_to_syslite_format(trace: str, aps: List[str]) -> str:
    """
    Convert canonical trace to SySLite format
    
    Input: [alarm=true, armed=false]; [alarm=false, armed=true]::1
    Output (with aps=["alarm", "armed"]): 1,0;0,1::1
    """
    if not trace:
        return ""
    
    # Split by loop notation
    parts = trace.split("::")
    states_str = parts[0]
    loop_idx = parts[1] if len(parts) > 1 else None
    
    # Extract state blocks
    state_blocks = re.findall(r'\[([^\]]+)\]', states_str)
    
    syslite_states = []
    for block in state_blocks:
        # Parse key=value pairs
        state_dict = {}
        pairs = block.split(", ")
        for pair in pairs:
            if "=" in pair:
                key, val = pair.split("=")
                state_dict[key.strip()] = val.strip()
        
        # Convert to binary based on AP order
        binary = []
        for ap in aps:
            if ap in state_dict:
                binary.append("1" if state_dict[ap] == "true" else "0")
            else:
                binary.append("0")
        
        syslite_states.append(",".join(binary))
    
    result = ";".join(syslite_states)
    if loop_idx:
        result += f"::{loop_idx}"
    
    return result
def llm_semantic_oracle(claude, nl_requirement, trace):
    """
    Soft semantic oracle using ClaudeAPIHelper.get_trace_feedback
    """
    should_satisfy, reasoning = claude.get_trace_feedback(
        trace_description=trace,
        nl_requirement=nl_requirement
    )
    return should_satisfy, reasoning
def llm_semantic_judgment(claude, nl_requirement, trace):
    """
    Canonical semantic oracle used in Step 4 and Step 7.
    """
    should_satisfy, reasoning = claude.get_trace_feedback(
        trace_description=trace,
        nl_requirement=nl_requirement
    )

    return {
        "llm_label": should_satisfy,
        "reasoning": reasoning,
        "user_override": None
    }

def bool_icon(value: bool) -> str:
    return "✓" if value else "✗"
def get_effective_label(judgment: SemanticJudgment) -> bool:
    """
    Returns the authoritative semantic label.
    User override > LLM judgment
    """
    if judgment.overridden:
        return judgment.user_label
    return judgment.llm_label
def collect_counterexamples(rows):
    """
    Counterexamples are traces that violate the requirement
    under the effective semantic judgment.
    """
    counterexamples = []

    for row in rows:
        effective = get_effective_label(row.semantic)
        if not effective:
            counterexamples.append(row.trace)

    return counterexamples

def render_judgment_row(row: JudgmentRow) -> JudgmentRow:
    llm_label = row.semantic.llm_label

    default_index = 0 if llm_label else 1
    options = ["Satisfies", "Violates"]

    user_choice = st.selectbox(
        "",
        options,
        index=default_index,
        key=f"semantic_{row.trace_id}_{row.constraint}"
    )

    user_label = user_choice == "Satisfies"

    # Detect override
    if user_label != llm_label:
        row.semantic.user_label = user_label
        row.semantic.overridden = True
    else:
        row.semantic.user_label = None
        row.semantic.overridden = False

    # Display row
    st.markdown(
        f"| {row.constraint} | {row.trace_id} | "
        f"{bool_icon(row.D)} | {bool_icon(row.P)} | {bool_icon(row.R)} | "
        f"**{user_choice}** |"
    )

    return row

def syslite_to_ltl(syslite_formula: str | None) -> str | None:
    if not syslite_formula:
        return None

    f = syslite_formula.strip()

    if f in {"None", "G(None)", "F(None)"}:
        return None

    # Normalize syntax
    replacements = {
        "&&": "&",
        "||": "|",
        "!(": "!(",
        "[]": "G",
        "<>": "F"
    }

    for k, v in replacements.items():
        f = f.replace(k, v)

    # Remove outer garbage
    if f.startswith("G(") and f.endswith(")") and "None" in f:
        return None

    return f

def render_semantic_table(
    title: str,
    rows: List[Dict],
    highlight_unsat: bool = True
):
    """
    Generic semantic evaluation table renderer.
    Each row must contain:
      - constraint
      - trace (or None)
      - judgment (or None)
      - status
    """

    st.subheader(title)

    df = pd.DataFrame(rows)

    def style_rows(row):
        if highlight_unsat and "Universally satisfied" in str(row["Semantic Status"]):
            return ["background-color: #e6ffe6"] * len(row)
        if "Violated" in str(row["Semantic Status"]):
            return ["background-color: #ffe6e6"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df.style.apply(style_rows, axis=1),
        use_container_width=True
    )
