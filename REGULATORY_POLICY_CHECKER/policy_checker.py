"""
policy_checker.py - Python bridge to OCaml policy checker
Integrates with LLM for natural language query processing
"""

import json
import subprocess
import sys
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from config import get_llm_client

@dataclass
class Fact:
    """Represents a ground fact"""
    predicate: str
    arguments: List[str]


@dataclass
class QueryRequest:
    """Request structure for policy checking"""
    formula: str
    facts: List[Fact]
    regulation: Optional[str] = None
    
    def to_json(self) -> str:
        """Convert to JSON for OCaml"""
        data = {
            "formula": self.formula,
            "facts": {
                "facts": [
                    {
                        "predicate": f.predicate,
                        "arguments": f.arguments
                    } for f in self.facts
                ]
            }
        }
        if self.regulation:
            data["regulation"] = self.regulation
        return json.dumps(data)


@dataclass
class PolicyMatch:
    """Represents a matched policy"""
    policy_id: str
    regulation: str
    section: str
    description: str
    relevance_score: float
    matched_terms: List[str]


@dataclass
class Evaluation:
    """Evaluation result for a single policy"""
    policy_id: str
    regulation: str
    section: str
    description: str
    formula_text: str
    evaluation: bool 
    explanation: str


@dataclass
class QueryResponse:
    """Complete response from policy checker"""
    matched_policies: List[PolicyMatch]
    evaluations: List[Evaluation]
    overall_compliant: bool
    violations: List[str]
    error: Optional[str] = None


class PolicyChecker:
    """Interface to OCaml policy checking system"""
    
    def __init__(self, ocaml_executable: str = "./_build/default/src/main.exe"):
        """
        Initialize policy checker
        
        Args:
            ocaml_executable: Path to OCaml executable
                             Default: ./_build/default/src/main.exe (after dune build)
                             Alternative: ./policy_checker (if you created symlink)
        """
        self.executable = Path(ocaml_executable)
        if not self.executable.exists():
            # Try alternative paths
            alternatives = [
                "./_build/default/src/main.exe",
                "./policy_checker",
                "./main.exe",
                "../_build/default/src/main.exe"
            ]
            found = False
            for alt in alternatives:
                alt_path = Path(alt)
                if alt_path.exists():
                    self.executable = alt_path
                    found = True
                    break
            
            if not found:
                raise FileNotFoundError(
                    f"OCaml executable not found at: {ocaml_executable}\n"
                    f"Tried alternatives: {alternatives}\n"
                    f"Did you run 'dune build'?"
                )
    
    def check_policy(self, request: QueryRequest, timeout: int = 30, verbose: bool = False) -> QueryResponse:
        """
        Send a query to the OCaml policy checker
        
        Args:
            request: QueryRequest with formula and facts
            timeout: Maximum execution time in seconds
            verbose: Show OCaml pipeline details
            
        Returns:
            QueryResponse with evaluation results
        """
        try:
            # Debug: Print what we're sending
            json_input = request.to_json()
            
            if verbose or os.getenv('DEBUG_POLICY_CHECKER'):
                print("\n" + "="*60)
                print("🔧 OCaml Pipeline Input")
                print("="*60)
                print(f"📤 Sending to OCaml executable: {self.executable}")
                print(f"📋 Formula (first 200 chars):\n{request.formula[:200]}...")
                print(f"📊 Facts: {len(request.facts)} facts")
                if request.facts:
                    print(f"   Sample: {request.facts[0]}")
                print(f"📜 Regulation Filter: {request.regulation or 'None'}")
                print("="*60 + "\n")
            
            # Run OCaml process
            result = subprocess.run(
                [str(self.executable), "--json"],
                input=json_input,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Debug: Print what we received
            if verbose or os.getenv('DEBUG_POLICY_CHECKER'):
                print("\n" + "="*60)
                print("🔍 OCaml Pipeline Output")
                print("="*60)
                print(f"⚙️  Return code: {result.returncode}")
                if result.returncode == 0:
                    print("✅ OCaml execution successful")
                else:
                    print(f"❌ OCaml execution failed (code {result.returncode})")
                
                if result.stdout:
                    print(f"\n📤 OCaml Response (first 500 chars):")
                    print(result.stdout[:500])
                    if len(result.stdout) > 500:
                        print("...")
                
                if result.stderr:
                    print(f"\n⚠️  OCaml Stderr:")
                    print(result.stderr)
                print("="*60 + "\n")
            
            # Parse response
            if result.returncode != 0:
                return QueryResponse(
                    matched_policies=[],
                    evaluations=[],
                    overall_compliant=False,
                    violations=[],
                    error=f"OCaml process error (code {result.returncode}):\nStdout: {result.stdout}\nStderr: {result.stderr}"
                )
            
            response_data = json.loads(result.stdout)
            
            # Check for errors in response
            if "error" in response_data:
                return QueryResponse(
                    matched_policies=[],
                    evaluations=[],
                    overall_compliant=False,
                    violations=[],
                    error=response_data["error"]
                )
            
            # Parse successful response
            parsed_response = self._parse_response(response_data)
            
            if verbose or os.getenv('DEBUG_POLICY_CHECKER'):
                print("\n" + "="*60)
                print("📊 OCaml Results Summary")
                print("="*60)
                print(f"✓ Matched Policies: {len(parsed_response.matched_policies)}")
                print(f"✓ Evaluations: {len(parsed_response.evaluations)}")
                print(f"✓ Overall Compliant: {parsed_response.overall_compliant}")
                print(f"✓ Violations: {len(parsed_response.violations)}")
                
                if parsed_response.matched_policies:
                    print(f"\n📋 Matched Policies:")
                    for match in parsed_response.matched_policies[:3]:
                        print(f"   - {match.policy_id}: {match.description[:60]}...")
                
                if parsed_response.evaluations:
                    print(f"\n🔍 Evaluations:")
                    for eval in parsed_response.evaluations[:3]:
                        status = "✓" if eval.evaluation else "✗"
                        print(f"   {status} {eval.policy_id}")
                
                print("="*60 + "\n")
            
            return parsed_response
            
            # Parse successful response
            return self._parse_response(response_data)
            
        except subprocess.TimeoutExpired:
            return QueryResponse(
                matched_policies=[],
                evaluations=[],
                overall_compliant=False,
                violations=[],
                error=f"Query timeout after {timeout} seconds"
            )
        except json.JSONDecodeError as e:
            return QueryResponse(
                matched_policies=[],
                evaluations=[],
                overall_compliant=False,
                violations=[],
                error=f"Invalid JSON response: {e}"
            )
        except Exception as e:
            return QueryResponse(
                matched_policies=[],
                evaluations=[],
                overall_compliant=False,
                violations=[],
                error=f"Unexpected error: {str(e)}"
            )
    
    def _parse_response(self, data: Dict[str, Any]) -> QueryResponse:
        """Parse JSON response from OCaml"""
        matched_policies = [
            PolicyMatch(
                policy_id=p["policy_id"],
                regulation=p["regulation"],
                section=p["section"],
                description=p["description"],
                relevance_score=p["relevance_score"],
                matched_terms=p["matched_terms"]
            ) for p in data.get("matched_policies", [])
        ]
        
        evaluations = [
            Evaluation(
                policy_id=e["policy_id"],
                regulation=e["regulation"],
                section=e["section"],
                description=e["description"],
                formula_text=e["formula_text"],
                evaluation=(e["evaluation"]["result"] == "true"),
                explanation=e["explanation"]
            ) for e in data.get("evaluations", [])
        ]
        
        return QueryResponse(
            matched_policies=matched_policies,
            evaluations=evaluations,
            overall_compliant=data.get("overall_compliant", False),
            violations=data.get("violations", [])
        )


class LLMIntegration:
    """
    Integration layer for LLM-based query processing
    LLM1: Natural Language → Formula + Facts
    LLM2: Results → Natural Language Explanation
    """
    
    # Define available predicates for LLM guidance
    AVAILABLE_PREDICATES = {
        # HIPAA/Healthcare
        "inrole": "inrole(person, role) - person has role (e.g., physician, patient)",
        "treats": "treats(doctor, patient) - doctor treats patient",
        "hasConsent": "hasConsent(patient, provider) - patient consented to provider",
        "familyMember": "familyMember(person1, person2) - person1 is family of person2",
        "involvedInCare": "involvedInCare(person, patient) - person involved in patient's care",
        "incapacitated": "incapacitated(patient) - patient is incapacitated",
        "disclose": "disclose(from, to, data) - disclosure of data from person to person",
        "canAccess": "canAccess(person, resource) - person can access resource",
        "authorizedAccess": "authorizedAccess(person, resource) - person authorized to access",
        
        # Access Control
        "hasRole": "hasRole(user, role) - user has role",
        "active": "active(user) - user account is active",
        "suspended": "suspended(user) - user account is suspended",
        "canModify": "canModify(user, resource) - user can modify resource",
        "canView": "canView(user, resource) - user can view resource",
        
        # General
        "Person": "Person(entity) - entity is a person",
        "Doctor": "Doctor(entity) - entity is a doctor",
        "trained": "trained(person) - person is trained",
        "approved": "approved(entity) - entity is approved",
        "verified": "verified(entity) - entity is verified",
    }
    
    EXAMPLE_FORMULAS = """
EXAMPLE 1:
Question: "Can a doctor access a patient's record if they have consent?"
Formula:
policy starts
forall doctor, patient, record.
  (inrole(doctor, @physician) and treats(doctor, patient) and hasConsent(patient, doctor))
  implies canAccess(doctor, record)
policy ends

EXAMPLE 2:
Question: "Can family members access medical records?"
Formula:
policy starts
forall family, patient, record.
  (familyMember(family, patient) and involvedInCare(family, patient))
  implies (hasConsent(patient, family) or incapacitated(patient))
policy ends

EXAMPLE 3:
Question: "Can admin users modify resources?"
Formula:
policy starts
forall user, resource.
  (hasRole(user, @admin) and active(user))
  implies canModify(user, resource)
policy ends
"""
    
    def __init__(self, policy_checker: PolicyChecker):
        self.checker = policy_checker
        self.client = None
        self.provider = None
        try:
            self.client, self.provider = get_llm_client()
        except:
            pass  # LLM optional for direct formula use
    
    def process_natural_language_query(
        self, 
        question: str, 
        context_facts: Optional[List[Fact]] = None
    ) -> QueryResponse:
        """
        Full pipeline: Natural Language → Formula → Evaluation
        """
        if not self.client:
            return QueryResponse(
                matched_policies=[],
                evaluations=[],
                overall_compliant=False,
                violations=[],
                error="LLM not configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY"
            )
        
        # Step 1: Convert question to formula and extract facts
        formula, inferred_facts = self._llm_to_formula(question)
        
        # Step 2: Combine facts
        all_facts = (context_facts or []) + inferred_facts
        
        # Step 3: Create and check policy
        request = QueryRequest(
            formula=formula,
            facts=all_facts,
            regulation=self._detect_regulation(question)
        )
        
        response = self.checker.check_policy(request)
        
        # If error, try to give helpful feedback
        if response.error and "Unknown predicate" in response.error:
            unknown_pred = self._extract_unknown_predicate(response.error)
            if unknown_pred:
                response.error += f"\n\nSuggestion: Use one of these predicates instead: {', '.join(list(self.AVAILABLE_PREDICATES.keys())[:5])}"
        
        return response
    
    def _extract_unknown_predicate(self, error_msg: str) -> Optional[str]:
        """Extract the unknown predicate name from error message"""
        import re
        match = re.search(r'Unknown predicate: (\w+)', error_msg)
        return match.group(1) if match else None
    
    def _llm_to_formula(self, question: str) -> tuple[str, List[Fact]]:
        """
        Use LLM1 to convert natural language to logical formula
        Returns: (formula_string, extracted_facts)
        """
        print(f"🧠 [{self.provider}] Converting question to logic...")
        
        # Build system prompt with available predicates
        predicates_list = "\n".join([f"- {name}: {desc}" for name, desc in list(self.AVAILABLE_PREDICATES.items())[:15]])
        
        system_prompt = f"""You are a Formal Logic Translator for policy compliance checking.

AVAILABLE PREDICATES:
{predicates_list}

CRITICAL RULES:
1. ONLY use predicates from the list above
2. Constants must be prefixed with @ (e.g., @physician, @admin, @doctor)
3. Variables use no prefix (e.g., doctor, patient, user)
4. Output ONLY the policy block, no explanations

FORMAT:
policy starts
forall <variables>. <conditions> implies <conclusion>
policy ends

{self.EXAMPLE_FORMULAS}

IMPORTANT: 
- Use "familyMember" NOT "isFamilyMember"
- Use "inrole(person, @physician)" for roles
- Use "@" prefix for all role names like @physician, @patient, @admin
"""
        
        try:
            if self.provider == "openai":
                completion = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Convert to formal logic: {question}"}
                    ],
                    temperature=0.3  # Lower temperature for more consistent output
                )
                formula_response = completion.choices[0].message.content.strip()
            
            else:  # Claude
                message = self.client.messages.create(
                    model="claude-3-5-sonnet-latest",
                    max_tokens=500,
                    temperature=0.3,
                    messages=[
                        {
                            "role": "user",
                            "content": f"{system_prompt}\n\nConvert to formal logic: {question}"
                        }
                    ]
                )
                formula_response = message.content[0].text.strip()
            
            print(f"📝 LLM Formula Output:\n{formula_response}\n")
            
            # Extract facts from the question using LLM
            facts = self._extract_facts(question)
            print(f"📊 Extracted Facts: {len(facts)} facts\n")
            
            return formula_response, facts
            
        except Exception as e:
            print(f"⚠️  LLM Error: {e}")
            # Fallback to a safe default
            return "policy starts\nTrue\npolicy ends", []
    
    def _extract_facts(self, question: str) -> List[Fact]:
        """
        Extract facts from natural language question using LLM
        """
        extraction_prompt = f"""Extract facts from this question for policy checking.

Question: {question}

Output ONLY a JSON array of facts in this format:
[
  {{"predicate": "familyMember", "arguments": ["grandma", "patient"]}},
  {{"predicate": "involvedInCare", "arguments": ["grandma", "patient"]}}
]

Available predicates: {', '.join(list(self.AVAILABLE_PREDICATES.keys())[:10])}

Rules:
- Use snake_case for entity names (e.g., "grandma" not "Grandma")
- Extract implied relationships (e.g., "my grandma" implies familyMember)
- Keep it minimal - only essential facts

Output JSON array only, no explanation:"""
        
        try:
            if self.provider == "openai":
                completion = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a fact extractor. Output only valid JSON."},
                        {"role": "user", "content": extraction_prompt}
                    ],
                    temperature=0.2
                )
                facts_json = completion.choices[0].message.content.strip()
            else:  # Claude
                message = self.client.messages.create(
                    model="claude-3-5-sonnet-latest",
                    max_tokens=300,
                    messages=[{"role": "user", "content": extraction_prompt}]
                )
                facts_json = message.content[0].text.strip()
            
            # Clean up JSON (remove markdown fences if present)
            facts_json = facts_json.replace("```json", "").replace("```", "").strip()
            
            # Parse JSON
            facts_data = json.loads(facts_json)
            facts = [Fact(f["predicate"], f["arguments"]) for f in facts_data]
            
            return facts
            
        except Exception as e:
            print(f"⚠️  Fact extraction failed: {e}")
            return []
    
    def _detect_regulation(self, question: str) -> Optional[str]:
        """Detect which regulation context from question"""
        q = question.lower()
        if any(term in q for term in ["hipaa", "health", "medical", "phi", "doctor", "patient", "hospital"]):
            return "HIPAA"
        elif any(term in q for term in ["gdpr", "privacy", "personal data", "eu"]):
            return "GDPR"
        elif any(term in q for term in ["sox", "financial", "audit", "accounting"]):
            return "SOX"
        return None
    
    def format_user_response(self, response: QueryResponse) -> str:
        """
        Format response for LLM2 to present to user
        LLM2 takes structured data and generates natural explanation
        """
        if response.error:
            return self._format_error_with_llm(response.error)
        
        # Use LLM2 to generate natural language explanation
        if self.client:
            return self._llm2_explain(response)
        else:
            # Fallback to template-based formatting
            return self._format_basic(response)
    
    def _llm2_explain(self, response: QueryResponse) -> str:
        """Use LLM2 to generate natural language explanation"""
        
        # Prepare structured data for LLM
        evaluation_summary = "\n".join([
            f"- {e.regulation} {e.section}: {'✓ Satisfied' if e.evaluation else '✗ Violated'}"
            f"\n  {e.description}\n  {e.explanation}"
            for e in response.evaluations
        ])
        
        prompt = f"""Explain these policy compliance results in clear, user-friendly language.

COMPLIANCE STATUS: {"✅ COMPLIANT" if response.overall_compliant else "❌ NON-COMPLIANT"}
VIOLATIONS: {len(response.violations)}

POLICY EVALUATIONS:
{evaluation_summary}

VIOLATED POLICIES:
{chr(10).join([f'- {v}' for v in response.violations]) if response.violations else 'None'}

Provide a clear explanation that:
1. Starts with a direct yes/no answer
2. Explains which regulations apply
3. States the key requirements
4. Mentions any violations clearly
5. Is concise (2-3 sentences)

DO NOT use technical jargon. Speak naturally."""
        
        try:
            if self.provider == "openai":
                completion = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful compliance advisor. Explain policy results clearly."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                return completion.choices[0].message.content.strip()
            
            else:  # Claude
                message = self.client.messages.create(
                    model="claude-3-5-sonnet-latest",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )
                return message.content[0].text.strip()
                
        except Exception as e:
            print(f"⚠️  LLM2 explanation failed: {e}")
            return self._format_basic(response)
    
    def _format_error_with_llm(self, error: str) -> str:
        """Use LLM to make error messages user-friendly"""
        if not self.client:
            return f"❌ Error: {error}"
        
        prompt = f"""The policy checker encountered this error:

{error}

Explain this to a non-technical user in simple terms. Suggest what might be wrong and how to fix it. Be brief (1-2 sentences)."""
        
        try:
            if self.provider == "openai":
                completion = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant explaining errors simply."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5
                )
                return "❌ " + completion.choices[0].message.content.strip()
            else:
                message = self.client.messages.create(
                    model="claude-3-5-sonnet-latest",
                    max_tokens=200,
                    messages=[{"role": "user", "content": prompt}]
                )
                return "❌ " + message.content[0].text.strip()
        except:
            return f"❌ Error: {error}"
    
    def _format_basic(self, response: QueryResponse) -> str:
        """Fallback formatting without LLM"""
        lines = []
        
        if response.overall_compliant:
            lines.append("✅ COMPLIANT: All relevant policies are satisfied.")
        else:
            lines.append(f"❌ NON-COMPLIANT: {len(response.violations)} policy violation(s) detected.")
        
        lines.append("\nPolicy Evaluations:")
        for e in response.evaluations:
            status = "✓" if e.evaluation else "✗"
            lines.append(f"{status} {e.regulation} {e.section}")
            lines.append(f"   {e.description}")
            lines.append(f"   {e.explanation}")
        
        if response.violations:
            lines.append("\nViolated Policies:")
            for v in response.violations:
                lines.append(f"  - {v}")
        
        return "\n".join(lines)
    
    def process_natural_language_query(
        self, 
        question: str, 
        context_facts: Optional[List[Fact]] = None
    ) -> QueryResponse:
        """
        Full pipeline: Natural Language → Formula → Evaluation
        
        Args:
            question: User's natural language question
            context_facts: Optional known facts about the scenario
            
        Returns:
            QueryResponse with evaluation results
        """
        # Step 1: LLM1 converts question to formula and extracts facts
        formula, inferred_facts = self._llm_to_formula(question)
        
        # Step 2: Combine context facts with inferred facts
        all_facts = (context_facts or []) + inferred_facts
        
        # Step 3: Create query request
        request = QueryRequest(
            formula=formula,
            facts=all_facts,
            regulation=self._detect_regulation(question)
        )
        
        # Step 4: Check policy
        response = self.checker.check_policy(request)
        
        return response
    
    def _llm_to_formula(self, question: str) -> tuple[str, List[Fact]]:
        """
        Use LLM1 to convert natural language to logical formula
        
        This is a PLACEHOLDER - implement with your actual LLM
        
        Example transformations:
        - "Can my grandma receive my x-ray scan?" →
          Formula: "exists physician. (treats(physician, grandma) and hasConsent(grandma, physician))"
          Facts: [Fact("familyMember", ["grandma", "user"])]
        """
        # TODO: Implement actual LLM call
        # For now, return a stub
        
        # Simple keyword-based inference (replace with LLM)
        if "x-ray" in question.lower() and "grandma" in question.lower():
            formula = """
            policy starts
            forall provider, patient, family, phi.
              (disclose(provider, family, phi) and 
               familyMember(family, patient) and
               involvedInCare(family, patient))
              implies
              (hasConsent(patient, family) or incapacitated(patient))
            policy ends
            """
            facts = [
                Fact("familyMember", ["grandma", "patient"]),
                Fact("involvedInCare", ["grandma", "patient"]),
            ]
            return formula.strip(), facts
        
        # Default fallback
        return "policy starts\nTrue\npolicy ends", []
    
    def _detect_regulation(self, question: str) -> Optional[str]:
        """Detect which regulation context from question"""
        question_lower = question.lower()
        if any(term in question_lower for term in ["hipaa", "health", "medical", "phi"]):
            return "HIPAA"
        elif any(term in question_lower for term in ["gdpr", "privacy", "personal data"]):
            return "GDPR"
        elif any(term in question_lower for term in ["sox", "financial", "audit"]):
            return "SOX"
        return None
    
    def format_user_response(self, response: QueryResponse) -> str:
        """
        Format response for LLM2 to present to user
        
        LLM2 will take this structured data and generate a natural language
        explanation with reasoning
        """
        if response.error:
            return f"Error processing query: {response.error}"
        
        output = []
        
        # Overall verdict
        if response.overall_compliant:
            output.append("✅ COMPLIANT: The scenario satisfies all relevant policies.\n")
        else:
            output.append(f"❌ VIOLATIONS FOUND: {len(response.violations)} policy violations detected.\n")
        
        # Detail each evaluation
        output.append("Policy Evaluations:")
        for eval in response.evaluations:
            status = "✅" if eval.evaluation else "❌"
            output.append(f"\n{status} {eval.regulation} {eval.section}")
            output.append(f"   Description: {eval.description}")
            output.append(f"   Explanation: {eval.explanation}")
        
        # List violations
        if response.violations:
            output.append("\nViolated Policies:")
            for v in response.violations:
                output.append(f"  - {v}")
        
        return "\n".join(output)


# ============================================
# COMMAND-LINE INTERFACE
# ============================================

def main():
    """CLI for testing the policy checker"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Policy Compliance Checker")
    parser.add_argument("--executable", default="./_build/default/src/main.exe", 
                       help="Path to OCaml policy checker executable")
    parser.add_argument("--formula-file", help="File containing policy formula")
    parser.add_argument("--facts-file", help="JSON file containing facts")
    parser.add_argument("--query", help="Natural language query (requires LLM)")
    parser.add_argument("--regulation", choices=["HIPAA", "GDPR", "SOX"],
                       help="Filter by regulation")
    
    args = parser.parse_args()
    
    # Initialize checker
    checker = PolicyChecker(args.executable)
    
    if args.query:
        # Natural language query (requires LLM integration)
        llm = LLMIntegration(checker)
        
        # Load context facts if provided
        facts = []
        if args.facts_file:
            with open(args.facts_file) as f:
                facts_data = json.load(f)
                # Handle both formats: {"facts": [...]} or direct [...]
                if isinstance(facts_data, dict):
                    if "facts" in facts_data:
                        facts_list = facts_data["facts"]
                    else:
                        facts_list = []
                else:
                    facts_list = facts_data
                
                facts = [Fact(f["predicate"], f["arguments"]) 
                        for f in facts_list if isinstance(f, dict)]
        
        response = llm.process_natural_language_query(args.query, facts)
        print(llm.format_user_response(response))
        
    elif args.formula_file:
        # Direct formula evaluation
        with open(args.formula_file) as f:
            formula = f.read()
        
        facts = []
        if args.facts_file:
            with open(args.facts_file) as f:
                facts_data = json.load(f)
                
                # Handle multiple JSON formats
                if isinstance(facts_data, dict):
                    # Format 1: {"facts": {"facts": [...]}} (OCaml query format)
                    if "facts" in facts_data and isinstance(facts_data["facts"], dict):
                        facts_list = facts_data["facts"].get("facts", [])
                    # Format 2: {"facts": [...]} (simple facts list)
                    elif "facts" in facts_data and isinstance(facts_data["facts"], list):
                        facts_list = facts_data["facts"]
                    # Format 3: Direct list in dict (shouldn't happen but handle it)
                    else:
                        facts_list = []
                # Format 4: Direct list
                elif isinstance(facts_data, list):
                    facts_list = facts_data
                else:
                    facts_list = []
                
                facts = [Fact(f["predicate"], f["arguments"]) 
                        for f in facts_list if isinstance(f, dict)]
        
        request = QueryRequest(formula, facts, args.regulation)
        response = checker.check_policy(request)
        
        if response.error:
            print(f"Error: {response.error}", file=sys.stderr)
            sys.exit(1)
        
        # Pretty print results
        print(f"Overall Compliant: {response.overall_compliant}")
        print(f"\nMatched Policies: {len(response.matched_policies)}")
        for match in response.matched_policies:
            print(f"  - {match.policy_id}: {match.description}")
        
        print(f"\nEvaluations:")
        for eval in response.evaluations:
            status = "✓" if eval.evaluation else "✗"
            print(f"  {status} {eval.policy_id}: {eval.explanation}")
        
        if response.violations:
            print(f"\nViolations:")
            for v in response.violations:
                print(f"  - {v}")
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()


# ============================================
# EXAMPLE USAGE
# ============================================

"""
Example 1: Direct formula checking
-----------------------------------
python policy_checker.py \\
    --formula-file query.txt \\
    --facts-file facts.json \\
    --regulation HIPAA

Example 2: Natural language query
----------------------------------
python policy_checker.py \\
    --query "Can my grandma receive my x-ray scan?" \\
    --facts-file context.json

Example 3: Programmatic usage
------------------------------
from policy_checker import PolicyChecker, QueryRequest, Fact

checker = PolicyChecker("./policy_checker")

request = QueryRequest(
    formula=\"\"\"
    policy starts
    forall p, d. 
      (inrole(p, physician) and treats(p, d))
      implies canAccess(p, d)
    policy ends
    \"\"\",
    facts=[
        Fact("inrole", ["dr_smith", "physician"]),
        Fact("treats", ["dr_smith", "patient_123"]),
    ],
    regulation="HIPAA"
)

response = checker.check_policy(request)
print(f"Compliant: {response.overall_compliant}")
"""
