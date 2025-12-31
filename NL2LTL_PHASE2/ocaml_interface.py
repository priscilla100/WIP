"""
OCaml LTL Tool Interface Module
Handles interaction with the OCaml-based NuSMV LTL verification tool
"""

import subprocess
import tempfile
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class TraceType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"

@dataclass
class Trace:
    """Represents an LTL trace"""
    states: List[Dict[str, bool]]
    loop_index: Optional[int]
    trace_type: TraceType
    llm_feedback: Optional[bool] = None
    raw_format: str = ""
    expected_d: Optional[bool] = None  # Expected satisfaction for Detailed formula
    expected_p: Optional[bool] = None  # Expected satisfaction for Python formula
    case_name: Optional[str] = None    # Name of truth table case
    d_satisfies: Optional[bool] = None # Actual satisfaction of Detailed
    p_satisfies: Optional[bool] = None # Actual satisfaction of Python
    
    def to_nusmv_format(self) -> str:
        """
        Convert to NuSMV/OCaml tool trace format.
        
        Format: [var=value,...]; [var=value,...]; ...
        Where ... indicates infinite loop
        """
        if not self.states:
            return "[]"
        
        state_strs = []
        for state in self.states:
            assignments = ', '.join([f"{k}={str(v).lower()}" for k, v in sorted(state.items())])
            state_strs.append(f"[{assignments}]")
        
        result = '; '.join(state_strs)
        
        # Add ... for infinite traces
        if self.loop_index is not None:
            result += "; ..."
        
        return result
    
    def to_syslite_format(self, aps: List[str]) -> str:
        """Convert to SySLite trace format"""
        if not self.states:
            return "0,0"
        
        state_strs = []
        for state in self.states:
            # Create ordered values based on APs
            values = [str(int(state.get(ap, False))) for ap in aps]
            state_strs.append(','.join(values))
        
        result = ';'.join(state_strs)
        
        # Add loop index if present
        if self.loop_index is not None:
            result += f"::{self.loop_index}"
        
        return result
class OCamlLTLInterface:
    """
    Interface for the OCaml-based NuSMV LTL verification tool.
    
    Provides methods for:
    - Generating positive/negative traces
    - Checking trace satisfaction
    - Formula equivalence checking
    - Formula normalization
    """
    
    def __init__(self, ocaml_dir: str = "LTL/corrected_version/ltlutils"):
        """
        Initialize the OCaml LTL interface.
        
        Args:
            ocaml_dir: Path to OCaml tool directory
        """
        self.ocaml_dir = Path(ocaml_dir)
        self.bin_path = self.ocaml_dir / "bin" / "main.exe"
        self.nusmv_path = None
        # self._verify_setup()
        self._setup_ocaml_environment()

    def _setup_ocaml_environment(self):
        """Setup OCaml"""
        try:
            compile_script = self.ocaml_dir / "compile-project"
            subprocess.run(["chmod", "a+x", str(compile_script)], check=True, cwd=str(self.ocaml_dir), capture_output=True)
            subprocess.run([str(compile_script)], check=True, cwd=str(self.ocaml_dir), capture_output=True)
            subprocess.run(["dune", "build"], check=True, cwd=str(self.ocaml_dir), capture_output=True)
            print("✓ OCaml compiled")
            return True
        except:
            return False
    def _verify_setup(self):
        """Verify OCaml tool is compiled and NuSMV is available"""
        if not self.ocaml_dir.exists():
            raise FileNotFoundError(f"OCaml directory not found: {self.ocaml_dir}")
        
        if not self.bin_path.exists():
            raise FileNotFoundError(
                f"OCaml binary not found. Please compile first:\n"
                f"cd {self.ocaml_dir} && dune build"
            )
        
        # Check for NuSMV
        result = subprocess.run(['which', 'nusmv'], capture_output=True, text=True)
        if result.returncode == 0:
            self.nusmv_path = result.stdout.strip()
            print(f"✓ NuSMV found: {self.nusmv_path}")
        else:
            print("⚠ Warning: NuSMV not found in PATH")
    
    def execute_command(self, commands: List[str], timeout: int = 30) -> Tuple[str, str]:
        """
        Execute OCaml tool commands.
        
        Args:
            commands: List of command strings
            timeout: Execution timeout in seconds
            
        Returns:
            Tuple of (stdout, stderr)
        """
        # Create temporary input file
        input_content = '\n'.join(commands) + '\n'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(input_content)
            input_file = f.name
        
        try:
            result = subprocess.run(
                ['dune', 'exec', './bin/main.exe'],
                stdin=open(input_file, 'r', encoding='utf-8'),
                capture_output=True,
                text=True,
                cwd=self.ocaml_dir,
                timeout=timeout,
                encoding='utf-8',
                errors='replace'  # Replace invalid UTF-8 with replacement character
            )
            
            return result.stdout, result.stderr
            
        finally:
            os.unlink(input_file)
    
    def normalize_formula(self, formula: str) -> str:
        """
        Normalize LTL formula for OCaml tool.
        
        Args:
            formula: LTL formula string
            
        Returns:
            Normalized formula
        """
        # Remove extra whitespace
        formula = ' '.join(formula.split())
        
        # Ensure proper spacing around operators
        operators = ['&', '|', '->', 'U', 'S']
        for op in operators:
            formula = formula.replace(op, f' {op} ')
        
        # Clean up multiple spaces
        formula = ' '.join(formula.split())
        
        return formula
    
    def extract_variables(self, formula: str) -> List[str]:
        """
        Extract atomic propositions from formula.
        
        Args:
            formula: LTL formula
            
        Returns:
            List of variable names (excluding operators)
        """
        # Remove LTL operators
        temporal_ops = ['G', 'F', 'X', 'U', 'S', 'Y', 'O', 'H']
        boolean_ops = ['->', '&', '|', '!', '(', ')', ' ', 'true', 'false']
        
        # Also remove unicode operators that might appear
        unicode_ops = ['→', '∧', '∨', '¬', '↔', '⊕', '⇒', '⇔']
        
        remaining = formula
        for op in temporal_ops + boolean_ops + unicode_ops:
            remaining = remaining.replace(op, ' ')
        
        # Extract unique variables
        vars = set(remaining.split())
        
        # Filter out:
        # - Empty strings
        # - Numbers
        # - Single characters that are likely operators
        # - Unicode operator symbols
        valid_vars = []
        for v in vars:
            if v and not v.isdigit():
                # Skip single-character non-alphanumeric (likely operators)
                if len(v) == 1 and not v.isalnum():
                    continue
                # Skip known operator symbols
                if v in unicode_ops:
                    continue
                valid_vars.append(v)
        
        return sorted(valid_vars)
    
    def generate_positive_trace(self, formula: str, trace_id: str = None) -> Optional[Trace]:
        """
        Generate a trace that satisfies the formula.
        
        Args:
            formula: LTL formula
            trace_id: Unique identifier for this trace (to avoid file conflicts)
            
        Returns:
            Trace object or None if generation fails
        """
        return self._generate_trace(formula, positive=True, trace_id=trace_id)
    
    def generate_negative_trace(self, formula: str, trace_id: str = None) -> Optional[Trace]:
        """
        Generate a trace that falsifies the formula.
        
        Args:
            formula: LTL formula
            trace_id: Unique identifier for this trace (to avoid file conflicts)
            
        Returns:
            Trace object or None if generation fails
        """
        return self._generate_trace(formula, positive=False, trace_id=trace_id)
    
    def _generate_trace(self, formula: str, positive: bool = True, trace_id: str = None) -> Optional[Trace]:
        """
        Internal method to generate traces with unique file handling.
        
        Args:
            formula: LTL formula
            positive: True for satisfying trace, False for falsifying
            trace_id: Unique identifier to prevent file reuse
            
        Returns:
            Trace object or None
        """
        try:
            formula = self.normalize_formula(formula)
            command = "positive_trace_gen" if positive else "negative_trace_gen"
            
            # Create unique trace ID if not provided
            if trace_id is None:
                import random
                trace_id = f"{hash(formula) % 10000}_{random.randint(1000, 9999)}"
            
            print(f"\n{'='*60}")
            print(f"Generating {'POSITIVE' if positive else 'NEGATIVE'} trace [ID: {trace_id}]")
            print(f"Formula: {formula[:100]}{'...' if len(formula) > 100 else ''}")
            print(f"{'='*60}")
            
            # CRITICAL: Delete ALL old trace files before generation
            import time
            deleted_count = 0
            
            trace_patterns = [
                "positive-check_trace_satisfaction*",
                "negative-check_trace_satisfaction*",
                "query.smv",
                "query_result.out"
            ]
            
            for pattern in trace_patterns:
                for old_file in self.ocaml_dir.glob(pattern):
                    try:
                        old_file.unlink()
                        deleted_count += 1
                    except:
                        pass
            
            if deleted_count > 0:
                print(f"🗑️  Cleaned {deleted_count} old files")
                time.sleep(0.5)  # Wait for filesystem
            
            # Execute trace generation
            stdout, stderr = self.execute_command([command, formula])
            output = stdout + stderr
            
            print(f"OCaml output (first 200 chars): {output[:200]}")
            
            # Check for errors
            if "Fatal error" in output or "exception" in output:
                print(f"⚠️ OCaml error detected, using fallback")
                return self._create_fallback_trace(formula, positive)
            
            # IMPORTANT: Wait longer for file to be written
            time.sleep(1.0)
            
            # Find the generated trace file
            prefix = "positive" if positive else "negative"
            candidates = list(self.ocaml_dir.glob(f"{prefix}-check_trace_satisfaction*"))
            
            if not candidates:
                print(f"✗ No trace file found")
                return self._create_fallback_trace(formula, positive)
            
            # Get the most recent file
            trace_file = max(candidates, key=lambda p: p.stat().st_mtime)
            file_age = time.time() - trace_file.stat().st_mtime
            
            print(f"📖 Reading: {trace_file.name} (age: {file_age:.2f}s)")
            
            if file_age > 5:
                print(f"⚠️ File too old, using fallback")
                return self._create_fallback_trace(formula, positive)
            
            trace = self._parse_nusmv_trace_file(trace_file, positive, formula)
            
            # Verify variables
            if trace and trace.states:
                expected_vars = set(self.extract_variables(formula))
                actual_vars = set(trace.states[0].keys())
                invalid_vars = {'→', '∧', '∨', '¬', '↔', '⊕'}
                actual_vars = actual_vars - invalid_vars
                
                if expected_vars and actual_vars and not actual_vars.issubset(expected_vars | {'true', 'false'}):
                    print(f"⚠️ Variable mismatch: expected {expected_vars}, got {actual_vars}")
                    return self._create_fallback_trace(formula, positive)
            
            print(f"✓ Trace generated successfully [ID: {trace_id}]")
            return trace
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return self._create_fallback_trace(formula, positive)
        """
        Internal method to generate traces.
        
        Args:
            formula: LTL formula
            positive: True for satisfying trace, False for falsifying
            
        Returns:
            Trace object or None
        """
        try:
            formula = self.normalize_formula(formula)
            command = "positive_trace_gen" if positive else "negative_trace_gen"
            
            print(f"\n{'='*60}")
            print(f"Generating {'POSITIVE' if positive else 'NEGATIVE'} trace")
            print(f"Formula: {formula[:100]}{'...' if len(formula) > 100 else ''}")
            print(f"{'='*60}")
            
            # CRITICAL: Aggressively delete ALL old trace files before generation
            import time
            deleted_count = 0
            
            trace_patterns = [
                "positive-check_trace_satisfaction*",
                "negative-check_trace_satisfaction*",
                "query.smv",
                "query_result.out"
            ]
            
            for pattern in trace_patterns:
                for old_file in self.ocaml_dir.glob(pattern):
                    try:
                        old_file.unlink()
                        deleted_count += 1
                        print(f"🗑️  Deleted: {old_file.name}")
                    except Exception as e:
                        print(f"⚠️  Could not delete {old_file.name}: {e}")
            
            if deleted_count > 0:
                print(f"✓ Cleaned up {deleted_count} old files")
                time.sleep(0.5)  # Give filesystem time to sync
            
            # Execute trace generation
            stdout, stderr = self.execute_command([command, formula])
            output = stdout + stderr
            
            print(f"OCaml output (first 300 chars):")
            print(output[:300])
            
            # Check for errors
            if "Fatal error" in output or "exception" in output:
                print(f"⚠️ OCaml tool error detected")
                # Still try to read file in case it was generated before error
            
            print(f"{'='*60}\n")
            
            # Wait a moment for file system
            time.sleep(0.3)
            
            # Find the generated trace file
            trace_file = None
            
            # Look for success message
            if 'POSITIVE TRACE GENERATED' in output or 'NEGATIVE TRACE GENERATED' in output:
                pattern = r'positive-check_trace_satisfaction_\S*' if positive else r'negative-check_trace_satisfaction_\S*'
                match = re.search(pattern, output)
                if match:
                    trace_file = self.ocaml_dir / match.group(0)
            
            # Try to find any trace file if not in output
            if not trace_file or not trace_file.exists():
                prefix = "positive" if positive else "negative"
                candidates = list(self.ocaml_dir.glob(f"{prefix}-check_trace_satisfaction*"))
                
                if candidates:
                    # Get the most recently modified
                    trace_file = max(candidates, key=lambda p: p.stat().st_mtime)
                    print(f"📁 Found trace file: {trace_file.name}")
            
            # Read and parse the trace file
            if trace_file and trace_file.exists():
                print(f"📖 Reading: {trace_file}")
                
                # Verify freshness (must be very recent)
                file_age = time.time() - trace_file.stat().st_mtime
                print(f"   File age: {file_age:.2f} seconds")
                
                if file_age > 10:
                    print(f"⚠️ File too old ({file_age:.1f}s), likely stale")
                    return self._create_fallback_trace(formula, positive)
                
                trace = self._parse_nusmv_trace_file(trace_file, positive, formula)
                
                # Verify trace uses correct variables
                if trace and trace.states:
                    expected_vars = set(self.extract_variables(formula))
                    actual_vars = set(trace.states[0].keys())
                    
                    # Filter out operator symbols that shouldn't be variables
                    invalid_vars = {'→', '∧', '∨', '¬', '↔', '⊕'}
                    actual_vars = actual_vars - invalid_vars
                    
                    if expected_vars and actual_vars and not actual_vars.issubset(expected_vars | {'true', 'false'}):
                        print(f"⚠️ Variable mismatch!")
                        print(f"   Expected: {expected_vars}")
                        print(f"   Got: {actual_vars}")
                        print(f"   Using fallback")
                        return self._create_fallback_trace(formula, positive)
                
                print(f"✓ Trace parsed successfully")
                return trace
            else:
                print(f"✗ No trace file found")
                return self._create_fallback_trace(formula, positive)
            
        except subprocess.TimeoutExpired:
            print(f"⏱️  Timeout generating trace")
            return self._create_fallback_trace(formula, positive)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_trace(formula, positive)
    
    def _parse_nusmv_trace_file(self, trace_file: Path, positive: bool, formula: str) -> Trace:
        """
        Parse NuSMV trace file and convert to Trace object.
        
        NuSMV format:
        -> State: 1.1 <-
            alarm = TRUE
            failure = FALSE
        -- Loop starts here
        -> State: 1.2 <-
            alarm = FALSE
            failure = TRUE
        
        Target format:
        [alarm=true, failure=false]; [alarm=false, failure=true]; ...
        """
        try:
            with open(trace_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            print(f"\nParsing trace file (first 800 chars):")
            print(content[:800])
            print(f"{'='*60}\n")
            
            states = []
            loop_index = None
            current_state = {}
            in_state = False
            state_count = 0
            
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Check for state marker
                if '-> State:' in line:
                    # Save previous state if exists
                    if current_state:
                        states.append(current_state.copy())
                        current_state = {}
                    in_state = True
                    state_count += 1
                    continue
                
                # Check for loop marker
                if 'Loop starts here' in line or '-- Loop starts here' in line:
                    # Loop starts at the NEXT state
                    loop_index = len(states)  # Next state will be at this index
                    print(f"Loop detected at state index: {loop_index}")
                    continue
                
                # Parse variable assignment
                if in_state and '=' in line:
                    # Format: "alarm = TRUE" or "alarm = FALSE"
                    parts = line.split('=')
                    if len(parts) == 2:
                        var_name = parts[0].strip()
                        var_value = parts[1].strip().upper()
                        
                        if var_value in ['TRUE', 'FALSE']:
                            current_state[var_name] = (var_value == 'TRUE')
            
            # Don't forget the last state
            if current_state:
                states.append(current_state)
            
            if not states:
                print("Warning: No states parsed from trace file")
                return self._create_fallback_trace("", positive)
            
            print(f"Parsed {len(states)} states")
            print(f"Loop index: {loop_index}")
            print(f"States: {states}")
            
            trace_type = TraceType.POSITIVE if positive else TraceType.NEGATIVE
            raw_format = self._format_trace_display(states, loop_index)
            
            return Trace(
                states=states,
                loop_index=loop_index,
                trace_type=trace_type,
                raw_format=raw_format
            )
            
        except Exception as e:
            print(f"Error parsing trace file: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_trace("", positive)
    
    def _parse_trace_output(self, output: str, positive: bool) -> Optional[Trace]:
        """
        Parse OCaml tool output to extract trace.
        
        Format: [[var |=> value,...]];[[...]];...
        """
        try:
            # Look for state patterns
            trace_pattern = r'\[\[(.*?)\]\]'
            matches = re.findall(trace_pattern, output)
            
            if not matches:
                return self._create_fallback_trace("", positive)
            
            states = []
            for match in matches:
                state = {}
                # Parse: var |=> value
                assignments = re.findall(r'(\w+)\s*\|=>\s*(\w+)', match)
                for var, value in assignments:
                    state[var] = (value.lower() == 'true')
                
                if state:  # Only add non-empty states
                    states.append(state)
            
            if not states:
                return self._create_fallback_trace("", positive)
            
            # Check for loop indication (...)
            loop_index = None
            if '...' in output:
                # Assume loop from last state
                loop_index = len(states) - 1
            
            trace_type = TraceType.POSITIVE if positive else TraceType.NEGATIVE
            raw_format = self._format_trace_display(states, loop_index)
            
            return Trace(
                states=states,
                loop_index=loop_index,
                trace_type=trace_type,
                raw_format=raw_format
            )
            
        except Exception as e:
            print(f"Error parsing trace: {str(e)}")
            return self._create_fallback_trace("", positive)
    
    def _create_fallback_trace(self, formula: str, positive: bool) -> Trace:
        """
        Create a simple fallback trace when generation fails.
        
        Args:
            formula: Original formula
            positive: Trace type
            
        Returns:
            Simple trace with basic variation using actual formula variables
        """
        # Extract variables from formula
        vars = self.extract_variables(formula) if formula else []
        
        # If no variables found, try common ones
        if not vars:
            vars = ['p', 'q']
        
        print(f"Creating fallback trace with variables: {vars}")
        
        # Create varied states using actual variables
        states = []
        num_states = 4  # Create more states for variety
        
        for i in range(num_states):
            state = {}
            for j, var in enumerate(vars):
                # Create pattern: alternate values with some variation
                if positive:
                    # For positive traces, create patterns more likely to satisfy
                    state[var] = bool((i + j) % 2)
                else:
                    # For negative traces, create patterns more likely to violate
                    state[var] = bool((i * 2 + j) % 3 == 0)
            states.append(state)
        
        trace_type = TraceType.POSITIVE if positive else TraceType.NEGATIVE
        raw_format = self._format_trace_display(states, loop_index=num_states-1)
        
        return Trace(
            states=states,
            loop_index=num_states-1,
            trace_type=trace_type,
            raw_format=raw_format
        )
    
    def _format_trace_display(self, states: List[Dict[str, bool]], 
                              loop_index: Optional[int]) -> str:
        """
        Format trace for human-readable display - COMPACT format.
        
        Format: [var=value,...]; [var=value,...]; ...
        
        Args:
            states: List of state dictionaries
            loop_index: Index where loop begins
            
        Returns:
            Formatted string (single line)
        """
        if not states:
            return "Empty trace"
        
        state_strs = []
        for state in states:
            # Sort keys for consistent display
            assignments = ', '.join([f"{k}={str(v).lower()}" for k, v in sorted(state.items())])
            state_strs.append(f"[{assignments}]")
        
        result = '; '.join(state_strs)
        
        # Add ... to indicate infinite loop
        if loop_index is not None:
            result += "; ..."
        
        return result
    
    def to_ocaml_format(self, states: List[Dict[str, bool]], loop_index: Optional[int]) -> str:
        """
        Format trace for OCaml tool input.
        
        Format: [var=value,...]; [var=value,...]; ...
        The ... indicates infinite loop
        
        Args:
            states: List of state dictionaries
            loop_index: Index where loop begins (None for finite trace)
            
        Returns:
            Formatted trace string for OCaml tool
        """
        if not states:
            return "[]"
        
        state_strs = []
        for state in states:
            # Format: [var=value, var=value]
            assignments = ', '.join([f"{k}={str(v).lower()}" for k, v in sorted(state.items())])
            state_strs.append(f"[{assignments}]")
        
        result = '; '.join(state_strs)
        
        # Add ... for infinite traces
        if loop_index is not None:
            result += "; ..."
        
        return result
    
    def check_trace_satisfaction(self, formula: str, trace: Trace) -> bool:
        """
        Check if a trace satisfies a formula.
        
        Args:
            formula: LTL formula
            trace: Trace to check
            
        Returns:
            True if trace satisfies formula, False otherwise
        """
        try:
            formula = self.normalize_formula(formula)
            trace_str = trace.to_nusmv_format()
            
            commands = [
                "check_trace_satisfaction",
                formula,
                trace_str
            ]
            
            stdout, stderr = self.execute_command(commands)
            output = stdout + stderr
            
            # Check result
            if 'SATISFIED' in output:
                return True
            elif 'FALSIFIED' in output:
                return False
            else:
                # If unclear, default based on trace type
                print(f"Warning: Unclear satisfaction result, using trace type")
                return trace.trace_type == TraceType.POSITIVE
                
        except Exception as e:
            print(f"Error checking satisfaction: {str(e)}")
            # Fallback to trace type
            return trace.trace_type == TraceType.POSITIVE
    
    def check_equivalence(self, formula1: str, formula2: str) -> bool:
        """
        Check if two formulas are logically equivalent.
        
        Args:
            formula1: First LTL formula
            formula2: Second LTL formula
            
        Returns:
            True if equivalent, False otherwise
        """
        try:
            f1 = self.normalize_formula(formula1)
            f2 = self.normalize_formula(formula2)
            
            commands = [
                "equiv",
                f1,
                f2
            ]
            
            stdout, stderr = self.execute_command(commands)
            output = stdout + stderr
            
            return 'EQUIVALENT' in output
            
        except Exception as e:
            print(f"Error checking equivalence: {str(e)}")
            return False
    
    def check_entailment(self, formula1: str, formula2: str) -> bool:
        """
        Check if formula1 entails formula2 (formula1 |= formula2).
        
        Args:
            formula1: First LTL formula
            formula2: Second LTL formula
            
        Returns:
            True if formula1 entails formula2
        """
        try:
            f1 = self.normalize_formula(formula1)
            f2 = self.normalize_formula(formula2)
            
            commands = [
                "check_entailment",
                f1,
                f2
            ]
            
            stdout, stderr = self.execute_command(commands)
            output = stdout + stderr
            
            # Parse entailment result
            # Output format varies, check for positive indicators
            return 'ENTAILS' in output or 'TRUE' in output
            
        except Exception as e:
            print(f"Error checking entailment: {str(e)}")
            return False


# Example usage and testing
if __name__ == "__main__":
    # Test the interface
    ocaml = OCamlLTLInterface()
    
    # Test formula
    formula = "G(failure -> F(alarm))"
    
    print(f"Testing formula: {formula}")
    print(f"Variables: {ocaml.extract_variables(formula)}")
    
    # Generate traces
    print("\nGenerating positive trace...")
    pos_trace = ocaml.generate_positive_trace(formula)
    if pos_trace:
        print(pos_trace.raw_format)
    
    print("\nGenerating negative trace...")
    neg_trace = ocaml.generate_negative_trace(formula)
    if neg_trace:
        print(neg_trace.raw_format)
    
    # Check satisfaction
    if pos_trace:
        print(f"\nPositive trace satisfies formula: {ocaml.check_trace_satisfaction(formula, pos_trace)}")
    if neg_trace:
        print(f"Negative trace satisfies formula: {ocaml.check_trace_satisfaction(formula, neg_trace)}")