import streamlit as st

# Page config
st.set_page_config(
    page_title="Research Projects Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Project configurations with live URLs
PROJECTS = [
    {
        "name": "NL2LTL Phase 1",
        "description": "Natural Language to Linear Temporal Logic - Core Research Implementation",
        "url": "https://appexperimentdashboardpy-2qq8aouv7wkun3k9yzctqw.streamlit.app/",
        "icon": "🧪",
        "color": "#FF6B6B",
        "tags": ["NL2LTL", "Phase 1", "Core System"],
        "status": "Pending resubmission"
    },
    {
        "name": "NL2LTL Phase 2",
        "description": "Advanced NL2LTL with enhanced verification capabilities and formal methods integration",
        "url": "https://appapppy-2fjfcxydx434dhecesslwd.streamlit.app/",
        "icon": "🔄",
        "color": "#4ECDC4",
        "tags": ["NL2LTL", "Phase 2", "Extension"],
        "status": "Work in Progress"
    },
    {
        "name": "Protocol Formalization",
        "description": "Systematic protocol specification formalization and verification framework",
        "url": "https://appapppy-vtocq7jm7ucl2ijjhdhq2v.streamlit.app/",
        "icon": "📋",
        "color": "#95E1D3",
        "tags": ["Protocol", "Formalization", "Extension"],
        "status": "Work in Progress"
    },
    {
        "name": "Multi-Policy Compliance Checker",
        "description": "Formal verification using Bounded FOTL for HIPAA, GDPR, and SOX compliance",
        "url": "https://appapppy-zvavaeg3z7ohc4wp8prnhq.streamlit.app/",
        "icon": "✅",
        "color": "#F38181",
        "tags": ["FOTL", "Compliance", "OCaml Core"],
        "status": "Active Development"
    }
]

# Custom CSS for modern card design
st.markdown("""
<style>
    /* Main container */
    .main {
        background: #f8f9fa;
        padding: 2rem 0;
    }
    
    /* Header styling */
    .header-container {
        text-align: center;
        padding: 2rem 0 3rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        margin: 0 1rem 2rem 1rem;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }
    
    .main-title {
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        color: white;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .subtitle {
        font-size: 1.3rem;
        opacity: 0.9;
        font-weight: 300;
        color: white;
    }
    
    /* Project cards */
    .project-card {
        background: white;
        padding: 2.5rem;
        border-radius: 20px;
        border: none;
        height: 100%;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        position: relative;
        overflow: hidden;
        cursor: pointer;
        text-decoration: none;
        display: block;
    }
    
    .project-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 5px;
        background: linear-gradient(90deg, var(--card-color), var(--card-color));
        opacity: 0.8;
    }
    
    .project-card:hover {
        transform: translateY(-10px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.2);
    }
    
    .project-card:active {
        transform: translateY(-8px);
    }
    
    .project-icon {
        font-size: 5rem;
        text-align: center;
        margin-bottom: 1.5rem;
        filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.1));
    }
    
    .project-title {
        font-size: 1.8rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 1rem;
        color: #2d3748;
        line-height: 1.3;
    }
    
    .project-desc {
        text-align: center;
        color: #4a5568;
        font-size: 1rem;
        line-height: 1.6;
        margin-bottom: 1.5rem;
        min-height: 80px;
    }
    
    .tag-container {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 15px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 1rem;
        background: #e6f3ff;
        color: #0066cc;
    }
    
    /* Stats section */
    .stats-container {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        margin: 2rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .stat-box {
        text-align: center;
        padding: 1rem;
    }
    
    .stat-number {
        font-size: 3rem;
        font-weight: 800;
        color: #667eea;
        line-height: 1;
    }
    
    .stat-label {
        font-size: 1rem;
        color: #4a5568;
        margin-top: 0.5rem;
        font-weight: 600;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem 0;
        color: black;
        opacity: 0.8;
    }
    
    /* Button override */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 1rem 2rem;
        font-size: 1.1rem;
        font-weight: 600;
        border-radius: 12px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header-container">
    <div class="main-title">🔬 Research Projects Dashboard</div>
    <div class="subtitle">Formal Methods & Policy Verification Suite</div>
</div>
""", unsafe_allow_html=True)

# Stats section
col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

with col_stat1:
    st.markdown("""
    <div class="stat-box">
        <div class="stat-number">4</div>
        <div class="stat-label">Active Projects</div>
    </div>
    """, unsafe_allow_html=True)

with col_stat2:
    st.markdown("""
    <div class="stat-box">
        <div class="stat-number">2</div>
        <div class="stat-label">NL2LTL Phases</div>
    </div>
    """, unsafe_allow_html=True)

with col_stat3:
    st.markdown("""
    <div class="stat-box">
        <div class="stat-number">100%</div>
        <div class="stat-label">Deployed</div>
    </div>
    """, unsafe_allow_html=True)

with col_stat4:
    st.markdown("""
    <div class="stat-box">
        <div class="stat-number">✓</div>
        <div class="stat-label">All Live</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Project cards in 2x2 grid
row1_col1, row1_col2 = st.columns(2, gap="large")
row2_col1, row2_col2 = st.columns(2, gap="large")

columns = [row1_col1, row1_col2, row2_col1, row2_col2]

for idx, project in enumerate(PROJECTS):
    with columns[idx]:
        # Make the entire card clickable with HTML link
        st.markdown(f"""
        <a href="{project['url']}" target="_blank" style="text-decoration: none; color: inherit;">
            <div class="project-card" style="--card-color: {project['color']};">
                <div class="project-icon">{project['icon']}</div>
                <div class="project-title">{project['name']}</div>
                <div class="project-desc">{project['description']}</div>
                <div style="text-align: center;">
                    <span class="status-badge">{project['status']}</span>
                </div>
            </div>
        </a>
        """, unsafe_allow_html=True)
        
        # Launch button
        st.link_button(
            "🚀 Launch Project",
            project['url'],
            use_container_width=True,
            type="primary"
        )
        
        # Quick info
        with st.expander("ℹ️ Details & Architecture"):
            st.markdown(f"**Project URL:** [{project['url']}]({project['url']})")
            st.markdown(f"**Status:**{project['status']}")
            st.markdown(f"**Tags:** {', '.join(project['tags'])}")
            
            # Special info for compliance checker
            if project['name'] == "Multi-Policy Compliance Checker":
                st.markdown("---")
                st.markdown("**Architecture Highlights:**")
                st.markdown("""
                - **OCaml Core**: Lexer → Parser → Type Checker → Evaluator
                - **Python Bridge**: JSON API + LLM Integration
                - **Regulations**: HIPAA, GDPR, SOX
                - **Logic**: Bounded First-Order Temporal Logic (FOTL)
                - **Modes**: Test, File, Interactive, JSON, Python API
                """)
            elif project['name'] == "NL2LTL Phase 1":
                st.markdown("---")
                st.markdown("**Submission History:**")
                st.markdown("""
                - FMCAD 2025: Rejected
                - ICSE 2026: Rejected
                - FASE 2026: Rejected
                -**Next**: FMCAD 2026 (May)
                - **Status**: Revising based on reviewer feedback
                """)

st.markdown("<br><br>", unsafe_allow_html=True)

# Information section
st.markdown("---")

col_info1, col_info2 = st.columns(2)

with col_info1:
    st.markdown("###About This Research")
    st.info("""
    This dashboard provides centralized access to a suite of **formal methods research projects** focused on:
    
    - **Natural Language to Linear Temporal Logic (NL2LTL)** conversion and verification
    - **Protocol formalization** using temporal logic
    - **Multi-policy compliance checking** with Bounded First-Order Temporal Logic (FOTL)
    
    The **Multi-Policy Compliance Checker** features an OCaml core engine with formal verification for HIPAA, GDPR, and SOX regulations, including lexer/parser, type checker, and evaluator components.
    """)

with col_info2:
    st.markdown("### 📊 Project Status")
    st.success("""
    **NL2LTL Phase 1**: Core research system. Submitted to FMCAD 2025, ICSE 2026, and FASE 2026 (all rejected). Revising for FMCAD 2026 (May target).
    
    **NL2LTL Phase 2**: Extension work incorporating advanced verification techniques and enhanced LTL synthesis.
    
    **Protocol Formalization**: Extension framework for systematic protocol specification and formal verification.
    
    **Multi-Policy Compliance Checker**: Active development featuring OCaml-based FOTL engine with Python integration layer for natural language query processing.
    """)

# Research context
with st.expander("📚 Publication History & Research Context"):
    st.markdown("""
    ### NL2LTL Phase 1 - Submission Timeline
    
    **Conference Submissions (All Rejected):**
    1. **FMCAD 2025** - Rejected
    2. **ICSE 2026** - Rejected  
    3. **FASE 2026** (Co-located with TACAS) - Rejected
    4. **FMCAD 2026** -Target submission (May 2026) - Revising based on feedback
    
    **Status**: Under peer review process. Incorporating reviewer feedback for next submission.
    
    ### Research Evolution
    
    **Phase 1 → Phase 2 Improvements:**
    - Enhanced verification algorithms
    - Improved natural language understanding
    - Extended temporal logic coverage
    - Better synthesis techniques
    
    **Extension Projects:**
    - **Protocol Formalization**: Applying NL2LTL techniques to protocol specifications
    - **Multi-Policy Compliance**: Expanding to First-Order Temporal Logic (FOTL) for regulatory compliance
    
    ### Multi-Policy Compliance Checker - Technical Architecture
    
    **Core Engine (OCaml):**
    - **Lexer & Parser**: Tokenization and AST construction for policy formulas
    - **Type Checker**: Validates formula well-formedness with quantifier scoping
    - **Evaluator**: Checks compliance against fact databases using bounded FOTL
    - **Configuration System**: 50+ predicates, domain management, function evaluation
    
    **Integration Layer (Python):**
    - JSON-based API for OCaml core
    - LLM integration (NL → Formula, Results → NL)
    - Natural language query processing
    
    **Supported Regulations:**
    - HIPAA (Health Insurance Portability and Accountability Act)
    - GDPR (General Data Protection Regulation)
    - SOX (Sarbanes-Oxley Act)
    
    **Key Features:**
    - Quantifiers (∀/∃) with proper scoping
    - Temporal operators (G, F, X, H, O, Y, U, S) with time bounds
    - Constants vs variables (@-prefixed vs unprefixed)
    - Multi-mode operation (test, file, interactive, JSON, Python bridge)
    
    ### Future Directions
    
    - **Integration**: Unifying all project components into comprehensive framework
    - **Scalability**: Performance optimization for large policy sets
    - **Validation**: Extended case studies across multiple domains
    - **Publication**: Continued refinement for top-tier venues
    """)
    
    st.markdown("### 🔗 Quick Links")
    col_link1, col_link2 = st.columns(2)
    with col_link1:
        st.markdown("""
        **Project Documentation:**
        - Multi-Policy Compliance Checker README
        - OCaml Core API Reference
        - Python Integration Guide
        """)
    with col_link2:
        st.markdown("""
        **Research Resources:**
        - FMCAD Conference Series
        - ICSE Proceedings
        - TACAS/FASE Workshop Papers
        """)

# Footer
st.markdown("---")
st.markdown("""
<div class="footer">
    <p>🔬 Research Projects Dashboard | All systems operational</p>
    <p>Click any project card to launch the application in a new tab</p>
</div>
""", unsafe_allow_html=True)