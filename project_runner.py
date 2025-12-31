"""
Helper script to run individual projects from the launcher
Usage: streamlit run run_project.py -- <project_key>
"""

import sys
import os
from pathlib import Path
import importlib.util

# Get the base directory
BASE_DIR = Path(__file__).parent.absolute()

# Project configurations (must match main_app.py)
PROJECTS = {
    "NL2LTL": {
        "path": BASE_DIR / "NL2LTL_PHASE2",
        "streamlit_app": "streamlit_app.py",
    },
    "PROTOCOL": {
        "path": BASE_DIR / "PROTOCOL_FORMALIZATION",
        "streamlit_app": "streamlit_app.py",
    },
    "REGULATORY": {
        "path": BASE_DIR / "REGULATORY_POLICY_CHECKER",
        "streamlit_app": "streamlit_app.py",
    }
}

def run_project(project_key):
    """Run the specified project's streamlit app"""
    if project_key not in PROJECTS:
        raise ValueError(f"Unknown project: {project_key}")
    
    project_info = PROJECTS[project_key]
    project_path = project_info["path"]
    app_file = project_path / project_info["streamlit_app"]
    
    if not app_file.exists():
        raise FileNotFoundError(f"Streamlit app not found: {app_file}")
    
    # Change to project directory to maintain relative paths
    os.chdir(project_path)
    
    # Add project directory to Python path
    if str(project_path) not in sys.path:
        sys.path.insert(0, str(project_path))
    
    # Load and execute the streamlit app
    spec = importlib.util.spec_from_file_location("streamlit_app", app_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules["streamlit_app"] = module
    spec.loader.exec_module(module)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: streamlit run run_project.py -- <project_key>")
        print(f"Available projects: {', '.join(PROJECTS.keys())}")
        sys.exit(1)
    
    project_key = sys.argv[1]
    run_project(project_key)
