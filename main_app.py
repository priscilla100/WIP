import streamlit as st
import sys
from pathlib import Path
import importlib.util

# Page config
st.set_page_config(
    page_title="Project Launcher",
    page_icon="🚀",
    layout="wide"
)

# Get the base directory
BASE_DIR = Path(__file__).parent.absolute()

# Project configurations - ALL THREE PROJECTS
PROJECTS = [
    {
        "key": "NL2LTL",
        "name": "NL2LTL Phase 2",
        "description": "Natural Language to Linear Temporal Logic conversion",
        "path": BASE_DIR / "NL2LTL_PHASE2",
        "streamlit_app": "streamlit_app.py",
        "icon": "🔄",
        "color": "#FF6B6B"
    },
    {
        "key": "PROTOCOL",
        "name": "Protocol Formalization",
        "description": "Protocol specification and formalization system",
        "path": BASE_DIR / "PROTOCOL_FORMALIZATION",
        "streamlit_app": "streamlit_app.py",
        "icon": "📋",
        "color": "#4ECDC4"
    },
    {
        "key": "REGULATORY",
        "name": "Regulatory Policy Checker",
        "description": "Policy compliance verification system",
        "path": BASE_DIR / "REGULATORY_POLICY_CHECKER",
        "streamlit_app": "streamlit_app.py",
        "icon": "✅",
        "color": "#95E1D3"
    }
]

def check_project_exists(project_info):
    """Check if project directory and streamlit app exist"""
    project_path = project_info["path"]
    app_path = project_path / project_info["streamlit_app"]
    return project_path.exists() and app_path.exists()

def load_and_run_project(project_info):
    """Load and execute the project's streamlit app"""
    project_path = project_info["path"]
    app_file = project_path / project_info["streamlit_app"]
    
    # Add project directory to sys.path so imports work
    if str(project_path) not in sys.path:
        sys.path.insert(0, str(project_path))
    
    # Import and run the project's app
    try:
        spec = importlib.util.spec_from_file_location("project_app", app_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True
    except Exception as e:
        st.error(f"Error loading project: {e}")
        return False

# Initialize session state for navigation
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = None

# Check if a project is selected
if st.session_state.selected_project is not None:
    # Find the selected project
    selected = next((p for p in PROJECTS if p['key'] == st.session_state.selected_project), None)
    
    if selected:
        # Show back button
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("← Back to Dashboard", type="secondary"):
                st.session_state.selected_project = None
                st.rerun()
        with col2:
            st.title(f"{selected['icon']} {selected['name']}")
        
        st.markdown("---")
        
        # Load and run the selected project
        if check_project_exists(selected):
            load_and_run_project(selected)
        else:
            st.error(f"Project not found at: {selected['path']}")
    
else:
    # Show dashboard/home page
    
    # Custom CSS
    st.markdown("""
    <style>
        .project-card {
            padding: 2rem;
            border-radius: 15px;
            border: 2px solid #e0e0e0;
            height: 100%;
            transition: all 0.3s ease;
            background: white;
            margin-bottom: 1rem;
            cursor: pointer;
        }
        .project-card:hover {
            border-color: #4ECDC4;
            box-shadow: 0 8px 16px rgba(0,0,0,0.15);
            transform: translateY(-5px);
        }
        .project-icon {
            font-size: 5rem;
            text-align: center;
            margin-bottom: 1.5rem;
        }
        .project-title {
            font-size: 1.8rem;
            font-weight: bold;
            text-align: center;
            margin-bottom: 1rem;
            color: #333;
        }
        .project-desc {
            text-align: center;
            color: #666;
            font-size: 1rem;
            line-height: 1.6;
            margin-bottom: 1.5rem;
        }
        .status-badge {
            display: inline-block;
            padding: 0.4rem 1rem;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
        }
        .status-ready {
            background-color: #d4edda;
            color: #155724;
        }
        .status-missing {
            background-color: #f8d7da;
            color: #721c24;
        }
        .main-header {
            text-align: center;
            margin-bottom: 3rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.title("🚀 Project Dashboard")
    st.markdown("### Select a project to launch")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Info banner
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("Total Projects", len(PROJECTS))
    with col_info2:
        available = sum(1 for p in PROJECTS if check_project_exists(p))
        st.metric("Available", available)
    with col_info3:
        st.metric("Status", "✅ Ready" if available == len(PROJECTS) else "⚠️ Check Setup")
    
    st.markdown("---")
    
    # Create three columns - ONE FOR EACH PROJECT
    col1, col2, col3 = st.columns(3)
    columns = [col1, col2, col3]
    
    # Display each project in its own column
    for idx, project in enumerate(PROJECTS):
        with columns[idx]:
            # Check if project exists
            exists = check_project_exists(project)
            status = "ready" if exists else "missing"
            status_text = "✅ Available" if exists else "❌ Not Found"
            
            # Create card
            st.markdown(f"""
            <div class="project-card" style="border-color: {project['color']};">
                <div class="project-icon">{project['icon']}</div>
                <div class="project-title">{project['name']}</div>
                <div class="project-desc">{project['description']}</div>
                <div style="text-align: center;">
                    <span class="status-badge status-{status}">{status_text}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Launch button
            if exists:
                if st.button(
                    "🚀 Launch Project",
                    key=f"btn_{project['key']}",
                    use_container_width=True,
                    type="primary"
                ):
                    st.session_state.selected_project = project['key']
                    st.rerun()
            else:
                st.error("⚠️ Project files not found")
            
            # Details expander
            with st.expander("📁 Project Info"):
                st.caption(f"**Path:** `{project['path']}`")
                st.caption(f"**Entry:** `{project['streamlit_app']}`")
                if exists:
                    st.success("✓ All files present")
                else:
                    st.error("✗ Missing project files")
    
    st.markdown("---")
    
    # Instructions section
    st.markdown("### 💡 How to Use")
    st.info("""
    1. **Click** on any "Launch Project" button above
    2. The selected project will load in this same page
    3. Use the **"← Back to Dashboard"** button to return here
    4. All project files and dependencies remain isolated
    """)
    
    # Setup information
    with st.expander("⚙️ Setup & Troubleshooting"):
        st.markdown("### Expected Directory Structure")
        st.code("""
YourRepo/
├── main_app.py (this file)
├── NL2LTL_PHASE2/
│   ├── streamlit_app.py
│   └── ... (other project files)
├── PROTOCOL_FORMALIZATION/
│   ├── streamlit_app.py
│   └── ... (other project files)
└── REGULATORY_POLICY_CHECKER/
    ├── streamlit_app.py
    └── ... (other project files)
        """)
        
        st.markdown("### Current Status")
        for project in PROJECTS:
            exists = check_project_exists(project)
            icon = "✅" if exists else "❌"
            st.markdown(f"{icon} **{project['name']}**")
            st.caption(f"Expected at: `{project['path']}`")
            if exists:
                st.caption(f"✓ Found: `{project['path']}/{project['streamlit_app']}`")
        
        st.markdown("### Deployment Notes")
        st.markdown("""
        **For Streamlit Cloud:**
        - All project folders must be in the same repository
        - Each project's `requirements.txt` should be merged or handled separately
        - Projects load within the same app instance (no separate processes)
        
        **For Local Development:**
        - Same structure works perfectly
        - Each project maintains its own working directory
        - No port conflicts or process management needed
        """)
    
    # Footer
    st.markdown("---")
    st.caption("🎯 All projects run in isolated environments with their own dependencies")
