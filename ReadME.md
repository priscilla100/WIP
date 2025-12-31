# 🚀 Unified Project Launcher

A centralized dashboard to launch and manage your three independent Streamlit projects.

## 📁 Directory Structure

```
WIP/
├── main_app.py                    # Main dashboard launcher
├── launch.sh                       # Convenience script for launching
├── LAUNCHER_README.md             # This file
├── NL2LTL_PHASE2/
│   ├── streamlit_app.py
│   └── ...
├── PROTOCOL_FORMALIZATION/
│   ├── streamlit_app.py
│   └── ...
└── REGULATORY_POLICY_CHECKER/
    ├── streamlit_app.py
    └── ...
```

## 🎯 Quick Start

### Option 1: Using the Launch Script (Easiest)

1. Make the script executable:
```bash
chmod +x launch.sh
```

2. Launch the dashboard:
```bash
./launch.sh dashboard
```

3. Or launch everything at once:
```bash
./launch.sh all
```

### Option 2: Manual Launch

1. **Launch the Dashboard:**
```bash
streamlit run main_app.py
```

2. **From the dashboard**, click on any project card to see the launch command

3. **Open a new terminal** and run the command shown

### Option 3: Launch Individual Projects Directly

```bash
# NL2LTL Phase 2
cd NL2LTL_PHASE2
streamlit run streamlit_app.py --server.port 8502

# Protocol Formalization
cd PROTOCOL_FORMALIZATION
streamlit run streamlit_app.py --server.port 8503

# Regulatory Policy Checker
cd REGULATORY_POLICY_CHECKER
streamlit run streamlit_app.py --server.port 8504
```

## 🔧 Setup

1. Place `main_app.py` and `launch.sh` in your `WIP` directory (the parent of your three projects)

2. Ensure each project has its virtual environment set up:
```bash
cd NL2LTL_PHASE2 && python -m venv myenv && source myenv/bin/activate && pip install -r requirements.txt
cd ../PROTOCOL_FORMALIZATION && python -m venv myenv && source myenv/bin/activate && pip install -r requirements.txt
cd ../REGULATORY_POLICY_CHECKER && python -m venv myenv && source myenv/bin/activate && pip install -r requirements.txt
```

3. Test the launcher:
```bash
cd WIP
streamlit run main_app.py
```

## 🎨 Features

### Dashboard (main_app.py)
- **Visual project cards** with status indicators
- **Click-to-launch** with automatic command generation
- **Project validation** - checks if paths and files exist
- **Port management** - each project runs on its own port
- **Quick start guide** and troubleshooting tips

### Launch Script (launch.sh)
- Launch individual projects or all at once
- Automatic virtual environment activation
- Port conflict detection
- Color-coded output for better readability

## 🛠️ Launch Script Commands

```bash
./launch.sh dashboard     # Launch only the dashboard
./launch.sh nl2ltl        # Launch NL2LTL Phase 2
./launch.sh protocol      # Launch Protocol Formalization  
./launch.sh regulatory    # Launch Regulatory Policy Checker
./launch.sh all           # Launch everything (dashboard + all projects)
./launch.sh help          # Show help message
```

## 🌐 Default Ports

- **Dashboard**: http://localhost:8501
- **NL2LTL Phase 2**: http://localhost:8502
- **Protocol Formalization**: http://localhost:8503
- **Regulatory Policy Checker**: http://localhost:8504

## ⚠️ Avoiding File Path Errors

The launcher is designed to prevent file path issues:

1. **Each project runs in its own directory** - `cd` into the project folder before launching
2. **Virtual environments are isolated** - each project uses its own `myenv`
3. **Separate ports** - no conflicts between running instances
4. **Independent session state** - projects don't interfere with each other

## 🐛 Troubleshooting

### "Port already in use"
- Stop the existing process on that port
- Or change the port number in the command: `--server.port XXXX`
- Check running processes: `lsof -i :8502` (replace 8502 with your port)

### "Module not found"
- Ensure you're in the correct project directory
- Activate the project's virtual environment:
  ```bash
  source myenv/bin/activate  # Unix/Mac
  myenv\Scripts\activate     # Windows
  ```

### "streamlit_app.py not found"
- Verify the project directory exists
- Check that `streamlit_app.py` is in the project root
- Review paths in the dashboard's project info section

### Virtual Environment Issues
```bash
# Recreate virtual environment
cd YOUR_PROJECT
rm -rf myenv
python -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
```

## 💡 Tips

1. **Keep the dashboard open** as your central hub - it shows all project statuses
2. **Use separate terminal tabs** for each project to easily monitor logs
3. **Bookmark the ports** in your browser for quick access
4. **Check the dashboard's info panel** for current project paths and status

## 🔄 Updating Project Paths

If you move your projects or change their structure, update the `PROJECTS` dictionary in `main_app.py`:

```python
PROJECTS = {
    "NL2LTL": {
        "name": "NL2LTL Phase 2",
        "path": BASE_DIR / "NL2LTL_PHASE2",  # Update this path
        "streamlit_app": "streamlit_app.py",
        "icon": "🔄",
        "port": 8502
    },
    # ... other projects
}
```

## 📝 Notes

- Each project maintains complete independence
- No shared dependencies between projects
- The launcher doesn't modify any project code
- All original project functionality is preserved

---

**Happy Launching! 🚀**
