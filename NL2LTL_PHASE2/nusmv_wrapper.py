import subprocess
import tempfile
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class NuSMVTraceGenerator:
    """
    Python wrapper for OCaml/NuSMV trace generation tool.
    Generates satisfying traces for LTL formulas.
    """
    
    def __init__(self, ocaml_dir: str = "LTL/corrected_version/ltlutils", nusmv_bin_path: str = None):
        """
        Initialize the trace generator.
        
        Args:
            ocaml_dir: Path to OCaml tool directory containing dune project
            nusmv_bin_path: Path to NuSMV bin directory (optional, will be set in compile-project)
        """
        self.ocaml_dir = Path(ocaml_dir).resolve()
        # The actual compiled binary is in _build/default/bin/main.exe
        self.bin_path = self.ocaml_dir / "_build" / "default" / "bin" / "main.exe"
        self.nusmv_bin_path = nusmv_bin_path
        self.is_setup = False
        
        if not self.ocaml_dir.exists():
            raise FileNotFoundError(f"OCaml directory not found: {self.ocaml_dir}")
        
        print(f"OCaml directory: {self.ocaml_dir}")
        
    def setup_environment(self, force: bool = False) -> bool:
        """
        Setup and compile the OCaml environment.
        
        Args:
            force: Force recompilation even if already setup
            
        Returns:
            True if setup successful, False otherwise
        """
        if self.is_setup and not force:
            return True
            
        print("Setting up OCaml environment...")
        
        try:
            # Step 1: Make compile-project executable
            compile_script = self.ocaml_dir / "compile-project"
            
            if not compile_script.exists():
                print(f"❌ compile-project script not found at: {compile_script}")
                return False
            
            # Make executable
            subprocess.run(
                ["chmod", "a+x", str(compile_script)],
                check=True,
                capture_output=True,
                text=True
            )
            print("✓ Made compile-project executable")
            
            # Step 2: Update NuSMV path in compile-project if provided
            if self.nusmv_bin_path:
                self._update_nusmv_path_in_script(compile_script, self.nusmv_bin_path)
                print(f"✓ Updated NuSMV path to: {self.nusmv_bin_path}")
            
            # Step 3: Run compile-project
            print("Running compile-project...")
            result = subprocess.run(
                [str(compile_script)],
                cwd=str(self.ocaml_dir),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"❌ compile-project failed:")
                print(f"stdout: {result.stdout}")
                print(f"stderr: {result.stderr}")
                return False
            
            print("✓ compile-project completed")
            
            # Step 4: Run dune build
            print("Running dune build...")
            result = subprocess.run(
                ["dune", "build"],
                cwd=str(self.ocaml_dir),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                print(f"❌ dune build failed:")
                print(f"stdout: {result.stdout}")
                print(f"stderr: {result.stderr}")
                return False
                
            print("✓ dune build completed")
            
            # Step 5: Verify binary exists
            if not self.bin_path.exists():
                print(f"❌ Binary not found at: {self.bin_path}")
                return False
            
            print(f"✓ Binary verified at: {self.bin_path}")
            
            self.is_setup = True
            print("✅ OCaml environment setup complete!\n")
            return True
            
        except subprocess.TimeoutExpired:
            print("❌ Setup timed out")
            return False
        except Exception as e:
            print(f"❌ Setup error: {str(e)}")
            return False
    
    def _update_nusmv_path_in_script(self, script_path: Path, nusmv_bin_path: str):
        """Update the NuSMV path in compile-project script"""
        try:
            with open(script_path, 'r') as f:
                content = f.read()
            
            # Replace the NuSMV path (assuming format like: NUSMV_PATH="/path/to/bin")
            updated_content = re.sub(
                r'NUSMV_PATH=.*',
                f'NUSMV_PATH="{nusmv_bin_path}"',
                content
            )
            
            with open(script_path, 'w') as f:
                f.write(updated_content)
                
        except Exception as e:
            print(f"Warning: Could not update NuSMV path in script: {e}")
    
    def extract_atomic_propositions(self, formula: str) -> List[str]:
        past_ops = ['O', 'Y', 'S', 'H', 'T']
        future_ops = ['G', 'F', 'X', 'U', 'R', 'W']
        symbols = ['&', '|', '->', '<->', '!', '(', ')']

        temp = formula
        for op in past_ops + future_ops + symbols:
            temp = re.sub(rf'\b{re.escape(op)}\b', ' ', temp)

        props = set()
        for word in re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', temp):
            if word.lower() not in ['true', 'false']:
                props.add(word)

        return sorted(props)

    
    def create_inp_file(self, formula: str, mode: str = "positive_trace_gen") -> str:
        """
        Create input file content for the OCaml tool.
        
        Args:
            formula: LTL formula
            mode: Generation mode (default: "positive_trace_gen")
            
        Returns:
            Input file content as string
        """
        # OCaml tool expects: mode, formula, and then an EXTRA blank line before EOF
        return f"{mode}\n{formula}\n\n"
    
    def parse_trace_output(self, output: str, atomic_props: List[str]) -> Optional[List[Dict[str, bool]]]:
        """
        Parse NuSMV trace output into structured format.
        
        Args:
            output: Raw NuSMV output
            atomic_props: List of atomic propositions
            
        Returns:
            List of states, where each state is a dict mapping props to boolean values
        """
        if "UNSATISFIABLE" in output or "DO NOT HAVE ANY POSITIVE TRACES" in output:
            return None
        
        # Check if result is true (formula is valid, no counterexample)
        if re.search(r'-- specification .* is true', output):
            return None
            
        # Find the trace section
        trace_match = re.search(r'Trace Description:.*?Trace Type:.*?\n(.*?)$', output, re.DOTALL)
        if not trace_match:
            return None
            
        trace_text = trace_match.group(1)
        
        # Parse states
        states = []
        current_state = {}
        loop_start = -1
        
        # Split by state markers
        state_blocks = re.split(r'-> State: ([\d\.]+) <-', trace_text)
        
        # Process state blocks (odd indices are state numbers, even indices are content)
        for i in range(1, len(state_blocks), 2):
            if i + 1 >= len(state_blocks):
                break
                
            state_num = state_blocks[i]
            state_content = state_blocks[i + 1]
            
            # Check for loop marker before this state
            if '-- Loop starts here' in state_blocks[i - 1] if i > 0 else False:
                loop_start = len(states)
            
            # Initialize state with previous values or False
            state = {}
            if states:
                state = states[-1].copy()
            else:
                state = {prop: False for prop in atomic_props}
            
            # Update with new assignments in this state
            for line in state_content.strip().split('\n'):
                line = line.strip()
                
                # Check for loop marker
                if '-- Loop starts here' in line:
                    loop_start = len(states)
                    continue
                
                # Parse variable assignments
                if '=' in line and not line.startswith('--'):
                    parts = line.split('=')
                    if len(parts) == 2:
                        var = parts[0].strip()
                        val = parts[1].strip().upper()
                        if var in atomic_props:
                            state[var] = (val == 'TRUE')
            
            states.append(state)
        
        return states if states else None
    
    def format_trace(self, states: List[Dict[str, bool]]) -> str:
        """
        Format trace in the required output format.
        
        Args:
            states: List of state dictionaries
            
        Returns:
            Formatted trace string: [a=false, b=true]; [a=true, b=false]; ...
        """
        if not states:
            return "No trace"
            
        formatted_states = []
        for state in states:
            assignments = [f"{var}={str(val).lower()}" for var, val in sorted(state.items())]
            formatted_states.append(f"[{', '.join(assignments)}]")
        
        return "; ".join(formatted_states)
    
    def generate_trace(self, formula: str, verbose: bool = False) -> Tuple[Optional[str], str]:
        """
        Generate a satisfying trace for the given LTL formula.
        
        Args:
            formula: LTL formula
            verbose: Print debug information
            
        Returns:
            Tuple of (formatted_trace, raw_output)
        """
        if not self.is_setup:
            if not self.setup_environment():
                return None, "OCaml environment not setup. Run setup_environment() first."
        
        # Extract atomic propositions
        atomic_props = self.extract_atomic_propositions(formula)
        
        if verbose:
            print(f"Formula: {formula}")
            print(f"Atomic Propositions: {atomic_props}")
        
        # Use the standard inp_file name that OCaml expects
        inp_file_path = self.ocaml_dir / "inp_file"
        
        try:
            # Write input file - content already has proper newlines
            inp_content = self.create_inp_file(formula)
            with open(inp_file_path, 'w') as f:
                f.write(inp_content)
            
            if verbose:
                print(f"Input file content:")
                with open(inp_file_path, 'r') as f:
                    content = f.read()
                    print(repr(content))  # Show exact content including newlines
                print("---")
            
            # Run exactly as you would manually: dune exec ./bin/main.exe < inp_file
            # Use shell=True to properly handle the redirection
            cmd = "dune exec ./bin/main.exe < inp_file"
            
            if verbose:
                print(f"Running command: {cmd}")
                print(f"In directory: {self.ocaml_dir}")
            
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.ocaml_dir),
                capture_output=True,
                text=True,
                timeout=60,
                executable='/bin/bash'  # Explicitly use bash
            )
            
            if verbose:
                print(f"\nReturn code: {result.returncode}")
                print(f"\nOCaml stdout:\n{result.stdout}")
                if result.stderr:
                    print(f"\nOCaml stderr:\n{result.stderr}")
            
            # Check for errors in stderr
            if "Fatal error" in result.stderr or "exception" in result.stderr:
                return None, f"OCaml error: {result.stderr}"
            
            # Check if trace was generated
            if "POSITIVE TRACE GENERATED SUCCESSFULLY" in result.stdout:
                # Extract the output file path
                match = re.search(r'POSITIVE TRACE GENERATED SUCCESSFULLY AND CAN BE FOUND HERE:\s*(\S+)', result.stdout)
                if match:
                    trace_file_rel = match.group(1).strip()
                    
                    # Resolve trace file path relative to OCaml directory
                    trace_file = self.ocaml_dir / trace_file_rel
                    
                    if not trace_file.exists():
                        # Try without leading ./
                        trace_file = self.ocaml_dir / trace_file_rel.lstrip('./')
                    
                    # Read the trace file
                    if trace_file.exists():
                        with open(trace_file, 'r') as f:
                            trace_output = f.read()
                        
                        if verbose:
                            print(f"\nTrace file: {trace_file}")
                            print(f"Trace file content:\n{trace_output[:500]}...")  # First 500 chars
                        
                        # Parse the trace
                        states = self.parse_trace_output(trace_output, atomic_props)
                        
                        if states:
                            formatted = self.format_trace(states)
                            return formatted, trace_output
                        else:
                            return None, "Failed to parse trace"
                    else:
                        return None, f"Trace file not found: {trace_file}"
            
            elif "UNSATISFIABLE" in result.stdout or "DO NOT HAVE ANY POSITIVE TRACES" in result.stdout:
                return None, "Formula is unsatisfiable"
            
            else:
                return None, f"No trace generated.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return None, "Process timed out"
        except Exception as e:
            import traceback
            return None, f"Error: {str(e)}\n{traceback.format_exc()}"
        finally:
            # Don't cleanup - leave inp_file for debugging
            pass
    
    def generate_truth_table_traces(self, detailed_formula: str, python_formula: str, 
                                    verbose: bool = False) -> Dict[str, Optional[str]]:
        """
        Generate traces for all four truth table combinations.
        
        Args:
            detailed_formula: Detailed LTL formula (D)
            python_formula: Python LTL formula (P)
            verbose: Print debug information
            
        Returns:
            Dictionary with keys: '!D&!P', 'D&!P', '!D&P', 'D&P'
        """
        if not self.is_setup:
            if not self.setup_environment():
                return {k: None for k in ['!D&!P', 'D&!P', '!D&P', 'D&P']}
        
        combinations = {
            '!D&!P': f"G(!({detailed_formula}) & !({python_formula}))",
            'D&!P':  f"G(({detailed_formula}) & !({python_formula}))",
            '!D&P':  f"G(!({detailed_formula}) & ({python_formula}))",
            'D&P':   f"G(({detailed_formula}) & ({python_formula}))"
        }

        
        results = {}
        
        for combo_name, combo_formula in combinations.items():
            if verbose:
                print(f"\n{'='*60}")
                print(f"Processing: {combo_name}")
                print(f"{'='*60}")
            
            trace, raw = self.generate_trace(combo_formula, verbose=verbose)
            results[combo_name] = {
                "trace": trace,
                "raw": raw,
                "satisfiable": trace is not None
            }

            
            if verbose:
                if trace:
                    print(f"✓ Trace generated: {trace}")
                else:
                    print(f"✗ No trace: {raw}")
        
        return results


# Example usage
if __name__ == "__main__":
    import sys
    
    # Initialize generator
    # UPDATE THESE PATHS FOR YOUR SYSTEM
    ocaml_dir = "LTL/corrected_version/ltlutils"  # Update this path
    nusmv_bin = "/usr/local/bin"  # Update this path to your NuSMV bin directory (not the nusmv executable)
    
    if not Path(ocaml_dir).exists():
        print(f"❌ OCaml directory not found: {ocaml_dir}")
        print("Please update the 'ocaml_dir' variable with the correct path.")
        sys.exit(1)
    
    generator = NuSMVTraceGenerator(ocaml_dir=ocaml_dir, nusmv_bin_path=nusmv_bin)
    
    # Setup environment
    if not generator.setup_environment():
        print("❌ Failed to setup OCaml environment")
        sys.exit(1)
    
    # Example formulas
    detailed = "G(alarm_active -> (F(alarm_reset) & (alarm_reset | X(alarm_reset) | X(X(alarm_reset)))))"
    python = "G(alarm_active -> (X(alarm_reset) | X(X(alarm_reset)) | X(X(X(alarm_reset)))))"
    
    print("\n" + "="*60)
    print("LTL Trace Generator")
    print("=" * 60)
    
    # Generate traces for all combinations
    results = generator.generate_truth_table_traces(detailed, python, verbose=True)
    
    print("\n" + "=" * 60)
    print("SUMMARY OF RESULTS")
    print("=" * 60)
    
    for combo, trace in results.items():
        print(f"\n{combo}:")
        if trace:
            print(f"  ✓ {trace}")
        else:
            print(f"  ✗ UNSATISFIABLE")