import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import re
sys.path.append(str(Path(__file__).parent))
try:
    from ocaml_interface import OCamlLTLInterface
    from nusmv_wrapper import NuSMVTraceGenerator
    from syslite_interface import SySLiteInterface
    from claude_api_helper import ClaudeAPIHelper
    from utils import SySLiteWrapper,llm_semantic_judgment, llm_semantic_oracle, TraceArtifact, CONSTRAINTS,render_semantic_table, extract_aps, build_constraint_formula, generate_python_formula, generate_detailed_formula, generate_nusmv_model, run_nusmv, nusmv_trace_to_canonical, trace_to_syslite_format,normalize_syslite_formula, convert_ast_to_standard_ltl, generate_truth_table_constraints
except ImportError as e:
    st.error(f"Import error: {e}")
    st.info("Make sure ocaml_interface.py, syslite_interface.py, and claude_api_helper.py are in the same directory")


PROJECT_ROOT = Path(__file__).parent.parent.resolve() 
class Config:
    OCAML_DIR = PROJECT_ROOT / "LTL" / "corrected_version" / "ltlutils"
    SYSLITE_DIR = PROJECT_ROOT / "SySLite2"
    MAX_ITERATIONS = 3


def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'mode': 'baseline',
        'ocaml_interface': None,
        'nusmv_generator': None,
        'syslite_interface': None,
        'claude_helper': None,
        'nl_requirement': '',
        'aps': [],
        'aps_explanation': '',
        "constraint_traces": {},
        'detailed_formula': '',
        'detailed_explanation': '',
        'python_formula': '',
        'python_explanation': '',
        "trace_artifacts": None,
        "traces_generated": False,
        'traces': [],
        'eval_data': [],
        'needs_refinement': False,
        'iteration': 0,
        'all_formulas': {},
        "syslite_results": {},
        'current_step': 1,
        'step3_results': {},  # Added for consistency
        'refined_formulas': [],  # Added for consistency
        'llm_feedbacks': {},
        'user_feedback_overrides': {},
        'llm_feedbacks_2cubed': {},
        'user_feedback_overrides_2cubed': {},
        'reintegrated_traces': {},
        'refined_formula': '',
        'step_6_complete': False,
        'step_7_complete': False,

        # Step control
        "current_step": 1,
        "iteration_count": 0,

        # Inputs
        "nl_requirement": None,

        # Step 3–6 artifacts
        "constraint_traces": {},
        "reintegrated_traces": {},

        # Semantic oracle
        "semantic_oracle": {},          # LLM judgments
        "semantic_ground_truth": {},    # Final truth (LLM + overrides)

    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def save_session_data(step_name: str):
    """Save a minimal snapshot of session state for debugging/export."""
    try:
        data = {
            'nl_requirement': st.session_state.get('nl_requirement', ''),
            'aps': st.session_state.get('aps', []),
            'detailed_formula': st.session_state.get('detailed_formula', ''),
            'python_formula': st.session_state.get('python_formula', ''),
            'traces_count': len(st.session_state.get('traces', [])),
            'eval_data': st.session_state.get('eval_data', []),
            'current_step': st.session_state.get('current_step', None),
        }
        out_dir = Path(__file__).parent / "session_exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"session_{step_name}.json"
        import json
        with open(out_file, 'w') as f:
            json.dump(data, f, default=str, indent=2)
        st.success(f"Session data saved to {out_file}")
        
    except Exception as e:
        st.error(f"Failed to save session data: {e}")

def main():
    st.set_page_config(
        page_title="NL to LTL Translation System",
        page_icon="🔄",
        layout="wide"
    )
    
    init_session_state()
    
    # Header
    st.title("🔄 Natural Language to LTL Translation System")
    st.markdown("Translate natural language requirements to Linear Temporal Logic formulas with iterative validation")
    st.markdown("---")
    
    # Sidebar
    render_sidebar()
    
    # Main content
    if st.session_state.mode == 'baseline':
        render_baseline_mode()
    else:
        render_agentic_mode()

def render_sidebar():
    """Render sidebar with configuration and tools"""
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Mode Selection
        mode = st.radio(
            "Operation Mode:",
            options=['baseline', 'agentic'],
            format_func=lambda x: "📋 Baseline/Workflow" if x == 'baseline' else "🤖 Agentic (CrewAI)",
            key='mode_selector'
        )
        st.session_state.mode = mode
        
        st.markdown("---")
        
        # Agentic Mode Configuration (only show when agentic mode is selected)
        if mode == 'agentic':
            st.subheader("🤖 Agentic Settings")
            
            max_repair = st.slider(
                "Max Repair Attempts:", 
                min_value=1, 
                max_value=5, 
                value=st.session_state.get('agentic_max_repair', 3),
                help="Maximum number of formula repair attempts before escalating to human review",
                key='agentic_max_repair_slider'
            )
            st.session_state.agentic_max_repair = max_repair
            
            auto_advance = st.checkbox(
                "Auto-advance on success",
                value=st.session_state.get('agentic_auto_advance', True),
                help="Automatically proceed to next step when formulas align",
                key='agentic_auto_advance_check'
            )
            st.session_state.agentic_auto_advance = auto_advance
            
            show_details = st.checkbox(
                "Show detailed logs",
                value=st.session_state.get('agentic_show_details', True),
                help="Display verbose execution logs and intermediate results",
                key='agentic_show_details_check'
            )
            st.session_state.agentic_show_details = show_details
            
            st.markdown("---")
        
        # Tool Initialization
        st.subheader("🔧 Tool Status")
        
        # OCaml Tool
        with st.expander("OCaml LTL Tool", expanded=False):
            ocaml_dir = st.text_input(
                "OCaml Directory:", 
                value=Config.OCAML_DIR, 
                key='ocaml_dir_input'
            )
            
            if st.button("Initialize OCaml", key='init_ocaml'):
                try:
                    with st.spinner("Initializing OCaml tool..."):
                        st.session_state.ocaml_interface = OCamlLTLInterface(ocaml_dir)
                        st.session_state.nusmv_generator = NuSMVTraceGenerator(ocaml_dir=ocaml_dir)
                    st.success("✓ OCaml initialized")
                except Exception as e:
                    st.error(f"✗ Error: {str(e)}")
            
            if st.session_state.get('ocaml_interface'):
                st.success("✓ OCaml Ready")
            if st.session_state.get('nusmv_generator'):
                st.success("✓ NuSMV Generator Ready")
            else:
                st.warning("⚠ Not initialized")
        
        # SySLite Tool
        with st.expander("SySLite Synthesis Tool", expanded=False):
            syslite_dir = st.text_input(
                "SySLite Directory:", 
                value=Config.SYSLITE_DIR, 
                key='syslite_dir_input'
            )
            
            if st.button("Initialize SySLite", key='init_syslite'):
                try:
                    with st.spinner("Initializing SySLite..."):
                        st.session_state.syslite_interface = SySLiteInterface(syslite_dir)
                    st.success("✓ SySLite initialized")
                except Exception as e:
                    st.error(f"✗ Error: {str(e)}")
            
            if st.session_state.get('syslite_interface'):
                st.success("✓ SySLite Ready")
            else:
                st.warning("⚠ Not initialized")
        
        # Claude API
        with st.expander("Claude API", expanded=False):
            api_key = st.text_input(
                "API Key:", 
                type="password", 
                key='claude_api_key'
            )
            
            if st.button("Initialize Claude", key='init_claude'):
                try:
                    with st.spinner("Initializing Claude API..."):
                        st.session_state.claude_helper = ClaudeAPIHelper(api_key)
                    st.success("✓ Claude initialized")
                except Exception as e:
                    st.error(f"✗ Error: {str(e)}")
            
            if st.session_state.get('claude_helper'):
                st.success("✓ Claude Ready")
            else:
                st.warning("⚠ Not initialized")
        
        st.markdown("---")
        
        # Parameters
        st.subheader("⚙️ Parameters")
        max_iterations = st.slider(
            "Max Iterations:", 
            1, 
            5, 
            st.session_state.get('max_iterations', Config.MAX_ITERATIONS),
            key='max_iterations_slider'
        )
        Config.MAX_ITERATIONS = max_iterations
        st.session_state.max_iterations = max_iterations
        
        # Quick Init All
        st.markdown("---")
        if st.button("🚀 Initialize All Tools", type="primary"):
            initialize_all_tools()
        
        # Session Reset
        st.markdown("---")
        if st.button("🔄 Reset Session", help="Clear all session data"):
            reset_session()

def initialize_all_tools():
    """Initialize all tools at once"""
    with st.spinner("Initializing all tools..."):
        try:
            # OCaml
            if not st.session_state.get('ocaml_interface'):
                st.session_state.ocaml_interface = OCamlLTLInterface(Config.OCAML_DIR)
            
            if not st.session_state.get('nusmv_generator'):
                st.session_state.nusmv_generator = NuSMVTraceGenerator(ocaml_dir=Config.OCAML_DIR)
            
            # SySLite
            if not st.session_state.get('syslite_interface'):
                st.session_state.syslite_interface = SySLiteInterface(Config.SYSLITE_DIR)
            
            # Claude (needs API key)
            if not st.session_state.get('claude_helper'):
                st.session_state.claude_helper = ClaudeAPIHelper()
            
            st.sidebar.success("✓ All tools initialized!")
        except Exception as e:
            st.sidebar.error(f"✗ Initialization error: {str(e)}")

def reset_session():
    """Reset all session state except tool initializations"""
    tools_to_keep = [
        'ocaml_interface',
        'nusmv_generator', 
        'syslite_interface',
        'claude_helper',
        'mode',
        'agentic_max_repair',
        'agentic_auto_advance',
        'agentic_show_details',
        'max_iterations'
    ]
    
    for key in list(st.session_state.keys()):
        if key not in tools_to_keep:
            del st.session_state[key]
    
    st.sidebar.success("✓ Session reset!")
    st.rerun()
def render_baseline_mode():
    """Render Baseline/Workflow Mode UI"""
    st.header("📋 Baseline/Workflow Mode")
    
    # Progress indicator
    steps = ["Input & AP Extraction", "Formula Generation", "Trace Generation", 
             "Evaluation", "Refinement", "Reintegration", "Reevaluation", "Summary"]
    current = st.session_state.current_step - 1
    
    progress_cols = st.columns(8)
    for i, (col, step) in enumerate(zip(progress_cols, steps)):
        with col:
            if i < current:
                st.success(f"✓ {i+1}")
            elif i == current:
                st.info(f"▶ {i+1}")
            else:
                st.text(f"  {i+1}")
    
    st.markdown("---")
    
    # Create tabs
    tabs = st.tabs([
        "1️⃣ Input & APs",
        "2️⃣ Formulas",
        "3️⃣ Traces",
        "4️⃣ Evaluation",
        "5️⃣ Refinement",
        "6️⃣ Reintegration",
        "7️⃣ Reevaluation",
        "8️⃣ Summary"        
    ])
    
    with tabs[0]:
        render_step1_ap_extraction()
    
    with tabs[1]:
        render_step2_formula_generation()
    
    with tabs[2]:
        render_step3_trace_generation()
    
    with tabs[3]:
        render_step4_evaluation()
    
    with tabs[4]:
        render_step5_refinement()
    
    with tabs[5]:
        render_step6_reintegration()
    
    with tabs[6]:
        render_step7_reevaluation()
    
    with tabs[7]:
        render_step8_summary()

def render_step1_ap_extraction():
    """Step 1: Extract Atomic Propositions"""
    st.subheader("Step 1: Atomic Proposition Extraction")
    
    st.markdown("""
    Enter your natural language requirement. The system will extract atomic propositions
    using the **maximal logical revelation** principle.
    """)
    
    # Example requirements
    with st.expander("📝 Example Requirements (Click to Use)", expanded=False):
        examples = {
            "Emergency Alert": "The alarm must sound whenever a failure is detected",
            "Traffic Light": "The light must stay green for at least 2 cycles before turning yellow",
            "Alarm Reset": "The alarm must be reset within 3 steps after it activates",
            "System Safety": "If the system is armed, then any detected motion triggers an alarm until disarmed",
            "Walking": "Go to the cafe, then stop by the bank, then go to McDonald's, but only after visiting the bank",
            "Data Persistence": "Data must be saved before the application terminates",
            "Request-Response": "Every request must eventually receive a response",
            "Mutual Exclusion": "At most one process can access the critical section at any time"
        }
        
        cols = st.columns(2)
        for idx, (name, req) in enumerate(examples.items()):
            with cols[idx % 2]:
                if st.button(f"📄 {name}", key=f"example_{idx}", use_container_width=True):
                    st.session_state.nl_requirement = req
                    st.session_state.nl_input_field = req
                    # Clear previous results
                    st.session_state.aps = []
                    st.session_state.detailed_formula = ''
                    st.session_state.python_formula = ''
                    st.session_state.traces = []
                    st.rerun()
        
        st.caption("Click any example to load it into the input field below")
    
    # Input
    nl_requirement = st.text_area(
        "Natural Language Requirement:",
        placeholder="Example: The alarm must sound whenever a failure is detected",
        height=120,
        value=st.session_state.nl_requirement,
        key='nl_input_field'
    )
    
    st.session_state.nl_requirement = nl_requirement
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🔍 Extract APs", type="primary", disabled=not nl_requirement):
            if st.session_state.claude_helper is None:
                st.error("⚠️ Please initialize Claude API first (see sidebar)")
            else:
                extract_aps(nl_requirement)
    
    with col2:
        if st.session_state.aps:
            if st.button("✓ Proceed to Step 2"):
                st.session_state.current_step = 2
                st.rerun()
    
    # Display results
    if st.session_state.aps:
        st.success("✓ Atomic Propositions Extracted")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("**Extracted APs:**")
            for ap in st.session_state.aps:
                st.code(ap, language="text")
        
        with col2:
            if st.session_state.aps_explanation:
                st.markdown("**Explanation:**")
                st.info(st.session_state.aps_explanation)

def render_step2_formula_generation():
    """Step 2: Generate LTL Formulas"""
    st.subheader("Step 2: LTL Formula Generation")
    
    if not st.session_state.aps:
        st.warning("⚠️ Please extract atomic propositions first (Step 1)")
        return
    
    st.markdown(f"""
    **Requirement:** {st.session_state.nl_requirement}
    
    **Using APs:** {', '.join(st.session_state.aps)}
    
    Generate formulas using two strategies:
    - **Detailed**: Direct LTL translation optimized for semantic accuracy
    - **Python**: AST-style representation converted to standard LTL
    """)
    
    col1, col2 = st.columns(2)
    
    # Detailed Strategy
    with col1:
        st.markdown("#### 🎯 Detailed Strategy")
        if st.button("Generate Detailed Formula", key='gen_detailed'):
            generate_detailed_formula()
        
        if st.session_state.detailed_formula:
            st.code(st.session_state.detailed_formula, language="text")
            
            # Show which APs are used
            used_aps = [ap for ap in st.session_state.aps if ap in st.session_state.detailed_formula]
            if used_aps:
                st.caption(f"✓ Uses APs: {', '.join(used_aps)}")
            else:
                st.warning(f"⚠️ Formula doesn't use expected APs: {', '.join(st.session_state.aps)}")
            
            if st.session_state.detailed_explanation:
                with st.expander("Explanation"):
                    st.write(st.session_state.detailed_explanation)
    
    # Python Strategy
    with col2:
        st.markdown("#### 🐍 Python Strategy")
        if st.button("Generate Python Formula", key='gen_python'):
            generate_python_formula()
        
        if st.session_state.python_formula:
            st.code(st.session_state.python_formula, language="text")
            
            # Show which APs are used
            used_aps = [ap for ap in st.session_state.aps if ap in st.session_state.python_formula]
            if used_aps:
                st.caption(f"✓ Uses APs: {', '.join(used_aps)}")
            else:
                st.warning(f"⚠️ Formula doesn't use expected APs: {', '.join(st.session_state.aps)}")
            
            if st.session_state.python_explanation:
                with st.expander("Explanation"):
                    st.write(st.session_state.python_explanation)
    
    # Proceed button
    if st.session_state.detailed_formula and st.session_state.python_formula:
        st.markdown("---")
        
        # Validate formulas before proceeding
        valid = True
        if not any(ap in st.session_state.detailed_formula for ap in st.session_state.aps):
            st.error("❌ Detailed formula doesn't use any of the extracted APs!")
            valid = False
        if not any(ap in st.session_state.python_formula for ap in st.session_state.aps):
            st.error("❌ Python formula doesn't use any of the extracted APs!")
            valid = False
        
        if valid:
            if st.button("✓ Proceed to Step 3", type="primary"):
                st.session_state.current_step = 3
                st.session_state.all_formulas['Detailed'] = st.session_state.detailed_formula
                st.session_state.all_formulas['Python'] = st.session_state.python_formula
                st.rerun()
        else:
            st.warning("⚠️ Please regenerate formulas to use the correct atomic propositions")

def render_step3_trace_generation():
    st.subheader("Step 3: Constraint Trace Generation")

    if not st.session_state.detailed_formula or not st.session_state.python_formula:
        st.warning("Run Step 2 to generate formulas first.")
        return
    
    if st.button("Generate Traces for All Constraints"):
        st.session_state.constraint_traces.clear()

        for name, flags in CONSTRAINTS.items():
            constraint = build_constraint_formula(
                st.session_state.detailed_formula,
                st.session_state.python_formula,
                flags
            )

            nusmv_input = generate_nusmv_model(constraint, st.session_state.aps)
            result = run_nusmv(nusmv_input)
            canonical_trace = nusmv_trace_to_canonical(
                result["raw"],
                st.session_state.aps
            )
            st.session_state.constraint_traces[name] = {
                "constraint_formula": constraint,
                "nusmv_input": nusmv_input,
                "trace": canonical_trace,
                "raw_output": result["raw"],
                "satisfiable": result["satisfiable"]
            }
        
        # Sync to step3_results
        st.session_state.step3_results = st.session_state.constraint_traces
    
    if st.session_state.constraint_traces:
        st.markdown("### 📋 Trace Summary")

        table = []
        for k, v in st.session_state.constraint_traces.items():
            table.append({
                "Constraint": k,
                "Trace": v["trace"] if v["trace"] else "UNSAT (universally satisfied)"

                # "Trace": v["trace"] if v["trace"] else "❌ No trace (UNSAT)"
            })

        st.table(table)

    # Display detailed view
    for name, art in st.session_state.constraint_traces.items():
        with st.expander(f"{name}  ({art['constraint_formula']})", expanded=False):
            st.code(art["nusmv_input"], language="text")

            if art["trace"]:
                st.success("Counterexample trace generated")
                st.code(art["trace"])
            else:
                st.info("UNSAT: no counterexample exists (universally satisfied)")


            st.markdown("**Raw NuSMV Output**")
            st.code(art["raw_output"], language="text")
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("← Back", key='step3_back'):
            st.session_state.current_step = 2
            st.rerun()
    
    with col2:
        if st.button("💾 Save Progress"):
            save_session_data("step3")
    
    with col3:
        if st.button("➡️ Evaluate", type="primary"):
            st.session_state.current_step = 4
            st.rerun()

def render_step4_evaluation():
    """
    Step 4: Semantic Evaluation with in-table Ground Truth editing
    """
    import pandas as pd
    
    st.header("Step 4: Semantic Evaluation (LLM Oracle + Ground Truth)")

    if not st.session_state.constraint_traces:
        st.warning("Run previous steps first.")
        return

    claude = st.session_state.claude_helper
    nl_req = st.session_state.nl_requirement

    if "semantic_oracle" not in st.session_state:
        st.session_state.semantic_oracle = {}

    if "semantic_ground_truth" not in st.session_state:
        st.session_state.semantic_ground_truth = {}

    # ----------------------------
    # Compute LLM Oracle (once per constraint)
    # ----------------------------
    for cname, art in st.session_state.constraint_traces.items():
        trace = art.get("trace")

        if cname not in st.session_state.semantic_oracle:
            if trace is None:
                oracle = {
                    "should_satisfy": True,
                    "reasoning": "UNSAT region — vacuously satisfies the requirement."
                }
            else:
                oracle = claude.get_trace_feedback(trace, nl_req)

            st.session_state.semantic_oracle[cname] = oracle

        # Initialize ground truth to LLM judgment if not set
        if cname not in st.session_state.semantic_ground_truth:
            oracle = st.session_state.semantic_oracle[cname]
            st.session_state.semantic_ground_truth[cname] = oracle["should_satisfy"]

    # ----------------------------
    # Render Table with In-Table Editing
    # ----------------------------
    st.markdown("### Evaluation Table")
    st.caption("LLM provides initial judgment. Edit Ground Truth using dropdowns in the last column.")
    
    # Table header
    header_cols = st.columns([1.5, 3, 0.5, 0.5, 1.2, 1.5])
    header_cols[0].markdown("**Constraint**")
    header_cols[1].markdown("**Trace**")
    header_cols[2].markdown("**D**")
    header_cols[3].markdown("**P**")
    header_cols[4].markdown("**LLM**")
    header_cols[5].markdown("**Ground Truth**")
    
    st.markdown("---")

    # Table rows with interactive Ground Truth selector
    table_data = []
    
    for cname, art in st.session_state.constraint_traces.items():
        trace = art.get("trace")
        oracle = st.session_state.semantic_oracle[cname]
        
        flags = CONSTRAINTS[cname]
        d_sat = not flags["negate_D"]
        p_sat = not flags["negate_P"]
        
        llm_judgment = oracle["should_satisfy"]
        is_unsat = (trace is None)
        
        # Create row
        row_cols = st.columns([1.5, 3, 0.5, 0.5, 1.2, 1.5])
        
        # Constraint name
        row_cols[0].markdown(f"**{cname}**")
        
        # Trace
        trace_display = "UNSAT" if is_unsat else (trace[:50] + "..." if len(trace) > 50 else trace)
        row_cols[1].markdown(f"`{trace_display}`")
        
        # D, P status
        row_cols[2].markdown("✓" if d_sat else "✗")
        row_cols[3].markdown("✓" if p_sat else "✗")
        
        # LLM judgment
        llm_text = "SATISFIES" if llm_judgment else "VIOLATES"
        if llm_judgment:
            row_cols[4].success(llm_text)
        else:
            row_cols[4].error(llm_text)
        
        # Ground Truth selector (IN-TABLE)
        if is_unsat:
            # UNSAT traces are always satisfied
            row_cols[5].success("✓ SATISFIES")
            st.session_state.semantic_ground_truth[cname] = True
        else:
            current_gt = st.session_state.semantic_ground_truth[cname]
            default_choice = "SATISFIES" if current_gt else "VIOLATES"
            
            choice = row_cols[5].selectbox(
                label=f"gt_{cname}",
                options=["SATISFIES", "VIOLATES"],
                index=0 if default_choice == "SATISFIES" else 1,
                key=f"gt_select_{cname}",
                label_visibility="collapsed"
            )
            
            st.session_state.semantic_ground_truth[cname] = (choice == "SATISFIES")
        
        # Store data for reasoning display
        table_data.append({
            "cname": cname,
            "llm_judgment": llm_text,
            "reasoning": oracle["reasoning"]
        })
        
        st.markdown("---")

    # ----------------------------
    # LLM Reasoning (Collapsible)
    # ----------------------------
    st.markdown("### 🔍 LLM Reasoning")
    
    for data in table_data:
        with st.expander(f"{data['cname']} — LLM: {data['llm_judgment']}"):
            st.markdown(data["reasoning"])

    st.success("✅ Evaluation complete. Ground truth set for all constraints.")

    # ----------------------------
    # Navigation
    # ----------------------------
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Back", key="step4_back"):
            st.session_state.current_step = 3
            st.rerun()

    with col2:
        if st.button("Next → Step 5", type="primary", key="step4_next"):
            st.session_state.current_step = 5
            st.rerun()        

def render_step5_refinement():
    st.header("Step 5: Formula Refinement")
    
    st.info("Formulas are misaligned. Choose a refinement method:")
    
    # Initialize refined formulas in session state
    if "refined_formulas" not in st.session_state:
        st.session_state.refined_formulas = []
    
    tab1, tab2 = st.tabs(["🤖 LLM Re-prompting", "🔬 SySLite Synthesis"])
    
    with tab1:
        st.markdown("### LLM Re-prompting")
        st.markdown("Generate a new formula by providing mismatch context to Claude")
        
        # Show previously generated LLM formulas
        llm_formulas = [f for f in st.session_state.refined_formulas if f["method"] == "LLM"]
        if llm_formulas:
            st.markdown("**Previously Generated (LLM):**")
            for i, rf in enumerate(llm_formulas):
                st.code(f"{i+1}. {rf['formula']}", language="text")
        
        if st.button("Generate Refined Formula (LLM)", type="primary", key="llm_refine_btn"):
            with st.spinner("Generating refined formula..."):
                # Collect mismatch info with user feedback
                mismatch_info = []
                for constraint, artifact in st.session_state.step3_results.items():
                    if artifact.get("trace"):
                        ground_truth = st.session_state.user_feedback_overrides.get(
                            constraint,
                            None
                        )
                        if ground_truth is not None:
                            feedback = "SHOULD satisfy" if ground_truth else "should NOT satisfy"
                            mismatch_info.append(
                                f"{constraint}: {artifact['trace'][:80]}... → {feedback}"
                            )
                
                claude = st.session_state.claude_helper
                prompt = f"""The current formulas don't match user intent.

Requirement: {st.session_state.nl_requirement}
APs: {', '.join(st.session_state.aps)}

User feedback on traces:
{chr(10).join(mismatch_info)}

Generate a NEW LTL formula that matches these expectations.
Use: G, F, X, U, ->, &, |, !

Return ONLY the formula."""
                
                response = claude.client.messages.create(
                    model=claude.model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                refined = response.content[0].text.strip()
                refined = re.sub(r'```.*?\n|```', '', refined)
                
                st.success("✅ Refined formula generated!")
                
                st.code(refined, language="text")
                
                st.session_state.refined_formulas.append({
                    "method": "LLM",
                    "formula": refined
                })
                st.rerun()
    
    with tab2:
        st.markdown("### SySLite Synthesis")
        st.markdown("Synthesize formula from positive/negative trace examples")
        
        # Show previously synthesized formulas
        syslite_formulas = [f for f in st.session_state.refined_formulas if f["method"] == "SySLite"]
        if syslite_formulas:
            st.markdown("**Previously Synthesized (SySLite):**")
            for i, rf in enumerate(syslite_formulas):
                st.code(f"{i+1}. {rf['formula']}", language="text")

        if st.button("Synthesize with SySLite", type="primary", key="syslite_synth_btn"):
            with st.spinner("Preparing traces..."):
                positive_traces = []
                negative_traces = []
                
                for constraint, artifact in st.session_state.step3_results.items():
                    trace = artifact.get("trace")
                    if not trace:
                        continue
                    
                    # Convert to SySLite format
                    syslite_trace = trace_to_syslite_format(
                        trace,
                        st.session_state.aps
                    )
                    
                    # Get ground truth (user override)
                    ground_truth = st.session_state.semantic_ground_truth.get(constraint)

                    
                    if ground_truth is None:
                        # Fall back to LLM feedback
                        oracle = st.session_state.semantic_oracle.get(constraint)

                        if oracle is None:
                            continue  # safety

                        ground_truth = oracle["should_satisfy"]

                    if ground_truth:
                        positive_traces.append(syslite_trace)
                    else:
                        negative_traces.append(syslite_trace)
                
                st.write(f"**Positive traces:** {len(positive_traces)}")
                st.write(f"**Negative traces:** {len(negative_traces)}")
                if len(positive_traces) == 0:
                    st.error(
                        "❌ SySLite requires at least ONE positive trace.\n\n"
                        "All traces are currently labeled negative.\n"
                        "Please revise semantic judgments or add a positive example."
                    )
                    st.stop()

                if len(negative_traces) == 0:
                    st.error(
                        "❌ SySLite requires at least ONE negative trace.\n\n"
                        "All traces are currently labeled positive."
                    )
                    st.stop()
                with st.expander("Trace Details"):
                    for i, t in enumerate(positive_traces):
                        st.code(f"Positive {i+1}: {t}", language="text")
                    for i, t in enumerate(negative_traces):
                        st.code(f"Negative {i+1}: {t}", language="text")
            
            with st.spinner("Running SySLite (may take 1-2 minutes)..."):
                syslite = SySLiteWrapper()
                formulas, debug_output, trace_file = syslite.synthesize(
                    positive_traces,
                    negative_traces,
                    st.session_state.aps,
                    size=5
                )
            
            # Show debug output
            with st.expander("🔍 SySLite Debug Output", expanded=True):
                st.code(debug_output, language="text")
                st.info(f"Trace file saved at: {trace_file}")
            
            if formulas:
                st.success(f"✅ Synthesized {len(formulas)} formulas!")
                
                # Convert AST formulas to standard LTL
                for i, formula in enumerate(formulas):
                    standard_formula = convert_ast_to_standard_ltl(formula)
                    st.markdown(f"**{i+1}. Original:** `{formula}`")
                    if standard_formula != formula:
                        st.markdown(f"**   Standard:** `{standard_formula}`")
                    else:
                        st.markdown(f"**   (Already standard)**")
                    st.markdown("---")
                    
                    # Store standard version
                    if not any(f["formula"] == standard_formula and f["method"] == "SySLite" 
                              for f in st.session_state.refined_formulas):
                        st.session_state.refined_formulas.append({
                            "method": "SySLite",
                            "formula": standard_formula,
                            "original": formula if standard_formula != formula else None
                        })
                st.rerun()
            else:
                st.error("❌ No formulas synthesized - check debug output above")
    
    # Show all refined formulas
    if not st.session_state.refined_formulas:
        st.info("ℹ️ No refined formulas yet. Generate one above to continue.")
        st.stop()

    labels = [
        f"[{rf['method']}] {rf['formula']}"
        for rf in st.session_state.refined_formulas
    ]
    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("← Back", key="refine_back"):
            st.session_state.current_step = 4
            st.rerun()
    with col2:
        if st.button("💾 Save Progress", key="refine_save"):
            st.success("✅ Progress saved!")
    with col3:
        if st.button("Reintegration →", type="primary", key="refine_summary"):
            st.session_state.current_step = 6
            st.rerun()

def render_step6_reintegration():
    st.subheader("Step 6: Reintegration")

    if not st.session_state.get("refined_formulas"):
        st.warning("Complete Step 5 first.")
        return

    # -----------------------------
    # Filter valid refinements
    # -----------------------------
    valid = [
        rf for rf in st.session_state.refined_formulas
        if isinstance(rf.get("formula"), str) and rf["formula"].strip()
    ]

    if not valid:
        st.error("No valid refined formulas available.")
        return

    st.markdown("### Select Refined Formula")

    labels = [
        f"{i+1}. {rf['method']}: {rf['formula'][:70]}..."
        for i, rf in enumerate(valid)
    ]

    selected = st.radio(
        "Choose formula:",
        range(len(labels)),
        format_func=lambda i: labels[i],
        key="refined_formula_selection"
    )

    # Store the selected index for later reference
    st.session_state.selected_refined_index = selected
    
    chosen = valid[selected]
    st.success("✅ Selected Formula:")
    st.code(chosen["formula"])

    # -----------------------------
    # Generate 2³ traces
    # -----------------------------
    if st.button("🔄 Generate 2³ Traces", type="primary"):
        formulas = {
            "D": st.session_state.detailed_formula,
            "P": st.session_state.python_formula,
            "R": chosen["formula"]
        }

        # Store the selected R formula explicitly
        st.session_state.selected_R_formula = chosen["formula"]
        st.session_state.selected_R_method = chosen["method"]

        constraints = generate_truth_table_constraints(formulas, max_formulas=3)
        st.session_state.reintegrated_traces = {}

        progress = st.progress(0.0)

        for i, c in enumerate(constraints):
            nusmv = generate_nusmv_model(c["formula"], st.session_state.aps)
            result = run_nusmv(nusmv)
            trace = nusmv_trace_to_canonical(result["raw"], st.session_state.aps)

            st.session_state.reintegrated_traces[c["name"]] = {
                "constraint_formula": c["formula"],
                "trace": trace,
                "satisfiable": result["satisfiable"],
                "negation_flags": c["negation_flags"]
            }

            progress.progress((i + 1) / len(constraints))

        st.session_state.step_6_complete = True
        st.success("✅ 2³ traces generated!")
        st.info("Go to **Step 7: Eval (2³)** tab to evaluate!")
        st.rerun()
    
    # Show preview
    if st.session_state.get("reintegrated_traces"):
        st.markdown("### Generated Traces")
        for name, art in st.session_state.reintegrated_traces.items():
            with st.expander(f"{name}"):
                if art["trace"]:
                    st.code(art["trace"])
                else:
                    st.warning("UNSATISFIABLE")
    
    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("← Back", key="step6_refine_back"):
            st.session_state.current_step = 5
            st.rerun()
    with col2:
        if st.button("💾 Save Progress", key="step6_refine_save"):
            st.success("✅ Progress saved!")
    with col3:
        if st.button("Re-evaluation →", type="primary", key="step6_refine_summary"):
            st.session_state.current_step = 7
            st.rerun()

def render_step7_reevaluation():
    """
    Step 7 — Single-Candidate Iterative Repair (FINAL, STABLE)
    - LLM = soft oracle (one-shot)
    - User = semantic ground truth
    - ALL interaction rendered IN-TABLE using st.columns layout
    """

    st.header("Step 7: Semantic Re-evaluation (D / P / R)")
    st.caption("LLM pre-fills judgment. User may override. UNSAT rows are auto-satisfied.")

    # -------------------------------------------------
    # Preconditions
    # -------------------------------------------------
    if not st.session_state.get("reintegrated_traces"):
        st.warning("Complete Step 6 first.")
        return

    # -------------------------------------------------
    # Safe, total initialization
    # -------------------------------------------------
    if "semantic_oracle" not in st.session_state:
        st.session_state.semantic_oracle = {}

    for cname, oracle in st.session_state.semantic_oracle.items():
        if "should_satisfy" not in oracle:
            st.session_state.semantic_oracle[cname] = {
                "should_satisfy": oracle.get("llm_label", True),
                "reasoning": oracle.get("reasoning", "")
            }

    st.session_state.setdefault("semantic_ground_truth", {})
    st.session_state.setdefault("user_overrides", {})
    st.session_state.setdefault("final_formula", None)

    claude = st.session_state.claude_helper
    nl_req = st.session_state.nl_requirement
    traces = st.session_state.reintegrated_traces

    # -------------------------------------------------
    # Render table header
    # -------------------------------------------------
    st.markdown("### Constraint Evaluation Table")
    header_cols = st.columns([2, 3, 0.5, 0.5, 0.5, 1.5])
    header_cols[0].markdown("**Constraint**")
    header_cols[1].markdown("**Trace**")
    header_cols[2].markdown("**D**")
    header_cols[3].markdown("**P**")
    header_cols[4].markdown("**R**")
    header_cols[5].markdown("**Ground Truth**")
    
    st.markdown("---")

    # -------------------------------------------------
    # Build rows with IN-TABLE interaction
    # -------------------------------------------------
    table_data = []
    
    for cname, art in traces.items():
        trace = art.get("trace")
        flags = art.get("negation_flags", {})

        d_sat = not flags.get("D", True)
        p_sat = not flags.get("P", True)
        r_sat = not flags.get("R", True)

        # ---------- LLM oracle (cached once) ----------
        if cname not in st.session_state.semantic_oracle:
            if trace is None:
                st.session_state.semantic_oracle[cname] = {
                    "should_satisfy": True,
                    "reasoning": "UNSAT region (vacuously satisfied)"
                }
            else:
                llm_label, reasoning = claude.get_trace_feedback(
                    trace_description=trace,
                    nl_requirement=nl_req
                )
                st.session_state.semantic_oracle[cname] = {
                    "should_satisfy": llm_label,
                    "reasoning": reasoning
                }

        llm_label = st.session_state.semantic_oracle[cname]["should_satisfy"]

        # ---------- Render row with columns ----------
        row_cols = st.columns([2, 3, 0.5, 0.5, 0.5, 1.5])
        
        # Constraint name
        row_cols[0].markdown(f"**{cname}**")
        
        # Trace
        trace_display = trace if trace else "*UNSAT*"
        row_cols[1].markdown(f"`{trace_display}`")
        
        # D, P, R status
        row_cols[2].markdown("✓" if d_sat else "✗")
        row_cols[3].markdown("✓" if p_sat else "✗")
        row_cols[4].markdown("✓" if r_sat else "✗")
        
        # Ground truth selector (IN-TABLE)
        if trace is None:
            gt = True
            row_cols[5].success("✓ (UNSAT)")
        else:
            default = "Satisfies" if llm_label else "Violates"
            choice = row_cols[5].selectbox(
                label=f"gt_{cname}",
                options=["Satisfies", "Violates"],
                index=0 if default == "Satisfies" else 1,
                key=f"gt_{cname}",
                label_visibility="collapsed"
            )
            gt = (choice == "Satisfies")

            if gt != llm_label:
                st.session_state.user_overrides[cname] = gt

        st.session_state.semantic_ground_truth[cname] = gt
        
        # Store data for alignment check
        table_data.append({
            "Constraint": cname,
            "D": d_sat,
            "P": p_sat,
            "R": r_sat,
            "GT": gt
        })
        
        st.markdown("---")

    # -------------------------------------------------
    # Alignment check (SINGLE candidate logic)
    # -------------------------------------------------
    aligned = {
        "D": all(row["D"] == row["GT"] for row in table_data),
        "P": all(row["P"] == row["GT"] for row in table_data),
        "R": all(row["R"] == row["GT"] for row in table_data),
    }

    st.subheader("Alignment Status")
    c1, c2, c3 = st.columns(3)

    # Handle D
    if aligned["D"]:
        c1.success("D aligned")
        c1.balloons()
    else:
        c1.error("D misaligned")

    # Handle P
    if aligned["P"]:
        c2.success("P aligned")
        c1.balloons()
    else:
        c2.error("P misaligned")

    # Handle R
    if aligned["R"]:
        c3.success("R aligned")
        c1.balloons()
    else:
        c3.error("R misaligned")
    # -------------------------------------------------
    # Decision logic (NO loops, NO hidden refinement)
    # -------------------------------------------------
    st.markdown("---")

    if aligned["R"]:
        st.success("🎉 Repaired formula semantically aligned.")
        st.session_state.final_formula = "R"

        if st.button("Finalize → Summary", type="primary"):
            st.session_state.current_step = 8
            st.rerun()
    else:
        st.error(
            "❌ Repaired formula still misaligned.\n\n"
            "Single-candidate repair bound reached.\n"
            "Please revise the requirement."
        )

    # -------------------------------------------------
    # Navigation
    # -------------------------------------------------
    col1, col2 = st.columns(2)
    if col1.button("← Back to Step 6"):
        st.session_state.current_step = 6
        st.rerun()
    if col2.button("Save Progress"):
        st.success("Progress saved.")

def render_step8_summary():
    """
    Step 8 — Final Summary (READ-ONLY, AUTHORITATIVE)
    Shows only selected refined formula, others are collapsible
    """
    import pandas as pd

    st.header("Step 8: Final Verification Summary")

    # -------------------------------------------------
    # Requirement
    # -------------------------------------------------
    st.subheader("1. Natural Language Requirement")
    st.info(st.session_state.get("nl_requirement", "N/A"))

    # -------------------------------------------------
    # Atomic Propositions
    # -------------------------------------------------
    st.subheader("2. Atomic Propositions")
    st.code(", ".join(st.session_state.get("aps", [])))

    # -------------------------------------------------
    # Formulas
    # -------------------------------------------------
    st.subheader("3. Candidate & Derived Formulas")

    st.markdown("**Initial LLM Candidates**")
    st.code(st.session_state.get("detailed_formula", "N/A"), language="text")
    st.code(st.session_state.get("python_formula", "N/A"), language="text")

    
    # -------------------------------------------------
    # Step 4 Ground Truth Summary
    # -------------------------------------------------
    st.subheader("4. Step 4: Initial Ground Truth (D & P)")

    rows = []
    gt = st.session_state.get("semantic_ground_truth", {})
    oracle = st.session_state.get("semantic_oracle", {})

    for cname, art in st.session_state.get("constraint_traces", {}).items():
        is_unsat = art.get("trace") is None
        flags = CONSTRAINTS[cname]
        
        # Get user's ground truth (from Step 4)
        user_gt = gt.get(cname, True)
        
        # Get LLM judgment for comparison
        llm_judgment = oracle.get(cname, {}).get("should_satisfy", True)

        rows.append({
            "Constraint": cname,
            "Trace": "UNSAT" if is_unsat else "SAT",
            "D": "✓" if not flags["negate_D"] else "✗",
            "P": "✓" if not flags["negate_P"] else "✗",
            "LLM": "✓" if llm_judgment else "✗",
            "Ground Truth": "✓" if user_gt else "✗"
        })

    if rows:
        df = pd.DataFrame(rows)[["Constraint", "D", "P", "LLM", "Ground Truth"]]
        st.dataframe(df, hide_index=True, use_container_width=True)
    
    st.markdown("**Refined / Synthesized (R)**")

    # Get all refined formulas
    refined = [
        f for f in st.session_state.get("refined_formulas", [])
        if f["method"] in {"LLM", "SySLite"}
    ]

    # Get the selected formula from reintegrated_traces
    selected_formula = None
    if st.session_state.get("reintegrated_traces"):
        # Extract the R formula from any trace (they all use the same R)
        for cname, art in st.session_state.reintegrated_traces.items():
            if "R" in art.get("negation_flags", {}):
                # Parse the constraint to get R formula
                # The constraint_formula contains the combination, we need to extract R
                pass
        
        # Alternative: check if we stored the selected index
        if "selected_refined_index" in st.session_state:
            selected_idx = st.session_state.selected_refined_index
            if 0 <= selected_idx < len(refined):
                selected_formula = refined[selected_idx]

    if selected_formula:
        # Show selected formula prominently
        st.success("**Selected Formula (Used in Evaluation):**")
        st.code(f"{selected_formula['method']}: {selected_formula['formula']}", language="text")
        
        # Show other formulas in expander
        other_formulas = [f for f in refined if f != selected_formula]
        if other_formulas:
            with st.expander("📋 View All Other Refined Formulas"):
                for i, f in enumerate(other_formulas):
                    st.code(f"{i+1}. {f['method']}: {f['formula']}", language="text")
    elif refined:
        # Fallback: show all if we can't determine selected
        st.warning("Could not determine selected formula. Showing all:")
        for i, f in enumerate(refined):
            st.code(f"{i+1}. {f['method']}: {f['formula']}", language="text")
    else:
        st.warning("No repaired formulas generated.")

    # -------------------------------------------------
    # Step 7 Final Evaluation (2³ traces)
    # -------------------------------------------------
    st.subheader("5. Step 7: Final Evaluation (D, P, R)")

    rows = []
    gt = st.session_state.get("semantic_ground_truth", {})

    for cname, art in st.session_state.get("reintegrated_traces", {}).items():
        flags = art.get("negation_flags", {})
        user_gt = gt.get(cname, True)
        
        rows.append({
            "Constraint": cname,
            "D": "✓" if not flags.get("D", True) else "✗",
            "P": "✓" if not flags.get("P", True) else "✗",
            "R": "✓" if not flags.get("R", True) else "✗",
            "Ground Truth": "✓" if user_gt else "✗"
        })

    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.warning("No Step 7 evaluation data available.")

    # -------------------------------------------------
    # Restart
    # -------------------------------------------------
    st.markdown("---")
    if st.button("🔄 Start New Session", type="primary"):
        for k in list(st.session_state.keys()):
            if k != "claude_helper":
                del st.session_state[k]
        st.session_state.current_step = 0
        st.rerun()


from agentic import run_agentic_pipeline

def render_agentic_mode():
    """Enhanced agentic mode UI for Streamlit - adapted from baseline UI"""
    import streamlit as st
    
    st.header("🤖 Agentic Mode (CrewAI)")
    st.caption("Automated formalization-verification-repair with multi-agent system")
    
    # Example requirements section (like baseline)
    with st.expander("📝 Example Requirements (Click to Use)", expanded=False):
        examples = {
            "Emergency Alert": "The alarm must sound whenever a failure is detected",
            "Traffic Light": "The light must stay green for at least 2 cycles before turning yellow",
            "Alarm Reset": "The alarm must be reset within 3 steps after it activates",
            "System Safety": "If the system is armed, then any detected motion triggers an alarm until disarmed",
            "Walking": "Go to the cafe, then stop by the bank, then go to McDonald's, but only after visiting the bank",
            "Data Persistence": "Data must be saved before the application terminates",
            "Request-Response": "Every request must eventually receive a response",
            "Mutual Exclusion": "At most one process can access the critical section at any time"
        }
        
        cols = st.columns(2)
        for idx, (name, req) in enumerate(examples.items()):
            with cols[idx % 2]:
                if st.button(f"📄 {name}", key=f"agentic_example_{idx}", use_container_width=True):
                    st.session_state.nl_requirement = req
                    st.session_state.agentic_nl_input = req
                    # Clear previous agentic results
                    if "agentic_results" in st.session_state:
                        del st.session_state.agentic_results
                    st.rerun()
        
        st.caption("Click any example to load it into the input field below")
    
    # Input section
    nl_req = st.text_area(
        "Natural Language Requirement:",
        placeholder="Example: The alarm must sound whenever a failure is detected",
        height=120,
        value=st.session_state.get("nl_requirement", ""),
        key='agentic_nl_input'
    )
    
    st.session_state.nl_requirement = nl_req
    
    # Check prerequisites
    if not nl_req:
        st.info("👆 Please enter a natural language requirement above")
        return
    
    if not st.session_state.get("claude_helper"):
        st.error("⚠️ Please initialize Claude API first (see sidebar)")
        return
    
    claude_helper = st.session_state.claude_helper
    
    st.markdown("---")
    st.info(f"**Requirement:** {nl_req}")
    
    # Get configuration from sidebar
    max_repair = st.session_state.get('agentic_max_repair', 3)
    auto_advance = st.session_state.get('agentic_auto_advance', True)
    show_details = st.session_state.get('agentic_show_details', True)
    
    # Run pipeline button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 Run Agentic Pipeline", type="primary", use_container_width=True):
            with st.spinner("🤖 Running multi-agent pipeline..."):
                try:
                    results = run_agentic_pipeline(nl_req, claude_helper, max_repair_attempts=max_repair)
                    st.session_state.agentic_results = results
                    
                    # Store results in session state for other steps
                    st.session_state.aps = results["aps"]
                    st.session_state.detailed_formula = results["formulas"]["D"]
                    st.session_state.python_formula = results["formulas"]["P"]
                    st.session_state.constraint_traces = results["traces"]
                    st.session_state.semantic_oracle = results["semantic_evaluation"]
                    st.session_state.semantic_ground_truth = results["ground_truth"]
                    
                    if results["refined_formulas"]:
                        if "refined_formulas" not in st.session_state:
                            st.session_state.refined_formulas = []
                        st.session_state.refined_formulas.extend(results["refined_formulas"])
                    
                    st.success("✅ Agentic pipeline completed!")
                except Exception as e:
                    st.error(f"❌ Pipeline error: {str(e)}")
                    st.exception(e)
            
            st.rerun()
    
    # Display results (if pipeline has been run)
    if "agentic_results" not in st.session_state:
        st.info("👆 Click 'Run Agentic Pipeline' to start automated workflow")
        return
    
    results = st.session_state.agentic_results
    
    # Progress indicator
    st.markdown("---")
    st.markdown("### 📊 Pipeline Progress")
    
    progress_steps = [
        ("ap_extraction", "1. APs"),
        ("formula_generation", "2. Formulas"),
        ("trace_generation", "3. Traces"),
        ("semantic_evaluation", "4. Evaluation"),
        ("repair", "5. Repair"),
        ("reintegration", "6. Reintegration"),
        ("reevaluation", "7. Re-eval")
    ]
    
    completed_steps = [log["step"] for log in results["execution_log"] if log["status"] == "completed"]
    
    progress_cols = st.columns(len(progress_steps))
    for i, (col, (step_key, step_name)) in enumerate(zip(progress_cols, progress_steps)):
        with col:
            if step_key in completed_steps:
                st.success(f"✓ {step_name}")
            else:
                st.text(f"  {step_name}")
    
    st.markdown("---")
    
    # Enhanced status overview
    status = results["final_status"]
    
    if status == "fully_aligned":
        st.success("### 🎉 SUCCESS: Repaired Formula (R) is Fully Aligned!")
        st.info("The refined formula has been reintegrated and evaluated. All constraints are satisfied.")
        if auto_advance:
            st.balloons()
    elif status == "aligned":
        st.success("### ✅ SUCCESS: Initial Formulas are Aligned!")
        st.info("No refinement needed. D and P formulas match ground truth.")
    elif status == "partially_aligned":
        st.warning("### ⚠️ PARTIAL: Refined Formulas Generated")
        st.info("Misalignments detected. Repair attempted. Review refined formulas and reintegration results.")
    else:
        st.error("### ❌ REVIEW NEEDED: Significant Misalignments")
        st.info("Automatic repair failed. Manual intervention recommended.")
    
    # Create tabs for organized results display
    result_tabs = st.tabs([
        "📊 Overview",
        "🔬 Formulas & APs",
        "📋 Traces (2²)",
        "⚠️ Evaluation",
        "🔧 Refined Formulas",
        "🔄 Reintegration (2³)"
    ])
    
    # Tab 1: Overview
    with result_tabs[0]:
        st.markdown("### Quick Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Atomic Propositions", len(results["aps"]))
        
        with col2:
            st.metric("Traces Generated", len(results["constraint_traces"]))
        
        with col3:
            sat_count = sum(1 for t in results["constraint_traces"].values() if t["satisfiable"])
            st.metric("SAT Traces", sat_count)
        
        with col4:
            st.metric("Misalignments", len(results["misalignments"]))
        
        st.markdown("---")
        
        # Show atomic propositions
        st.markdown("**Extracted Atomic Propositions:**")
        st.code(", ".join(results["aps"]), language="text")
        
        if results.get("aps_explanation"):
            with st.expander("🔍 AP Extraction Reasoning"):
                st.info(results["aps_explanation"])
        
        st.markdown("---")
        
        # Show generated formulas
        st.markdown("**Generated Formulas:**")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**D (Detailed):**")
            st.code(results["formulas"]["D"], language="text")
        with col2:
            st.markdown("**P (Python):**")
            st.code(results["formulas"]["P"], language="text")
    
    # Tab 2: Formulas & APs (detailed)
    with result_tabs[1]:
        st.markdown("### 📝 Formula Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Detailed Formula (D)")
            st.code(results["formulas"]["D"], language="text")
            if results.get("formula_explanations", {}).get("D"):
                st.markdown("**Explanation:**")
                st.info(results["formula_explanations"]["D"])
        
        with col2:
            st.markdown("#### Python Formula (P)")
            st.code(results["formulas"]["P"], language="text")
            if results.get("formula_explanations", {}).get("P"):
                st.markdown("**Explanation:**")
                st.info(results["formula_explanations"]["P"])
        
        st.markdown("---")
        
        st.markdown("### 🔤 Atomic Propositions")
        st.code(", ".join(results["aps"]), language="text")
        
        if results.get("aps_explanation"):
            st.markdown("**Extraction Logic:**")
            st.info(results["aps_explanation"])
    
    # Tab 3: Traces Table (like baseline Step 3)
    with result_tabs[2]:
        st.markdown("### 📋 Constraint Traces Summary")
        st.caption("Generated traces for all 2² = 4 constraint combinations")
        
        import pandas as pd
        from utils import CONSTRAINTS
        
        # Build table data
        table_data = []
        for cname, trace_data in results["constraint_traces"].items():
            flags = CONSTRAINTS[cname]
            
            table_data.append({
                "Constraint": cname,
                "D": "✓" if not flags["negate_D"] else "✗",
                "P": "✓" if not flags["negate_P"] else "✗",
                "Satisfiable": "✓ SAT" if trace_data["satisfiable"] else "✗ UNSAT",
                "Trace": trace_data["trace"][:80] + "..." if trace_data["trace"] else "UNSAT (universally satisfied)"
            })
        
        # Display table
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### 🔍 Detailed Trace View")
        
        # Show detailed traces in expanders (like baseline)
        for cname, trace_data in results["constraint_traces"].items():
            with st.expander(f"{cname} — {trace_data['constraint_formula'][:60]}..."):
                st.markdown("**Constraint Formula:**")
                st.code(trace_data["constraint_formula"], language="text")
                
                if trace_data["trace"]:
                    st.success("✓ Counterexample trace generated")
                    st.markdown("**Canonical Trace:**")
                    st.code(trace_data["trace"], language="text")
                else:
                    st.info("✓ UNSAT: No counterexample exists (universally satisfied)")
                
                with st.expander("Raw NuSMV Output"):
                    st.code(trace_data["raw_output"], language="text")
    
    # Tab 4: Evaluation Results
    with result_tabs[3]:
        st.markdown("### ⚙️ Semantic Evaluation")
        
        import pandas as pd
        from utils import CONSTRAINTS
        
        # Build evaluation table
        eval_data = []
        for cname, trace_data in results["constraint_traces"].items():
            flags = CONSTRAINTS[cname]
            oracle = results["semantic_oracle"].get(cname, {})
            gt = results["semantic_ground_truth"].get(cname, True)
            
            d_sat = not flags["negate_D"]
            p_sat = not flags["negate_P"]
            llm_judgment = oracle.get("should_satisfy", True)
            
            # Check if aligned
            d_aligned = (d_sat == gt)
            p_aligned = (p_sat == gt)
            
            eval_data.append({
                "Constraint": cname,
                "D": "✓" if d_sat else "✗",
                "P": "✓" if p_sat else "✗",
                "LLM": "✓" if llm_judgment else "✗",
                "Ground Truth": "✓" if gt else "✗",
                "D Aligned": "✓" if d_aligned else "❌",
                "P Aligned": "✓" if p_aligned else "❌"
            })
        
        df = pd.DataFrame(eval_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Show misalignments if any
        if results["misalignments"]:
            st.warning(f"### ⚠️ {len(results['misalignments'])} Misalignments Detected")
            
            for m in results["misalignments"]:
                with st.expander(f"❌ {m['constraint']} — Formula: {m['formula']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Expected (Ground Truth):**")
                        st.markdown("✓ Satisfies" if m['expected'] else "✗ Violates")
                    with col2:
                        st.markdown("**Actual (Formula Result):**")
                        st.markdown("✓ Satisfies" if m['actual'] else "✗ Violates")
                    
                    if m.get("trace"):
                        st.markdown("**Trace:**")
                        st.code(m["trace"][:200] + "..." if len(m["trace"]) > 200 else m["trace"], language="text")
        else:
            st.success("### ✅ No Misalignments — Formulas are Aligned!")
        
        st.markdown("---")
        
        # Show LLM reasoning
        st.markdown("### 🔍 LLM Reasoning for Each Constraint")
        for cname, oracle in results["semantic_oracle"].items():
            judgment = "SATISFIES" if oracle.get("should_satisfy", True) else "VIOLATES"
            icon = "✅" if oracle.get("should_satisfy", True) else "❌"
            
            with st.expander(f"{icon} {cname} — LLM: {judgment}"):
                st.markdown(oracle.get("reasoning", "No reasoning provided"))
    
    # Tab 5: Refined Formulas
    with result_tabs[4]:
        st.markdown("### 🔧 Refined Formulas")
        
        if not results["refined_formulas"]:
            st.info("No refined formulas generated (none needed or repair failed)")
        else:
            st.success(f"Generated {len(results['refined_formulas'])} refined formulas")
            
            for i, rf in enumerate(results["refined_formulas"]):
                st.markdown(f"**{i+1}. Method: {rf['method']}**")
                st.code(rf['formula'], language="text")
                
                if rf.get("original"):
                    st.caption(f"Original formula: {rf['original']}")
                
                st.markdown("---")
    
    # Navigation section
    st.markdown("---")
    st.markdown("### 🧭 Next Steps")
    
    nav_col1, nav_col2, nav_col3 = st.columns(3)
    
    with nav_col1:
        if st.button("🔄 Re-run Pipeline", use_container_width=True):
            if "agentic_results" in st.session_state:
                del st.session_state.agentic_results
            st.rerun()
    
    with nav_col2:
        if st.button("📋 Switch to Baseline", use_container_width=True):
            st.session_state.mode = "baseline"
            if results["refined_formulas"]:
                # If refined formulas exist, start at Step 5 for review
                st.session_state.current_step = 5
            else:
                # Otherwise start at Step 4 to review evaluations
                st.session_state.current_step = 4
            st.rerun()
    
    with nav_col3:
        # Show appropriate next action based on status
        if status == "aligned":
            if st.button("→ View Summary (Step 8)", type="primary", use_container_width=True):
                st.session_state.mode = "baseline"
                st.session_state.current_step = 8
                st.rerun()
        elif results["refined_formulas"]:
            if st.button("→ Review Refinements (Step 5)", type="primary", use_container_width=True):
                st.session_state.mode = "baseline"
                st.session_state.current_step = 5
                st.info("💡 You can review and select refined formulas in Step 5, then proceed to Step 6 for reintegration.")
                st.rerun()
        else:
            if st.button("→ Manual Refinement (Step 5)", type="primary", use_container_width=True):
                st.session_state.mode = "baseline"
                st.session_state.current_step = 5
                st.rerun()