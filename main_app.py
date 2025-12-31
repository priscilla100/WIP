import streamlit as st
import subprocess
import sys
import os
from pathlib import Path
import time

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
        "port": 8502
    },
    {
        "key": "PROTOCOL",
        "name": "Protocol Formalization",
        "description": "Protocol specification and formalization system",
        "path": BASE_DIR / "PROTOCOL_FORMALIZATION",
        "streamlit_app": "streamlit_app.py",
        "icon": "📋",
        "port": 8503
    },
    {
        "key": "REGULATORY",
        "name": "Regulatory Policy Checker",
        "description": "Policy compliance verification system",
        "path": BASE_DIR / "REGULATORY_POLICY_CHECKER",
        "streamlit_app": "streamlit_app.py",
        "icon": "✅",
        "port": 8504
    }
]

def check_project_exists(project_info):
    """Check if project directory and streamlit app exist"""
    project_path = project_info["path"]
    app_path = project_path / project_info["streamlit_app"]
    return project_path.exists() and app_path.exists()

def check_port_in_use(port):
    """Check if a port is already in use"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def launch_project(project_info):
    """Launch a project in a subprocess"""
    project_path = project_info["path"]
    app_file = project_path / project_info["streamlit_app"]
    port = project_info["port"]
    
    # Check if already running
    if check_port_in_use(port):
        return "already_running", port
    
    # Build command
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(app_file),
        "--server.port", str(port),
        "--server.headless", "true"
    ]
    
    try:
        # Launch in background
        process = subprocess.Popen(
            cmd,
            cwd=str(project_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )
        return "launched", port
    except Exception as e:
        return "error", str(e)

# Initialize session state
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

# Custom CSS
st.markdown("""
<style>
    .project-card {
        padding: 2rem;
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        height: 100%;
        transition: all 0.3s ease;
        background: white;
        margin-bottom: 1rem;
    }
    .project-card:hover {
        border-color: #4ECDC4;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    .project-icon {
        font-size: 4rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .project-title {
        font-size: 1.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .project-desc {
        text-align: center;
        color: #666;
        font-size: 0.95rem;
        margin-bottom: 1rem;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
    }
    .status-ready {
        background-color: #d4edda;
        color: #155724;
    }
    .status-running {
        background-color: #cce5ff;
        color: #004085;
        animation: pulse 2s infinite;
    }
    .status-missing {
        background-color: #f8d7da;
        color: #721c24;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🚀 Project Launcher Dashboard")
st.markdown("### All Three Projects - Click Any Card to Launch")
st.info(f"📊 **{len(PROJECTS)} projects** configured and ready")
st.markdown("---")

# Create three columns - ONE FOR EACH PROJECT
col1, col2, col3 = st.columns(3)
columns = [col1, col2, col3]

# Display each project in its own column
for idx, project in enumerate(PROJECTS):
    with columns[idx]:
        # Check status
        exists = check_project_exists(project)
        is_running = check_port_in_use(project['port'])
        
        # Determine status
        if not exists:
            status = "missing"
            status_text = "❌ Not Found"
            status_color = "#f8d7da"
        elif is_running:
            status = "running"
            status_text = "🟢 RUNNING"
            status_color = "#cce5ff"
        else:
            status = "ready"
            status_text = "✅ Ready"
            status_color = "#d4edda"
        
        # Create card HTML
        st.markdown(f"""
        <div class="project-card">
            <div class="project-icon">{project['icon']}</div>
            <div class="project-title">{project['name']}</div>
            <div class="project-desc">{project['description']}</div>
            <div style="text-align: center;">
                <span class="status-badge status-{status}">{status_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        if not exists:
            # Project not found
            st.error("⚠️ **Project Not Found**")
            st.caption(f"Expected at: `{project['path']}`")
            
        elif is_running:
            # Already running - show open button
            st.success(f"**Running on port {project['port']}**")
            st.link_button(
                "🌐 OPEN PROJECT",
                f"http://localhost:{project['port']}",
                use_container_width=True,
                type="primary"
            )
            st.caption("Project is already running!")
            
        else:
            # Ready to launch
            st.success("**Ready to Launch**")
            
            # Launch button
            if st.button(
                "🚀 LAUNCH NOW", 
                key=f"launch_{project['key']}_{idx}",
                use_container_width=True,
                type="primary"
            ):
                with st.spinner(f"🔄 Starting {project['name']}..."):
                    status_code, info = launch_project(project)
                    
                    if status_code == "launched":
                        st.success(f"✅ **Launched!**")
                        st.balloons()
                        st.info(f"Opening on port {info}...")
                        time.sleep(2)
                        st.rerun()
                        
                    elif status_code == "already_running":
                        st.info(f"Already running on port {info}")
                        
                    else:
                        st.error(f"❌ Launch failed: {info}")
        
        # Show project details
        with st.expander("📁 Details"):
            st.code(str(project['path']))
            st.caption(f"Port: {project['port']}")
            st.caption(f"App: {project['streamlit_app']}")

st.markdown("---")

# Active services section
st.markdown("### 🖥️ Active Services Dashboard")
running_projects = [p for p in PROJECTS if check_port_in_use(p['port'])]

if running_projects:
    st.success(f"**{len(running_projects)} of {len(PROJECTS)} projects running**")
    
    service_cols = st.columns(len(running_projects))
    for idx, project in enumerate(running_projects):
        with service_cols[idx]:
            st.markdown(f"""
            **{project['icon']} {project['name']}**
            
            Port: {project['port']}
            """)
            st.link_button(
                "Open →",
                f"http://localhost:{project['port']}",
                use_container_width=True
            )
else:
    st.info("🔵 No projects currently running. Click **LAUNCH NOW** on any card above!")

st.markdown("---")

# Quick actions
col_a, col_b, col_c = st.columns(3)

with col_a:
    if st.button("🔄 Refresh Status", use_container_width=True):
        st.session_state.last_refresh = time.time()
        st.rerun()

with col_b:
    st.metric("Projects Found", sum(1 for p in PROJECTS if check_project_exists(p)))

with col_c:
    st.metric("Currently Running", len(running_projects))

# Help section
with st.expander("❓ Help & Troubleshooting"):
    st.markdown("""
    ### How to Use
    1. **Check Status**: Each card shows if the project is Ready, Running, or Missing
    2. **Click LAUNCH NOW**: Starts the project in the background (takes 3-5 seconds)
    3. **Click OPEN PROJECT**: Opens the running project in a new tab
    
    ### All Three Projects
    """)
    
    for i, p in enumerate(PROJECTS, 1):
        exists_icon = "✅" if check_project_exists(p) else "❌"
        running_icon = "🟢" if check_port_in_use(p['port']) else "⚪"
        st.markdown(f"{i}. {exists_icon} {running_icon} **{p['name']}** - Port {p['port']}")
    
    st.markdown("""
    ### Stopping Projects
    
    Projects run in background. To stop:
    
    ```bash
    # Stop specific port (e.g., 8502)
    lsof -ti:8502 | xargs kill -9
    
    # Or stop all streamlit
    pkill -f streamlit
    ```
    
    ### If Launch Fails
    - Check the terminal running this dashboard for error messages
    - Try manual launch: `cd PROJECT_PATH && streamlit run streamlit_app.py --server.port PORT`
    - Ensure dependencies installed: `pip install -r requirements.txt`
    - Check if virtual environment needs activation
    """)

# Footer
st.markdown("---")
st.caption(f"🚀 Dashboard on port 8501 | Last refresh: {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_refresh))}")