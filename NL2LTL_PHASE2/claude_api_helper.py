"""
Claude API Helper Module
Handles interactions with Claude for AP extraction, formula generation, and feedback
"""

import os
from typing import List, Dict, Optional, Tuple
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ClaudeAPIHelper:
    """Helper class for Claude API interactions"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude API helper.
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError(
                "No API key provided. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"
    
    def extract_atomic_propositions(self, nl_requirement: str) -> Tuple[List[str], str]:
        """
        Extract atomic propositions from natural language requirement.
        
        Uses maximal logical revelation principle: reveal the deepest logical
        structure supported by LTL, not just surface-level predicates.
        
        Args:
            nl_requirement: Natural language requirement
        
        Returns:
            Tuple of (list of APs, explanation)
        """
        prompt = f"""You are an expert in Linear Temporal Logic (LTL) and formal specification.

Your task is to extract atomic propositions (APs) from the following natural language requirement.

**CRITICAL PRINCIPLE - Maximal Logical Revelation:**
Always reveal the deepest logical structure supported by LTL, not just surface-level predicates.

For example:
- "The alarm sounds" → Don't just extract "alarm_sounds"
- Instead extract: "alarm_active", "alarm_triggered", "sound_playing" if these are the underlying states
- "The system is in safe mode" → Extract the boolean state: "safe_mode"
- "A failure is detected" → Extract: "failure_detected"

**Guidelines:**
1. Extract boolean-valued atomic propositions (true/false states)
2. Use clear, concise names (e.g., "failure", "alarm", "armed")
3. Avoid redundancy (don't create "alarm_on" and "alarm_off" - just "alarm")
4. Consider temporal aspects that need separate APs
5. Think about what needs to be tracked over time

**Natural Language Requirement:**
{nl_requirement}

**Output Format:**
Provide your response in this exact format:

ATOMIC_PROPOSITIONS:
- ap_name_1: Brief description of what it represents
- ap_name_2: Brief description
- ...

EXPLANATION:
Brief explanation of your choices and any assumptions made.

Begin your analysis:"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response = message.content[0].text
            
            # Parse response
            aps = []
            explanation = ""
            
            lines = response.split('\n')
            in_aps = False
            in_explanation = False
            
            for line in lines:
                line = line.strip()
                
                if 'ATOMIC_PROPOSITIONS:' in line:
                    in_aps = True
                    in_explanation = False
                    continue
                
                if 'EXPLANATION:' in line:
                    in_aps = False
                    in_explanation = True
                    continue
                
                if in_aps and line.startswith('-'):
                    # Extract AP name (before colon)
                    ap_line = line[1:].strip()
                    if ':' in ap_line:
                        ap_name = ap_line.split(':')[0].strip()
                        aps.append(ap_name)
                
                if in_explanation and line:
                    explanation += line + " "
            
            if not aps:
                # Fallback: try to extract from response
                import re
                ap_pattern = r'-\s*(\w+):'
                aps = re.findall(ap_pattern, response)
            
            return aps, explanation.strip()
            
        except Exception as e:
            raise Exception(f"Error extracting APs: {str(e)}")
    
    def generate_detailed_formula(self, 
                                  nl_requirement: str, 
                                  aps: List[str]) -> Tuple[str, str]:
        """
        Generate LTL formula using detailed strategy.
        
        Args:
            nl_requirement: Natural language requirement
            aps: List of atomic propositions
        
        Returns:
            Tuple of (LTL formula, explanation)
        """
        aps_str = ', '.join(aps)
        
        prompt = f"""You are an expert in Linear Temporal Logic (LTL) translation.

Your task is to translate the following natural language requirement into a COMPLETE, VALID LTL formula.

**Available Atomic Propositions:**
{aps_str}

**LTL Operators:**
- G (Globally/Always): G(φ) means φ holds at all future states
- F (Finally/Eventually): F(φ) means φ holds at some future state
- X (Next): X(φ) means φ holds in the next state
- U (Until): φ U ψ means φ holds until ψ becomes true
- S (Since): φ S ψ means φ has held since ψ was true (past)
- Y (Yesterday): Y(φ) means φ held in the previous state (past)
- O (Once): O(φ) means φ held at some past state
- H (Historically): H(φ) has always held (past)
- Boolean: & (and), | (or), ! (not), -> (implies)

**Natural Language Requirement:**
{nl_requirement}

**CRITICAL INSTRUCTIONS:**
1. Generate a COMPLETE formula - do NOT leave it incomplete
2. Use ONLY the atomic propositions provided: {aps_str}
3. Use standard LTL notation with proper parentheses
4. The formula must be syntactically valid and executable
5. Explain your translation clearly

IMPORTANT SYNTAX RULES:
- Do NOT use operator chaining like XX(p) or XXX(p)
- Nested operators MUST be written explicitly:
  ✅ X(X(p))
  ❌ XX(p)
- Every temporal operator takes exactly ONE argument
- Parentheses are REQUIRED around operator arguments

**Output Format:**
FORMULA:
<complete LTL formula on a single line>

EXPLANATION:
<step-by-step explanation of your translation>

**Example:**
Requirement: "The alarm sounds after every failure"
Formula: G(failure -> F(alarm))

Now translate the requirement above:"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response = message.content[0].text
            
            # Parse response more carefully
            formula = ""
            explanation = ""
            
            lines = response.split('\n')
            in_formula = False
            in_explanation = False
            
            for line in lines:
                stripped = line.strip()
                
                if 'FORMULA:' in stripped:
                    in_formula = True
                    in_explanation = False
                    # Check if formula is on same line
                    if ':' in stripped:
                        formula_part = stripped.split(':', 1)[1].strip()
                        if formula_part and not formula_part.startswith('<'):
                            formula = formula_part
                            in_formula = False
                    continue
                
                if 'EXPLANATION:' in stripped:
                    in_formula = False
                    in_explanation = True
                    continue
                
                if in_formula and stripped and not stripped.startswith('<'):
                    # Take the first non-empty line as formula
                    formula = stripped
                    in_formula = False
                
                if in_explanation and stripped:
                    explanation += stripped + " "
            
            # Fallback: try to find formula patterns in response
            if not formula or len(formula) < 5:
                import re
                # Look for LTL patterns (must contain operators and propositions)
                pattern = r'(?:G|F|X|U|S|Y|O|H)\s*\([^)]+\)'
                matches = re.findall(pattern, response)
                if matches:
                    # Find the longest match (most likely the complete formula)
                    formula = max(matches, key=len)
            
            # Validate formula uses provided APs
            if formula:
                for ap in aps:
                    if ap not in formula:
                        explanation += f" Note: Atomic proposition '{ap}' not used in formula."
            
            return formula.strip(), explanation.strip()
            
        except Exception as e:
            raise Exception(f"Error generating detailed formula: {str(e)}")
    
    def generate_python_formula(self, 
                                nl_requirement: str, 
                                aps: List[str]) -> Tuple[str, str]:
        """
        Generate LTL formula using Python AST strategy.
        
        Args:
            nl_requirement: Natural language requirement
            aps: List of atomic propositions
        
        Returns:
            Tuple of (Python AST representation, standard LTL, explanation)
        """
        aps_str = ', '.join(aps)
        
        prompt = f"""You are an expert in LTL and Python programming.

Your task is to express an LTL formula as BOTH a Python AST representation AND standard LTL notation.

**Available Atomic Propositions (USE THESE ONLY):**
{aps_str}

**Python LTL Classes:**
- AtomicProposition(name): Represents an atomic proposition
- Globally(φ): G(φ) - Always
- Eventually(φ): F(φ) - Eventually
- Next(φ): X(φ) - Next state
- Until(φ, ψ): φ U ψ
- Since(φ, ψ): φ S ψ
- Yesterday(φ): Y(φ)
- Once(φ): O(φ)
- Historically(φ): H(φ)
- And(φ, ψ): φ & ψ
- Or(φ, ψ): φ | ψ
- Not(φ): !φ
- Implies(φ, ψ): φ -> ψ

**Natural Language Requirement:**
{nl_requirement}

**CRITICAL: You must provide BOTH formats:**
IMPORTANT SYNTAX RULES:
- Do NOT use operator chaining like XX(p) or XXX(p)
- Nested operators MUST be written explicitly:
  ✅ X(X(p))
  ❌ XX(p)
- Every temporal operator takes exactly ONE argument
- Parentheses are REQUIRED around operator arguments

**Output Format:**
PYTHON_AST:
<complete Python AST formula using only the APs: {aps_str}>

STANDARD_LTL:
<the same formula in standard LTL notation>

EXPLANATION:
<brief explanation of the translation>

**Example:**
Requirement: "The alarm eventually sounds after every failure"
PYTHON_AST:
Globally(Implies(AtomicProposition("failure"), Eventually(AtomicProposition("alarm"))))

STANDARD_LTL:
G(failure -> F(alarm))

Now translate the requirement above (use ONLY these APs: {aps_str}):"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response = message.content[0].text
            
            # Parse response more carefully
            python_ast = ""
            standard_ltl = ""
            explanation = ""
            
            lines = response.split('\n')
            in_ast = False
            in_ltl = False
            in_explanation = False
            
            for line in lines:
                stripped = line.strip()
                
                if 'PYTHON_AST:' in stripped:
                    in_ast = True
                    in_ltl = False
                    in_explanation = False
                    # Check if AST is on same line
                    if ':' in stripped:
                        ast_part = stripped.split(':', 1)[1].strip()
                        if ast_part and 'AtomicProposition' in ast_part:
                            python_ast = ast_part
                            in_ast = False
                    continue
                
                if 'STANDARD_LTL:' in stripped or 'STANDARD LTL:' in stripped:
                    in_ast = False
                    in_ltl = True
                    in_explanation = False
                    # Check if LTL is on same line
                    if ':' in stripped:
                        ltl_part = stripped.split(':', 1)[1].strip()
                        if ltl_part and len(ltl_part) > 3:
                            standard_ltl = ltl_part
                            in_ltl = False
                    continue
                
                if 'EXPLANATION:' in stripped:
                    in_ast = False
                    in_ltl = False
                    in_explanation = True
                    continue
                
                if in_ast and stripped and 'AtomicProposition' in stripped:
                    python_ast = stripped
                    in_ast = False
                
                if in_ltl and stripped and len(stripped) > 3:
                    standard_ltl = stripped
                    in_ltl = False
                
                if in_explanation and stripped:
                    explanation += stripped + " "
            
            # If we got Python AST but no standard LTL, try to convert
            if python_ast and not standard_ltl:
                standard_ltl = self._convert_python_ast_to_ltl(python_ast)
            
            # If we got standard LTL but no Python AST, that's okay - use standard
            if standard_ltl and not python_ast:
                python_ast = f"Standard LTL: {standard_ltl}"
            
            return python_ast.strip(), standard_ltl.strip(), explanation.strip()
            
        except Exception as e:
            raise Exception(f"Error generating Python formula: {str(e)}")
    
    def _convert_python_ast_to_ltl(self, python_ast: str) -> str:
        """Quick conversion from Python AST to standard LTL"""
        ltl = python_ast
        # Basic conversions
        ltl = ltl.replace('Globally(', 'G(')
        ltl = ltl.replace('Eventually(', 'F(')
        ltl = ltl.replace('Next(', 'X(')
        ltl = ltl.replace('Implies(', '(').replace(', ', ' -> ', 1)
        ltl = ltl.replace('And(', '(').replace(', ', ' & ', 1)
        ltl = ltl.replace('Or(', '(').replace(', ', ' | ', 1)
        ltl = ltl.replace('Not(', '!(')
        ltl = ltl.replace('AtomicProposition("', '').replace('")', '')
        return ltl
    
    def get_trace_feedback(self, trace_description: str, 
                          nl_requirement: str) -> Tuple[bool, str]:
        """
        Ask Claude if a trace should satisfy the requirement
        
        Returns: (should_satisfy: bool, reasoning: str)
        """
        prompt = f"""You are evaluating whether a trace should satisfy a requirement.

**Original Requirement:**
{nl_requirement}

**Trace:**
{trace_description}

**Question:**
Based on the intended meaning of the requirement, should this trace satisfy the requirement?

**Output Format:**
ANSWER: YES or NO

REASONING:
<brief explanation>

Provide your evaluation:"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            
            # Parse response
            should_satisfy = False
            reasoning = ""
            
            lines = content.split('\n')
            in_reasoning = False
            
            for line in lines:
                line_stripped = line.strip()
                
                if 'ANSWER:' in line_stripped:
                    if 'YES' in line_stripped.upper():
                        should_satisfy = True
                    elif 'NO' in line_stripped.upper():
                        should_satisfy = False
                    continue
                
                if 'REASONING:' in line_stripped:
                    in_reasoning = True
                    continue
                
                if in_reasoning and line_stripped:
                    reasoning += line_stripped + " "
            
            if not reasoning:
                reasoning = content
            
            return {
    "should_satisfy": should_satisfy,
    "reasoning": reasoning.strip()
}
            
        except Exception as e:
            return {
                "should_satisfy": False,
                "reasoning": f"Error: {str(e)}"
            }

    
    
    def repair_formula(self,
                      nl_requirement: str,
                      aps: List[str],
                      traces: List[Dict],
                      mismatches: List[Dict]) -> Tuple[str, str]:
        """
        Request formula repair from Claude based on mismatches.
        
        Args:
            nl_requirement: Original requirement
            aps: Atomic propositions
            traces: List of traces with their properties
            mismatches: List of mismatches between formula and user intent
        
        Returns:
            Tuple of (repaired formula, explanation)
        """
        aps_str = ', '.join(aps)
        
        # Format traces and mismatches
        trace_info = []
        for i, (trace, mismatch) in enumerate(zip(traces, mismatches)):
            trace_info.append(
                f"Trace {i+1}: {trace['description']}\n"
                f"  User expects: {mismatch['user_feedback']}\n"
                f"  Formula gives: {mismatch['formula_result']}\n"
                f"  Mismatch: {'YES' if mismatch['is_mismatch'] else 'NO'}"
            )
        
        traces_str = '\n'.join(trace_info)
        
        prompt = f"""You are an expert in LTL formula repair.

**Original Requirement:**
{nl_requirement}

**Atomic Propositions:**
{aps_str}

**Current Formula Issues:**
The current formula(s) do not align with user intent on the following traces:

{traces_str}

**Your Task:**
Generate a new LTL formula that:
1. Correctly satisfies traces where user expects satisfaction
2. Correctly violates traces where user expects violation
3. Accurately captures the intended meaning of the requirement

**Output Format:**
REPAIRED_FORMULA:
<your new LTL formula>

EXPLANATION:
<explain how this formula addresses the mismatches>

Begin your repair:"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response = message.content[0].text
            
            # Parse response
            formula = ""
            explanation = ""
            
            lines = response.split('\n')
            in_formula = False
            in_explanation = False
            
            for line in lines:
                line = line.strip()
                
                if 'REPAIRED_FORMULA:' in line or 'FORMULA:' in line:
                    in_formula = True
                    in_explanation = False
                    continue
                
                if 'EXPLANATION:' in line:
                    in_formula = False
                    in_explanation = True
                    continue
                
                if in_formula and line:
                    formula = line
                    in_formula = False
                
                if in_explanation and line:
                    explanation += line + " "
            
            return formula, explanation.strip()
            
        except Exception as e:
            raise Exception(f"Error repairing formula: {str(e)}")


# Example usage
if __name__ == "__main__":
    helper = ClaudeAPIHelper()
    
    # Test AP extraction
    nl = "The alarm must sound whenever a failure is detected"
    aps, explanation = helper.extract_atomic_propositions(nl)
    print(f"APs: {aps}")
    print(f"Explanation: {explanation}\n")
    
    # Test formula generation
    formula, explanation = helper.generate_detailed_formula(nl, aps)
    print(f"Detailed Formula: {formula}")
    print(f"Explanation: {explanation}\n")
    
    python_ast, std_ltl, explanation = helper.generate_python_formula(nl, aps)
    print(f"Python AST: {python_ast}")
    print(f"Standard LTL: {std_ltl}")
    print(f"Explanation: {explanation}")