import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
import json
import subprocess
def get_llm_client():
    from anthropic import Anthropic, AsyncAnthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in environment variables")
    return Anthropic(api_key=api_key), AsyncAnthropic(api_key=api_key)  

# Précis path
PRECIS_PATH = str(Path(__file__).parent.parent / "policy_checker" / "precis")
print(f"Précis path set to: {PRECIS_PATH}")
# API Key
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Verify
if not Path(PRECIS_PATH).exists():
    raise FileNotFoundError(f"Précis not found at: {PRECIS_PATH}")

if not ANTHROPIC_API_KEY:
    print("⚠️  Warning: ANTHROPIC_API_KEY not set")


def call_precis_json(formula: str, facts: list) -> dict:
    """Call OCaml Précis engine in JSON mode"""
    
    request = {
        "formula": formula,
        "facts": {"facts": facts},
        "regulation": "HIPAA"
    }
    
    try:
        # Get Précis directory
        precis_dir = os.path.dirname(PRECIS_PATH)
        
        # Run from Précis directory so it finds data/
        proc = subprocess.Popen(
            [PRECIS_PATH, "json"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=precis_dir  # ← ADD THIS!
        )
        
        stdout, stderr = proc.communicate(input=json.dumps(request), timeout=30)
        
        return {
            "success": proc.returncode == 0,
            "output": stdout,
            "error": stderr,
            "response": json.loads(stdout) if stdout.strip() else {}
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}