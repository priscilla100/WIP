"""
SySLite2 Synthesis Tool Interface Module
Handles LTL formula synthesis from positive and negative example traces
"""

import subprocess
import tempfile
import os
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class SynthesisResult:
    """Result from SySLite synthesis"""
    formulas: List[str]
    synthesis_time: float
    success: bool
    error_message: Optional[str] = None


class SySLiteInterface:
    """
    Interface for SySLite2 LTL formula synthesis tool.
    
    SySLite learns LTL formulas from positive and negative example traces
    using bit-vector SyGuS encoding.
    """
    
    def __init__(self, syslite_dir: str = "."):
        """
        Initialize SySLite interface.
        
        Args:
            syslite_dir: Path to SySLite installation directory
        """
        self.syslite_dir = Path(syslite_dir)
        self.driver_script = self.syslite_dir / "src" / "Driver.py"
        self._verify_setup()
    
    def _verify_setup(self):
        """Verify SySLite is properly installed"""
        if not self.syslite_dir.exists():
            raise FileNotFoundError(f"SySLite directory not found: {self.syslite_dir}")
        
        if not self.driver_script.exists():
            raise FileNotFoundError(
                f"SySLite Driver.py not found at: {self.driver_script}\n"
                f"Please ensure SySLite is properly installed."
            )
        
        print(f"✓ SySLite found: {self.driver_script}")
    
    def create_trace_file(self,
                         aps: List[str],
                         positive_traces: List[Dict],
                         negative_traces: List[Dict],
                         unary_operators: Optional[List[str]] = None,
                         binary_operators: Optional[List[str]] = None,
                         formula_size: Optional[int] = None,
                         target_formula: Optional[str] = None) -> str:
        """
        Create SySLite trace file content.
        
        Args:
            aps: List of atomic propositions
            positive_traces: List of positive example traces
            negative_traces: List of negative example traces
            unary_operators: Allowed unary operators (!, Y, O, H, F, G, X)
            binary_operators: Allowed binary operators (S, &, |, =>, U)
            formula_size: Target formula size
            target_formula: Target formula for matching (optional)
        
        Returns:
            Trace file content as string
        """
        lines = []
        
        # Section 1: Atomic Propositions
        lines.append(','.join(aps))
        lines.append('---')
        
        # Section 2: Positive Traces
        if not positive_traces:
            lines.append('')  # Empty positive section
        else:
            for trace in positive_traces:
                trace_str = self._format_trace(trace, aps)
                lines.append(trace_str)
        lines.append('---')
        
        # Section 3: Negative Traces
        if not negative_traces:
            lines.append('')  # Empty negative section
        else:
            for trace in negative_traces:
                trace_str = self._format_trace(trace, aps)
                lines.append(trace_str)
        lines.append('---')
        
        # Section 4: Unary Operators (Optional)
        if unary_operators:
            lines.append(','.join(unary_operators))
            lines.append('---')
        
        # Section 5: Binary Operators (Optional)
        if binary_operators:
            lines.append(','.join(binary_operators))
            lines.append('---')
        
        # Section 6: Formula Size (Optional)
        if formula_size:
            lines.append(str(formula_size))
            lines.append('---')
        
        # Section 7: Target Formula (Optional)
        if target_formula:
            lines.append(target_formula)
        
        return '\n'.join(lines)
    
    def _format_trace(self, trace: Dict, aps: List[str]) -> str:
        """
        Format a single trace for SySLite.
        
        Trace format: state1;state2;...;stateN::loop_index
        State format: val1,val2,...,valN (ordered by aps)
        
        Args:
            trace: Dictionary with 'states' and optional 'loop_index'
            aps: Ordered list of atomic propositions
        
        Returns:
            Formatted trace string
        """
        states = trace.get('states', [])
        loop_index = trace.get('loop_index', None)
        
        if not states:
            # Return default trace
            return ','.join(['0'] * len(aps))
        
        state_strs = []
        for state in states:
            # Create ordered values based on APs
            if isinstance(state, dict):
                values = [str(int(state.get(ap, False))) for ap in aps]
            else:
                # If state is already a list
                values = [str(int(v)) for v in state]
            
            state_strs.append(','.join(values))
        
        result = ';'.join(state_strs)
        
        # Add loop index if present
        if loop_index is not None:
            result += f"::{loop_index}"
        
        return result
    
    def parse_nusmv_to_syslite_trace(self, nusmv_trace_text: str, aps: List[str]) -> str:
        """
        Convert NuSMV trace format to SySLite format.
        
        NuSMV format:
            A
            Loop starts here
            B
            Loop ends here
            C
            Loop starts here
            D
        
        SySLite format:
            A; B::1; C; D::3
        
        Args:
            nusmv_trace_text: NuSMV trace as text
            aps: Atomic propositions
        
        Returns:
            SySLite formatted trace
        """
        lines = nusmv_trace_text.strip().split('\n')
        states = []
        loop_indices = []
        
        in_loop = False
        loop_start_idx = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if 'loop starts' in line.lower():
                in_loop = True
                loop_start_idx = len(states)
                continue
            
            if 'loop ends' in line.lower():
                if loop_start_idx is not None:
                    loop_indices.append(loop_start_idx)
                in_loop = False
                loop_start_idx = None
                continue
            
            # Parse state assignment
            if '=' in line or '|=>' in line:
                state = {}
                # Handle both formats: "var=value" and "var |=> value"
                assignments = re.findall(r'(\w+)\s*(?:=|=>)\s*(\w+)', line)
                for var, value in assignments:
                    if var in aps:
                        state[var] = (value.lower() == 'true' or value == '1')
                
                if state:
                    states.append(state)
        
        # Format for SySLite
        if not states:
            return ','.join(['0'] * len(aps))
        
        state_strs = []
        for i, state in enumerate(states):
            values = [str(int(state.get(ap, False))) for ap in aps]
            state_str = ','.join(values)
            
            # Check if this state is a loop point
            if i in loop_indices:
                state_str += f"::{i}"
            
            state_strs.append(state_str)
        
        return ';'.join(state_strs)
    
    def synthesize(self,
                  trace_file_content: str,
                  max_formulas: int = 5,
                  timeout: int = 60) -> SynthesisResult:
        """
        Run SySLite synthesis.
        
        Args:
            trace_file_content: Content of trace file
            max_formulas: Maximum number of formulas to find
            timeout: Timeout in seconds
        
        Returns:
            SynthesisResult object
        """
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.trace', delete=False) as trace_f:
            trace_f.write(trace_file_content)
            trace_file = trace_f.name
        
        result_file = tempfile.mktemp(suffix='.txt')
        
        try:
            # Build command
            cmd = [
                'python3',
                str(self.driver_script),
                '-l', 'ltl',
                '-n', str(max_formulas),
                '-r', result_file,
                '-a', 'bv_sygus',
                '-dict',
                '-t', trace_file
            ]
            
            # Execute synthesis
            import time
            start_time = time.time()
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.syslite_dir
            )
            
            synthesis_time = time.time() - start_time
            
            # Parse output
            output = result.stdout + result.stderr
            formulas = self._parse_synthesis_output(output)
            
            if formulas:
                return SynthesisResult(
                    formulas=formulas,
                    synthesis_time=synthesis_time,
                    success=True
                )
            else:
                return SynthesisResult(
                    formulas=[],
                    synthesis_time=synthesis_time,
                    success=False,
                    error_message="No formulas found in output"
                )
            
        except subprocess.TimeoutExpired:
            return SynthesisResult(
                formulas=[],
                synthesis_time=timeout,
                success=False,
                error_message=f"Synthesis timed out after {timeout} seconds"
            )
        except Exception as e:
            return SynthesisResult(
                formulas=[],
                synthesis_time=0,
                success=False,
                error_message=str(e)
            )
        finally:
            # Cleanup
            if os.path.exists(trace_file):
                os.unlink(trace_file)
            if os.path.exists(result_file):
                os.unlink(result_file)
    
    def _parse_synthesis_output(self, output: str) -> List[str]:
        """
        Parse SySLite output to extract formulas.
        
        Output format:
            2025-12-11 17:22:19,454: INFO - Found Formula G(!(&(failure,X(failure))))
            2025-12-11 17:22:19,454: INFO - Time: 1.97 seconds
        
        Args:
            output: SySLite stdout/stderr
        
        Returns:
            List of found formulas
        """
        formulas = []
        
        # Pattern: "Found Formula <formula>"
        pattern = r'Found Formula\s+(.+?)(?:\n|$)'
        matches = re.findall(pattern, output)
        
        for match in matches:
            formula = match.strip()
            if formula and formula not in formulas:
                formulas.append(formula)
        
        return formulas
    
    def convert_syslite_to_standard_ltl(self, syslite_formula: str) -> str:
        """
        Convert SySLite formula notation to standard LTL.
        
        SySLite uses:
        - G(φ) → standard G
        - F(φ) → standard F
        - X(φ) → standard X
        - U(φ,ψ) → standard φ U ψ
        - &(φ,ψ) → standard φ & ψ
        - |(φ,ψ) → standard φ | ψ
        - !(φ) → standard !φ
        - =>(φ,ψ) → standard φ -> ψ
        
        Args:
            syslite_formula: Formula in SySLite notation
        
        Returns:
            Formula in standard LTL notation
        """
        formula = syslite_formula
        
        # Convert binary operators from prefix to infix
        # U(φ,ψ) → (φ U ψ)
        formula = re.sub(r'U\(([^,]+),([^)]+)\)', r'(\1 U \2)', formula)
        
        # &(φ,ψ) → (φ & ψ)
        formula = re.sub(r'&\(([^,]+),([^)]+)\)', r'(\1 & \2)', formula)
        
        # |(φ,ψ) → (φ | ψ)
        formula = re.sub(r'\|\(([^,]+),([^)]+)\)', r'(\1 | \2)', formula)
        
        # =>(φ,ψ) → (φ -> ψ)
        formula = re.sub(r'=>\(([^,]+),([^)]+)\)', r'(\1 -> \2)', formula)
        
        # S(φ,ψ) → (φ S ψ)
        formula = re.sub(r'S\(([^,]+),([^)]+)\)', r'(\1 S \2)', formula)
        
        # !(φ) → !φ
        formula = re.sub(r'!\(([^)]+)\)', r'!\1', formula)
        
        # Unary operators G, F, X, Y, O, H are already in standard form
        
        return formula


# Example usage
if __name__ == "__main__":
    syslite = SySLiteInterface()
    
    # Example: Create trace file for emergency alert system
    aps = ['failure', 'alarm']
    
    positive_traces = [
        {
            'states': [
                {'failure': True, 'alarm': True},
                {'failure': False, 'alarm': True},
                {'failure': False, 'alarm': False}
            ],
            'loop_index': None
        },
        {
            'states': [
                {'failure': True, 'alarm': False},
                {'failure': False, 'alarm': True},
                {'failure': False, 'alarm': True}
            ],
            'loop_index': 1
        }
    ]
    
    negative_traces = [
        {
            'states': [
                {'failure': True, 'alarm': False},
                {'failure': True, 'alarm': False},
                {'failure': True, 'alarm': False}
            ],
            'loop_index': None
        }
    ]
    
    # Create trace file
    trace_content = syslite.create_trace_file(
        aps=aps,
        positive_traces=positive_traces,
        negative_traces=negative_traces,
        unary_operators=['!', 'F', 'G', 'X'],
        binary_operators=['&', '|', '=>', 'U']
    )
    
    print("Trace file content:")
    print(trace_content)
    print("\n" + "="*50 + "\n")
    
    # Run synthesis
    print("Running synthesis...")
    result = syslite.synthesize(trace_content, max_formulas=5, timeout=60)
    
    if result.success:
        print(f"✓ Synthesis successful! ({result.synthesis_time:.2f}s)")
        print(f"Found {len(result.formulas)} formulas:")
        for i, formula in enumerate(result.formulas, 1):
            print(f"  {i}. {formula}")
            std_formula = syslite.convert_syslite_to_standard_ltl(formula)
            print(f"     Standard: {std_formula}")
    else:
        print(f"✗ Synthesis failed: {result.error_message}")
