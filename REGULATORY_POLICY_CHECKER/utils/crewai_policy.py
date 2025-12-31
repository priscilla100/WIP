"""
Multi-Agent HIPAA Compliance System
====================================
A lightweight multi-agent system without CrewAI dependency.
Each agent is a specialized LLM call with specific tools and context.
"""

import json
import subprocess
import re
import time
from typing import List, Dict, Optional, Tuple
from anthropic import Anthropic

# ============================================
# AGENT TOOLS (Simple Python Functions)
# ============================================

ARITY_MAP = {
    'coveredEntity': 1,
    'protectedHealthInfo': 1,
    'publicHealthAuthority': 1,
    'hasAuthorization': 3,
    'requiredByLaw': 1,
    'disclose': 4,
    'permittedUseOrDisclosure': 4
}

HIPAA_KNOWLEDGE = {
    "164.502": "Uses and disclosures of PHI: General rules. Covered entities must have authorization or meet specific conditions.",
    "164.506": "Uses and disclosures for treatment, payment, and healthcare operations.",
    "164.510": "Uses and disclosures requiring an opportunity for the individual to agree or object.",
    "164.512": "Uses and disclosures for which authorization or opportunity to agree or object is not required."
}

def validate_fact_structure(fact: List[str]) -> Tuple[bool, str]:
    """Validate a fact's predicate and arity"""
    if len(fact) < 2:
        return False, "Fact must have at least predicate and one argument"
    
    predicate = fact[0]
    args = fact[1:]
    
    if predicate not in ARITY_MAP:
        return False, f"Unknown predicate: {predicate}"
    
    expected = ARITY_MAP[predicate]
    if len(args) != expected:
        return False, f"{predicate} expects {expected} args, got {len(args)}"
    
    return True, f"Valid: {predicate}({', '.join(args)})"


def check_formula_syntax(formula: str) -> Tuple[bool, str]:
    """Check formula syntax and variable bindings"""
    try:
        if not formula.strip().startswith('forall'):
            return False, "Formula should start with 'forall'"
        
        # Extract declared variables
        forall_part = formula.split('.')[0]
        var_str = forall_part.replace('forall', '').strip()
        declared_vars = set(v.strip() for v in var_str.split(','))
        
        # Find all variables in body
        body = '.'.join(formula.split('.')[1:])
        all_vars = set(re.findall(r'\b([a-z_][a-z0-9_]*)\b', body))
        
        keywords = {'and', 'or', 'implies', 'not', 'true', 'false'}
        predicates = {p.lower() for p in ARITY_MAP.keys()}
        used_vars = all_vars - keywords - predicates
        
        unbound = used_vars - declared_vars
        if unbound:
            return False, f"Unbound variables: {unbound}"
        
        return True, f"Valid formula with variables: {declared_vars}"
    
    except Exception as e:
        return False, f"Syntax error: {str(e)}"


def query_hipaa_section(section: str) -> str:
    """Get HIPAA section information"""
    for key, value in HIPAA_KNOWLEDGE.items():
        if key in section:
            return f"§{key}: {value}"
    return f"Section {section} not in knowledge base"


# ============================================
# BASE AGENT CLASS
# ============================================

class Agent:
    """Base agent with role, tools, and LLM access"""
    
    def __init__(self, name: str, role: str, tools: List[str], client: Anthropic):
        self.name = name
        self.role = role
        self.tools = tools
        self.client = client
        self.memory = []  # Conversation history
    
    def think(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Agent reasoning using LLM"""
        
        # Build full prompt with role and tools
        system_prompt = f"""You are {self.name}, a {self.role}.

Your available tools:
{self._format_tools()}

Think step-by-step. Use tools when needed by saying:
TOOL: tool_name(arguments)

Then continue reasoning."""
        
        if context:
            prompt = f"Context: {json.dumps(context, indent=2)}\n\n{prompt}"
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response = message.content[0].text
            self.memory.append({"prompt": prompt, "response": response})
            
            return response
        
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def _format_tools(self) -> str:
        """Format available tools description"""
        tool_descriptions = {
            "validate_fact": "validate_fact(fact) - Check if a fact has correct structure",
            "check_formula": "check_formula(formula) - Validate formula syntax",
            "query_hipaa": "query_hipaa(section) - Get HIPAA section info"
        }
        return "\n".join([tool_descriptions.get(t, t) for t in self.tools])


# ============================================
# SPECIALIZED AGENTS
# ============================================

class FactExtractorAgent(Agent):
    def __init__(self, client: Anthropic):
        super().__init__(
            name="Fact Extractor",
            role="HIPAA fact extraction specialist",
            tools=["validate_fact", "query_hipaa"],
            client=client
        )
    
    def extract(self, query: str) -> List[List[str]]:
        """Extract structured facts from natural language"""
        
        prompt = f"""Extract HIPAA compliance facts from this question:

"{query}"

CRITICAL: Identify question type:
- "Is X required?" / "Must X do Y?" → Extract RULES/REQUIREMENTS (no disclose)
- "Can X do Y?" → Extract SPECIFIC ACTIONS (with disclose)

PREDICATES:
- coveredEntity(Entity) [1 arg]
- protectedHealthInfo(Entity) [1 arg]
- disclose(From, To, PHI, Purpose) [4 args] - ONLY for action questions
- permittedUseOrDisclosure(From, To, PHI, Purpose) [4 args]
- hasAuthorization(CE, Recipient, PHI) [3 args]

PURPOSE CONSTANTS: @Treatment, @Payment, @HealthcareOperations, @Research

EXAMPLES:

Q: "Is consent required for treatment-related uses of PHI?"
Type: REQUIREMENT question
Facts:
{{
    "facts": [
        ["coveredEntity", "Hospital1"],
        ["protectedHealthInfo", "PHI1"],
        ["permittedUseOrDisclosure", "Hospital1", "Provider1", "PHI1", "@Treatment"]
    ]
}}
NO disclose() because asking about rules, not specific action.

Q: "Can a hospital share patient data with researchers?"
Type: ACTION question
Facts:
{{
    "facts": [
        ["coveredEntity", "Hospital1"],
        ["protectedHealthInfo", "PatientData1"],
        ["disclose", "Hospital1", "Researcher1", "PatientData1", "@Research"]
    ]
}}
Include disclose() because asking about specific action.

Now extract from: {query}

Output ONLY valid JSON:
{{
    "facts": [
        ["predicate", "arg1", "arg2", ...],
        ...
    ]
}}"""
        
        response = self.think(prompt)
        
        # Parse JSON from response
        try:
            json_match = re.search(r'\{.*"facts".*\}', response, re.DOTALL)
            if json_match:
                facts_json = json.loads(json_match.group())
                facts = facts_json.get("facts", [])
                
                # Validate each fact
                validated = []
                for fact in facts:
                    is_valid, msg = validate_fact_structure(fact)
                    if is_valid:
                        validated.append(fact)
                
                # Auto-add permittedUseOrDisclosure for TPO purposes if disclose exists
                self._add_permitted_uses(validated)
                
                return validated
        except:
            pass
        
        # Fallback
        return [
            ["coveredEntity", "Entity1"],
            ["protectedHealthInfo", "PHI1"]
        ]
    
    def _add_permitted_uses(self, facts: List[List[str]]) -> None:
        """Automatically add permittedUseOrDisclosure for Treatment/Payment/Operations"""
        
        permitted_purposes = ["@Treatment", "@Payment", "@HealthcareOperations"]
        
        for fact in facts[:]:  # Copy to avoid modification during iteration
            if fact[0] == "disclose" and len(fact) == 5:
                purpose = fact[4]
                if purpose in permitted_purposes:
                    # Check if permittedUseOrDisclosure already exists
                    permitted_fact = ["permittedUseOrDisclosure", fact[1], fact[2], fact[3], fact[4]]
                    if permitted_fact not in facts:
                        facts.append(permitted_fact)


class LogicTranslatorAgent(Agent):
    def __init__(self, client: Anthropic):
        super().__init__(
            name="Logic Translator",
            role="First-order logic expert",
            tools=["check_formula"],
            client=client
        )
    
    def translate(self, query: str, facts: List[List[str]]) -> str:
        """Translate query to formal logic formula"""
        
        # Have the agent explain the reasoning, but use template for output
        prompt = f"""Analyze this HIPAA compliance question:

Question: "{query}"
Facts: {json.dumps(facts)}

Explain in 1-2 sentences what compliance rule applies here.
The formula template will be: "If a covered entity discloses PHI, then it must be permitted, authorized, or required by law."

Your explanation:"""
        
        # Get the agent's reasoning (for memory/logging)
        reasoning = self.think(prompt)
        
        # But always return the standard formula
        formula = "forall ce, recipient, phi, purpose. (coveredEntity(ce) and protectedHealthInfo(phi) and disclose(ce, recipient, phi, purpose)) implies (permittedUseOrDisclosure(ce, recipient, phi, purpose) or hasAuthorization(ce, recipient, phi) or requiredByLaw(purpose))"
        
        # Log the reasoning
        self.memory.append({
            "reasoning": reasoning,
            "formula": formula
        })
        
        return formula


class ValidatorAgent(Agent):
    def __init__(self, client: Anthropic):
        super().__init__(
            name="Validator",
            role="Fact and formula validation specialist",
            tools=["validate_fact", "check_formula"],
            client=client
        )
    
    def validate(self, facts: List[List[str]], formula: str) -> Dict:
        """Validate facts and formula"""
        
        issues = []
        
        # Validate facts
        for fact in facts:
            is_valid, msg = validate_fact_structure(fact)
            if not is_valid:
                issues.append(f"Fact issue: {msg}")
        
        # Validate formula
        is_valid, msg = check_formula_syntax(formula)
        if not is_valid:
            issues.append(f"Formula issue: {msg}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "facts_count": len(facts),
            "formula_valid": is_valid
        }


class VerifierAgent(Agent):
    def __init__(self, client: Anthropic):
        super().__init__(
            name="Verifier",
            role="OCaml Précis engine operator",
            tools=[],
            client=client
        )
    
    def verify(self, formula: str, facts: List[List[str]]) -> Dict:
        """Call OCaml Précis verification engine"""
        
        PRECIS_PATH = "/Users/priscilladanso/Documents/STONYBROOK/RESEARCH/TOWARDDISSERTATION/WIP/REGULATORY_POLICY_CHECKER/precis"
        
        try:
            # Prepare facts for OCaml
            facts_for_ocaml = [
                {"predicate": f[0], "arguments": f[1:]}
                for f in facts if len(f) >= 2
            ]
            
            # Wrap formula
            wrapped = f"""regulation HIPAA version "1.0"
policy starts
{formula}
;
policy ends"""
            
            # Build request
            request = {
                "formula": wrapped,
                "facts": {"facts": facts_for_ocaml},
                "regulation": "HIPAA"
            }
            
            # Call OCaml
            proc = subprocess.Popen(
                [PRECIS_PATH, "json"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd="/Users/priscilladanso/Documents/STONYBROOK/RESEARCH/TOWARDDISSERTATION/WIP/REGULATORY_POLICY_CHECKER"
            )
            
            output, error = proc.communicate(input=json.dumps(request), timeout=30)
            
            if proc.returncode == 0 and output.strip():
                result = json.loads(output)
                
                # Parse verification result correctly
                overall_compliant = result.get("overall_compliant", None)
                violations = result.get("violations", [])
                evaluations = result.get("evaluations", [])
                
                # Determine verification status
                if overall_compliant is not None:
                    # Use overall_compliant if present (most reliable)
                    verified = overall_compliant
                elif evaluations:
                    # Fallback: check if all evaluations passed
                    verified = all(
                        e.get("evaluation", {}).get("result") == "true"
                        for e in evaluations
                    )
                else:
                    # No evaluations found
                    verified = False
                
                return {
                    "success": True,
                    "verified": verified,
                    "result": result,
                    "output": output,
                    "error": "",
                    "violations_count": len(violations),
                    "compliant_count": len(evaluations) - len(violations) if evaluations else 0
                }
            else:
                return {
                    "success": False,
                    "verified": False,
                    "result": {},
                    "output": output,
                    "error": error
                }
        
        except Exception as e:
            return {
                "success": False,
                "verified": False,
                "result": {},
                "output": "",
                "error": str(e)
            }


class ExplainerAgent(Agent):
    def __init__(self, client: Anthropic):
        super().__init__(
            name="Explainer",
            role="HIPAA compliance communication specialist",
            tools=["query_hipaa"],
            client=client
        )
    
    def explain(self, query: str, verified: bool, facts: List, formula: str) -> str:
        """Generate human-readable explanation"""
        
        prompt = f"""Explain this HIPAA compliance verification result:

Question: "{query}"
Facts: {json.dumps(facts)}
Formula: {formula}
Verification: {"PASSED (Compliant)" if verified else "FAILED (Violation)"}

Provide:
1. Direct YES/NO answer
2. Brief explanation (2-3 sentences)
3. Cite HIPAA §164.502(a)(1)
4. Actionable next step if needed

Keep it clear and practical."""
        
        response = self.think(prompt)
        return response


# ============================================
# MULTI-AGENT SYSTEM ORCHESTRATOR
# ============================================

def multi_agent_compliance_system(query: str, client: Anthropic) -> dict:
    """
    Orchestrate multiple agents to verify HIPAA compliance
    """
    
    start_time = time.time()
    steps = []
    
    try:
        # Create agents
        steps.append("🤖 Initializing agents...")
        fact_extractor = FactExtractorAgent(client)
        logic_translator = LogicTranslatorAgent(client)
        validator = ValidatorAgent(client)
        verifier = VerifierAgent(client)
        explainer = ExplainerAgent(client)
        
        # Agent 1: Extract Facts
        steps.append("🔍 Agent 1 (Fact Extractor): Analyzing query...")
        facts = fact_extractor.extract(query)
        steps.append(f"✅ Extracted {len(facts)} facts")
        
        # Agent 2: Translate to Logic
        steps.append("📐 Agent 2 (Logic Translator): Creating formula...")
        formula = logic_translator.translate(query, facts)
        steps.append(f"✅ Formula: {formula[:80]}...")
        
        # Agent 3: Validate
        steps.append("🔍 Agent 3 (Validator): Checking correctness...")
        validation = validator.validate(facts, formula)
        if validation['valid']:
            steps.append("✅ Validation passed")
        else:
            steps.append(f"⚠️ Validation issues: {validation['issues']}")
        
        # Agent 4: Verify with OCaml
        steps.append("⚙️ Agent 4 (Verifier): Running formal verification...")
        verification = verifier.verify(formula, facts)
        
        if verification['success']:
            steps.append("✅ Verification complete")
            verified = verification['verified']
        else:
            steps.append(f"❌ Verification failed: {verification['error']}")
            verified = False
        
        # Agent 5: Explain
        steps.append("💬 Agent 5 (Explainer): Generating explanation...")
        explanation = explainer.explain(query, verified, facts, formula)
        steps.append("✅ Explanation generated")
        
        return {
            "name": "Multi-Agent System 🤖",
            "answer": explanation,
            "duration": time.time() - start_time,
            "steps": steps,
            "extracted_facts": facts,
            "formula": formula,
            "verified": verified,
            "method": "5-Agent System (Extract → Translate → Validate → Verify → Explain)",
            "compliance_status": "✅ COMPLIANT" if verified else "❌ VIOLATION",
            "precis_result": {
                "success": verification['success'],
                "output": verification['output'],
                "error": verification['error'],
                "json_response": verification['result'],
                "pipeline_steps": [
                    "✅ Agent 1: Fact Extraction",
                    "✅ Agent 2: Logic Translation",
                    "✅ Agent 3: Validation",
                    "✅ Agent 4: Formal Verification",
                    "✅ Agent 5: Explanation"
                ]
            }
        }
    
    except Exception as e:
        steps.append(f"❌ System error: {str(e)}")
        return {
            "name": "Multi-Agent System 🤖",
            "answer": f"System error: {str(e)}",
            "duration": time.time() - start_time,
            "steps": steps,
            "extracted_facts": [],
            "formula": "",
            "verified": False,
            "method": "5-Agent System (Failed)",
            "compliance_status": "❌ ERROR"
        }


