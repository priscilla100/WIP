import streamlit as st
import json
import subprocess
import os
import re
import time
import pandas as pd
import ast
from anthropic import Anthropic
from datetime import datetime
from dotenv import load_dotenv
import PyPDF2
from io import BytesIO
from utils.utils import EXPERIMENTS, display_simple_result,display_agent4_result,display_experiment_result, experiment_baseline, experiment_rag, experiment_agent4compliance,MultiRegulationPipeline
# from utils.crewai_agent_system import ComplianceAgentSystem
from utils.rag_csv_export import RAGPolicyExporter
from utils.crewai_policy import multi_agent_compliance_system
load_dotenv()

st.set_page_config(
    page_title="Agent4Compliance", 
    page_icon="⚖️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

PRECIS_PATH = os.environ.get(
    "PRECIS_PATH",
    "/Users/priscilladanso/Documents/STONYBROOK/RESEARCH/TOWARDDISSERTATION/IMPLEMENTATION/policy_checker/precis"
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Initialize agent system

# agent_system = ComplianceAgentSystem(
#     precis_path=PRECIS_PATH,
#     rag_csv_path=None,  # Will be created/used if available
#     anthropic_key=ANTHROPIC_API_KEY
# )
    
# ============================================
# SESSION STATE INITIALIZATION
# ============================================

if 'page' not in st.session_state:
    st.session_state.page = 'Compliance Checker'

if 'facts' not in st.session_state:
    st.session_state.facts = []
if 'processing_results' not in st.session_state:
    st.session_state.processing_results = None

if 'last_uploaded_file' not in st.session_state:
    st.session_state.last_uploaded_file = None

# ============================================
# SIDEBAR NAVIGATION
# ============================================

with st.sidebar:
    st.markdown("# ⚖️ Agent4Compliance")
    st.markdown("---")
    
    # Page Navigation
    st.markdown("## 📑 Navigation")
    page = st.radio(
        "Select Page:",
        ["Compliance Checker", "Document → FOTL", "What-If Simulator", "System Status"],
        key='page_selector'
    )
    st.markdown("---")
    if page == "Compliance Checker":
        st.sidebar.info("🤖 Agent mode uses CrewAI for reasoning and tool use")
        
        # Show agent status
        with st.sidebar.expander("👥 Active Agents"):
            st.markdown("""
            1. **Fact Extractor** - Extracts entities/relationships
            2. **Policy Researcher** - Searches regulations
            3. **Logic Translator** - Converts to FOTL
            4. **Verification Agent** - Runs Précis
            5. **Explainer** - Generates answer
            """)

    st.markdown("---")
    st.markdown("## 🌐 Supported Regulations")
    st.markdown("- ✅ HIPAA (US Healthcare)")
    st.markdown("- ✅ GDPR (EU Data Protection)")
    st.markdown("- ✅ CCPA (California Privacy)")
    
    st.markdown("---")
    # API Configuration
    st.markdown("## ⚙️ Configuration")
    api_key = st.text_input("Anthropic API Key", value=ANTHROPIC_API_KEY or "", type="password")
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key
    
    st.markdown("---")
    
    # Quick Stats
    st.markdown("## 📊 Quick Stats")
    st.metric("Active Session", "✅")
    st.metric("Précis Engine", "Ready")

# ============================================
# PAGE 1: COMPLIANCE CHECKER
# ============================================

if page == "Compliance Checker":
    st.markdown("# 🔍 Compliance Checker")
    st.markdown("Ask questions about HIPAA compliance and get formal verification")
    
    # Example queries
    with st.expander("💡 Example Questions"):
        examples = [
            "Can a hospital share patient data with researchers?",
            "Is consent required for treatment-related uses of PHI?",
            "Can my grandma get my x-ray scan?",
            "Can hospitals share data with business associates?",
            "Must covered entities have a privacy officer?",
        ]
        for ex in examples:
            if st.button(ex, key=f"ex_{ex}"):
                st.session_state.query_input = ex
    
    # Query input
    query = st.text_area(
        "Your Compliance Question:",
        value=st.session_state.get('query_input', ''),
        height=100,
        placeholder="e.g., Can a hospital share patient data with researchers?"
    )
    col1, col2, col3, col4 = st.columns(4)
    exp1 = col1.checkbox("Baseline", value=True)
    exp2 = col2.checkbox("RAG", value=True)
    exp3 = col3.checkbox("Pipeline", value=True)
    exp4 = col4.checkbox("Agentic ⭐", value=True)

    if st.button("🚀 Check Compliance", type="primary"):
        if not query.strip():
            st.warning("⚠️ Please enter a question")

        elif not ANTHROPIC_API_KEY:
            st.error("❌ Please set ANTHROPIC_API_KEY")
        else:
            client = Anthropic(api_key=ANTHROPIC_API_KEY)
            results = []
        
            with st.spinner("Running experiments..."):
                if exp1:
                    results.append(experiment_baseline(query, client))
                if exp2:
                    results.append(experiment_rag(query, client))
                if exp3:
                    results.append(experiment_agent4compliance(query, client))
                if exp4:
                    results.append(multi_agent_compliance_system(query, client))
            # Display
            for r in results:
                with st.expander(f"📌 {r['name']}", expanded=True):
                    # display_agent4_result(r)

                    cols = st.columns(3)
                    cols[0].metric("Time", f"{r['duration']:.1f}s")
                    cols[1].metric("Method", r['method'])
                    if 'compliance_status' in r:
                        # Show explicit compliance status
                        status = r['compliance_status']
                        if "COMPLIANT" in status and "NOT" not in status:
                            cols[2].metric("Status", "✅ COMPLIANT", delta="Verified")
                        elif "NOT COMPLIANT" in status or "VIOLATION" in status:
                            cols[2].metric("Status", "👎 VIOLATION ❌", delta="Failed")
                        else:
                            cols[2].metric("Status", "⚠️ UNKNOWN", delta="Inconclusive")
                    elif 'verified' in r:
                        cols[2].metric("Verified", "✅" if r['verified'] else "❌")
                    
                    st.markdown("**Pipeline:**")
                    for step in r['steps']:
                        st.markdown(f"- {step}")
                    
                    if 'formula' in r:
                        with st.expander("🔬 Formula"):
                            st.code(r['formula'])
                    
                    if 'extracted_facts' in r:
                        with st.expander("📋 Facts"):
                            st.json(r['extracted_facts'])
                    
                    if 'precis_result' in r and 'pipeline_steps' in r['precis_result']:
                        with st.expander("🔧 OCaml Pipeline (Lexer → Parser → Type Check → Evaluator)"):
                            for step in r['precis_result']['pipeline_steps']:
                                st.markdown(f"- {step}")
                            
                            # Show validation warnings if any
                            if any("⚠️" in s for s in r['steps']):
                                st.warning("**Validation Issues Detected:**")
                                for step in r['steps']:
                                    if "⚠️" in step:
                                        st.markdown(f"- {step}")
                            
                            st.markdown("**Full Output:**")
                            st.code(r['precis_result']['output'], language="text")
                    
                    st.info(r['answer'])
           
            # Display results with different formatters
            for r in results:
                with st.expander(f"📌 {r['name']}", expanded=True):
                    
                    # Check if this is a Pipeline/Agentic result (has precis_result)
                    if 'precis_result' in r:
                        # USE FANCY FORMATTING for Pipeline ⭐ and Agentic
                        display_agent4_result(r)
                    else:
                        # USE SIMPLE FORMATTING for Baseline and RAG
                        display_simple_result(r)


            # # Display all results with unified formatting
            for r in results:
                with st.expander(f"📌 {r['name']}", expanded=True):
                    display_experiment_result(r)
        
            # FIXED: Comparison section - results is a list, not dict
            st.markdown("---")
            st.markdown("## 📈 Comparison")
            
            comparison_data = []
            for result in results:
                if "error" not in result:
                    # Determine experiment type from result name
                    exp_key = None
                    if "Baseline" in result['name']:
                        exp_key = "baseline_no_context"
                    elif "RAG" in result['name']:
                        exp_key = "rag"
                    elif "Pipeline" in result['name']:
                        exp_key = "pipeline"
                    elif "Agentic" in result['name']:
                        exp_key = "agentic"
                    
                    if exp_key:
                        comparison_data.append({
                            "Experiment": EXPERIMENTS[exp_key]["exp_name"],
                            "Duration (s)": f"{result.get('duration', 0):.2f}",
                            "Steps": len(result.get('steps', [])),
                            "Uses Retrieval": "✅" if EXPERIMENTS[exp_key]["use_retrieval"] else "❌",
                            "Uses Précis": "✅" if EXPERIMENTS[exp_key]["use_precis"] else "❌",
                        })
            
            if comparison_data:
                st.table(comparison_data)
            
            # Download results
            st.markdown("---")
            st.markdown("### 💾 Download Results")
            
            results_json = json.dumps(results, indent=2, default=str)
            st.download_button(
                label="📥 Download as JSON",
                data=results_json,
                file_name=f"compliance_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
# ============================================
# PAGE 2: DOCUMENT → FOTL TRANSLATION
# ============================================

elif page == "Document → FOTL":
    
    # Main Page
    st.markdown("# 📄 Document → Multi-Regulation FOTL System")
    st.markdown("Upload any regulatory document. System auto-detects regulation and generates type system + policy file.")

    # Instructions
    with st.expander("ℹ️ How It Works"):
        st.markdown("""
        **Automated Pipeline:**
        1. **Upload** - PDF/TXT document
        2. **Auto-Detect** - Identifies HIPAA/GDPR/CCPA
        3. **Extract** - Finds sections
        4. **Translate** - Converts to FOTL
        5. **Generate Type System** - Auto-creates predicate definitions
        6. **Generate Policy File** - Creates loadable .policy file
        
        **No Manual Type System Configuration Required!**
        """)

    # File upload
    uploaded_file = st.file_uploader(
        "📤 Upload Regulatory Document",
        type=['pdf', 'txt'],
        help="Supports HIPAA, GDPR, CCPA documents"
    )

    if uploaded_file:
        # Check if this is the same file we already processed
        file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        
        if st.session_state.last_uploaded_file == file_id and st.session_state.processing_results:
            st.info("📋 Using cached results from previous processing. Click 'Process Document' to re-run.")
            show_cached = True
            results = st.session_state.processing_results
        else:
            st.success(f"✅ Loaded: {uploaded_file.name}")
            show_cached = False
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_sections = st.number_input(
                "Max Sections to Process",
                min_value=1,
                max_value=20,
                value=5
            )
        
        with col2:
            st.metric("File Size", f"{uploaded_file.size / 1024:.1f} KB")
        
        if st.button("🚀 Process Document", type="primary") or show_cached:
            if not ANTHROPIC_API_KEY:
                st.error("❌ Set API key in sidebar")
            else:
                if not show_cached:
                    # Process document
                    client = Anthropic(api_key=ANTHROPIC_API_KEY)
                    pipeline = MultiRegulationPipeline(client, PRECIS_PATH)
                    
                    with st.spinner("Processing..."):
                        results = pipeline.process_document(uploaded_file, max_sections)
                    
                    # Save to session state
                    st.session_state.processing_results = results
                    st.session_state.last_uploaded_file = file_id
                
                # Display results (works for both new and cached)
                st.markdown("---")
                st.markdown("## ✅ Processing Complete!")
                
                if show_cached:
                    st.success("♻️ Showing cached results - No API calls made!")
                
                # Regulation detected
                col1, col2, col3 = st.columns(3)
                col1.metric("Regulation Detected", results['regulation'])
                col2.metric("Sections Processed", len(results['sections']))
                col3.metric("Policies Generated", len(results['policies']))
                
                # Show policies
                if results['policies']:
                    st.markdown("### 📋 Generated Policies")
                    
                    for i, policy in enumerate(results['policies'][:5]):  # Show first 5
                        with st.expander(f"{policy['section']} - {policy['title']}"):
                            st.markdown("**Original:**")
                            st.info(policy['statement'])
                            
                            st.markdown("**FOTL Formula:**")
                            st.code(policy['fotl_formula'], language="ocaml")
                    
                    if len(results['policies']) > 5:
                        st.info(f"Showing 5 of {len(results['policies'])} policies. Download files to see all.")
                
                # Download section - ALWAYS VISIBLE
                st.markdown("---")
                st.markdown("## 💾 Download Generated Files")
                st.warning("⚠️ Download all files NOW before leaving this page!")
                
                download_col1, download_col2, download_col3, download_col4 = st.columns(4)
                
                with download_col1:
                    st.markdown("### 📄 Type System")
                    st.download_button(
                        label="📥 Type System (.txt)",
                        data=results['type_system'],
                        file_name=f"{results['regulation'].lower()}_types.txt",
                        mime="text/plain",
                        help="Predicate definitions for OCaml",
                        use_container_width=True
                    )
                
                with download_col2:
                    st.markdown("### 📜 Policy File")
                    st.download_button(
                        label="📥 Policy File (.policy)",
                        data=results['policy_file'],
                        file_name=f"{results['regulation'].lower()}_generated.policy",
                        mime="text/plain",
                        help="FOTL formulas for OCaml",
                        use_container_width=True
                    )
                with download_col3:
                    st.markdown("### 🔖 RAG")
                    st.download_button(
                    label="📊 RAG CSV",
                    data=RAGPolicyExporter.generate_rag_csv(results),
                    file_name=f"{results['regulation'].lower()}_rag.csv",
                    mime="text/csv",
                    help="Searchable policy database",
                    use_container_width=True
                )
                
                with download_col4:
                    st.markdown("### 📊 Full Report")
                    # Generate JSON report
                    report = {
                        'regulation': results['regulation'],
                        'timestamp': datetime.now().isoformat(),
                        'sections_processed': len(results['sections']),
                        'policies_generated': len(results['policies']),
                        'policies': results['policies']
                    }
                    
                    st.download_button(
                        label="📥 JSON Report",
                        data=json.dumps(report, indent=2),
                        file_name=f"{results['regulation'].lower()}_report.json",
                        mime="application/json",
                        help="Complete processing report",
                        use_container_width=True
                    )
 
                # Preview sections
                with st.expander("👁️ Preview Type System"):
                    st.code(results['type_system'], language="text")
                
                with st.expander("👁️ Preview Policy File"):
                    st.code(results['policy_file'][:2000] + "\n...(truncated)", language="ocaml")
                
                # Instructions
                st.markdown("---")
                st.markdown("### 🎯 Integration Instructions")
                
                with st.expander("📖 How to Use These Files in OCaml"):
                    st.code(f"""
    # 1. Save files to your project
    cp {results['regulation'].lower()}_types.txt data/
    cp {results['regulation'].lower()}_generated.policy policies/

    # 2. Update your OCaml loader (environment_config.ml)

    let load_multi_regulation_types () : type_environment =
    (* Load individual type systems *)
    let hipaa_types = Type_system_db.load_type_system_file "data/hipaa_types.txt" in
    let {results['regulation'].lower()}_types = Type_system_db.load_type_system_file "data/{results['regulation'].lower()}_types.txt" in
    
    (* Merge type environments *)
    let merged = merge_type_environments [hipaa_types; {results['regulation'].lower()}_types] in
    merged

    (* 3. Load policies - your existing code already handles this! *)
    let manager = create_manager "policies/"
    reload_all manager  (* Loads all .policy files including new one *)

    (* 4. Query against {results['regulation']} *)
    let response = process_query formula (Some "{results['regulation']}") ...
                    """, language="ocaml")
                
                # Clear cache button
                st.markdown("---")
                if st.button("🗑️ Clear Cache & Start Fresh"):
                    st.session_state.processing_results = None
                    st.session_state.last_uploaded_file = None
                    st.rerun()

# ============================================
# PAGE 3: WHAT-IF SIMULATOR
# ============================================

elif page == "What-If Simulator":
    st.markdown("# 🔮 What-If Simulator")
    st.markdown("Interactively modify facts and see how compliance changes")
    
    st.info("💡 **How to use:** Add facts to the scenario and see compliance re-evaluated in real-time")
    
    # Display current facts
    st.markdown("### 📋 Current Facts")
    
    current_facts = st.session_state.get('facts', [])
    
    if current_facts:
        for i, fact in enumerate(current_facts):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.code(f"{fact[0]}({', '.join(fact[1:])})", language="ocaml")
            with col2:
                if st.button("🗑️", key=f"delete_{i}"):
                    current_facts.pop(i)
                    st.session_state.facts = current_facts
                    st.rerun()
    else:
        st.info("No facts added yet. Add some below!")
    
    # Add new fact
    st.markdown("### ➕ Add New Fact")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        new_fact_str = st.text_input(
            "Enter fact",
            placeholder="e.g., hasAuthorization(HospitalA, ResearcherCarol, PHI_001)",
            help="Format: predicate(arg1, arg2, ...)"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        add_clicked = st.button("Add Fact", type="primary")
    
    if add_clicked and new_fact_str:
        # Parse fact string
        match = re.match(r'(\w+)\((.*)\)', new_fact_str.strip())
        if match:
            predicate = match.group(1)
            args_str = match.group(2)
            args = [arg.strip() for arg in args_str.split(',')]
            
            new_fact = [predicate] + args
            current_facts.append(new_fact)
            st.session_state.facts = current_facts
            st.success(f"✅ Added: {predicate}({', '.join(args)})")
            st.rerun()
        else:
            st.error("❌ Invalid format. Use: predicate(arg1, arg2, ...)")
    
    # Quick add buttons
    st.markdown("### ⚡ Quick Add")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ coveredEntity(HospitalA)"):
            current_facts.append(["coveredEntity", "HospitalA"])
            st.session_state.facts = current_facts
            st.rerun()
    
    with col2:
        if st.button("➕ protectedHealthInfo(PHI_001)"):
            current_facts.append(["protectedHealthInfo", "PHI_001"])
            st.session_state.facts = current_facts
            st.rerun()
    
    with col3:
        if st.button("➕ hasAuthorization(...)"):
            current_facts.append(["hasAuthorization", "HospitalA", "ResearcherCarol", "PHI_001"])
            st.session_state.facts = current_facts
            st.rerun()
    
    # Clear all
    if current_facts and st.button("🗑️ Clear All Facts"):
        st.session_state.facts = []
        st.rerun()

# ============================================
# PAGE 4: SYSTEM STATUS
# ============================================

elif page == "System Status":
    st.markdown("# 🔧 System Status")
    st.markdown("Verify that all components are working correctly")
    
    # Test Précis
    st.markdown("### 🔍 Précis Engine Test")
    
    if st.button("Run Précis Test"):
        with st.spinner("Testing Précis engine..."):
            try:
                result = subprocess.run(
                    [PRECIS_PATH, "inspect"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    st.success("✅ Précis engine is working!")
                    with st.expander("📋 Précis Output"):
                        st.code(result.stdout[:500])
                else:
                    st.error("❌ Précis test failed")
                    st.code(result.stderr)
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Test Anthropic API
    st.markdown("### 🤖 Anthropic API Test")
    
    if st.button("Test API Connection"):
        if not ANTHROPIC_API_KEY:
            st.error("❌ API key not set")
        else:
            with st.spinner("Testing API..."):
                try:
                    client = Anthropic(api_key=ANTHROPIC_API_KEY)
                    message = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=100,
                        messages=[{"role": "user", "content": "Say 'API test successful'"}]
                    )
                    st.success("✅ API connection working!")
                    st.info(message.content[0].text)
                except Exception as e:
                    st.error(f"❌ API error: {e}")
    
    # System info
    st.markdown("### 📊 System Information")
    
    info_data = {
        "Précis Path": PRECIS_PATH,
        "API Key Set": "✅" if ANTHROPIC_API_KEY else "❌",
        "Session Facts": len(st.session_state.get('facts', [])),
        "Python Version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
    }
    
    for key, value in info_data.items():
        st.metric(key, value)

# ============================================
# FOOTER
# ============================================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p><strong>Agent4Compliance</strong> - Formal Compliance Verification System</p>
    <p style="font-size: 0.85rem;">Powered by Précis Engine + Claude Sonnet 4</p>
    <p style="font-size: 0.75rem;">⚠️ For educational and research purposes only. Not legal advice.</p>
</div>
""", unsafe_allow_html=True)


with st.sidebar:
    st.markdown("---")
    st.markdown("""
    ### 📚 About
    
    This system implements three approaches to compliance verification:
    
    1. **Baseline**: Direct LLM
    2. **RAG**: Retrieval + LLM
    3. **Pipeline4Compliance**: Full pipeline with formal verification
    4. **Agent4Compliance**: Full Agent Reasoning, tool use, replanning using CrewAI
    
                
                
    Built with ❤️ using Précis + Claude
    """)