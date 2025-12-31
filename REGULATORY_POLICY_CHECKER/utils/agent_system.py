#!/usr/bin/env python3
"""
agent_system.py

Runnable agentic-style compliance verification pipeline:
Extract (LLM) -> Translate (LLM) -> Verify (OCaml Précis) -> Explain (LLM)

Requirements:
- Python 3.10+
- Anthropic SDK or compatible client interface (the code uses a minimal wrapper)
- OCaml precis binary available on PATH or provide PRECIS_PATH env var
- Set ANTHROPIC_API_KEY in environment
- To avoid CrewAI import-time complaints elsewhere, set OPENAI_API_KEY=dummy if needed

Usage:
    export ANTHROPIC_API_KEY="sk-...."
    export OPENAI_API_KEY="dummy"      # only if some library insists on it
    python agent_system.py
"""

import os
import re
import json
import time
import subprocess
from typing import List, Tuple, Dict, Any, Optional
from dotenv import load_dotenv
import os

load_dotenv()
# -----------------------
# Configuration / Globals
# -----------------------
PRECIS_PATH = os.environ.get("PRECIS_PATH", "precis")  # rely on PATH by default
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
# Some libraries import-time check OpenAI; set dummy if absent to avoid crashes.
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "dummy"

# ARITY map for validators
ARITY_MAP = {
    "coveredEntity": 1,
    "protectedHealthInfo": 1,
    "publicHealthAuthority": 1,
    "hasAuthorization": 3,
    "requiredByLaw": 1,
    "disclose": 4,
    "permittedUseOrDisclosure": 4,
}

# Simple minimal Anthropic client wrapper that matches how you earlier invoked it:
class AnthropicClientWrapper:
    def __init__(self, api_key: str):
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required")
        self.api_key = ANTHROPIC_API_KEY

        # Lazy import to avoid hard dependency in environments lacking the SDK:
        try:
            from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT  # type: ignore
            self.client = Anthropic(api_key=api_key)
            self.human_tok = HUMAN_PROMPT
            self.ai_tok = AI_PROMPT
            self._use_sdk = True
        except Exception:
            # Fallback: implement a simple HTTP-based fallback could be added, but for now raise clear error
            raise RuntimeError(
                "Could not import the official Anthropic SDK. Install `anthropic` package or provide a compatible client."
            )

    def create(self, model: str, messages: List[Dict[str, str]], max_tokens: int = 500) -> str:
        """
        messages: list of {'role': 'user'|'assistant', 'content': '...'}
        Returns concatenated assistant text.
        """
        # Build single prompt (Anthropic expects a single prompt string usually)
        # We will join messages into a single prompt with HUMAN/AI tokens
        prompt_parts = []
        for m in messages:
            if m.get("role", "user") == "user":
                prompt_parts.append(self.human_tok + "\n" + m["content"] + "\n")
            else:
                prompt_parts.append(self.ai_tok + "\n" + m["content"] + "\n")
        prompt_parts.append(self.ai_tok)  # indicate we expect an assistant response
        prompt = "".join(prompt_parts)

        # Use the SDK client to create a completion (chat-style)
        resp = self.client.completions.create(
            model=model,
            prompt=prompt,
            max_tokens_to_sample=max_tokens,
            stop_sequences=[self.human_tok],
        )
        # resp is expected to have 'completion' key or similar based on SDK version
        text = resp.completion if hasattr(resp, "completion") else getattr(resp, "text", None)
        if text is None:
            # Try alternative attribute names
            text = json.dumps(resp.__dict__)
        return text

# -----------------------
# User-provided validators
# (inlined exactly with minor adaptation)
# -----------------------
def validate_facts(extracted_facts: list) -> tuple:
    """Validate fact structure and return (valid_facts, warnings)"""

    validated_facts = []
    warnings = []

    for fact in extracted_facts:
        if not isinstance(fact, list) or len(fact) < 2:
            warnings.append(f"⚠️ Invalid fact structure: {fact}, skipping")
            continue

        pred = fact[0]
        args = fact[1:]

        # Check if predicate exists
        if pred not in ARITY_MAP:
            warnings.append(f"⚠️ Unknown predicate: {pred}, skipping")
            continue

        # Validate arity
        expected_arity = ARITY_MAP[pred]
        if len(args) != expected_arity:
            warnings.append(f"⚠️ {pred} expects {expected_arity} args, got {len(args)}, skipping")
            continue

        # Validate constants have @ prefix in purpose positions
        if pred in ['disclose', 'permittedUseOrDisclosure'] and len(args) == 4:
            purpose = args[3]
            if not purpose.startswith('@'):
                warnings.append(f"⚠️ Purpose '{purpose}' missing @, converting to @{purpose}")
                args[3] = f"@{purpose}"

        if pred == 'requiredByLaw' and len(args) == 1:
            purpose = args[0]
            if not purpose.startswith('@'):
                warnings.append(f"⚠️ Purpose '{purpose}' missing @, converting to @{purpose}")
                args[0] = f"@{purpose}"

        validated_facts.append([pred] + args)

    # Ensure minimum facts
    if not validated_facts:
        warnings.append("⚠️ No valid facts extracted, using minimal fallback")
        validated_facts = [
            ["coveredEntity", "Entity1"],
            ["protectedHealthInfo", "PHI1"]
        ]

    return validated_facts, warnings


def validate_and_fix_formula(formula: str) -> tuple:
    """Validate and fix formula, return (fixed_formula, warnings, unbound_vars)"""

    warnings = []

    # Fix: Remove purpose comparison - we don't use purposeIsPurpose
    if ' = @' in formula or '= @' in formula or 'purposeIsPurpose' in formula:
        warnings.append("⚠️ Formula contains purpose comparison, removing it...")
        # Remove "and purpose = @Treatment" or "and purposeIsPurpose(...)"
        formula = re.sub(r'\s+and\s+\w+\s*=\s*@\w+', '', formula)
        formula = re.sub(r'\s+and\s+purposeIsPurpose\([^)]+\)', '', formula)

    # Check for unbound variables
    declared_vars = set()
    if formula.startswith("forall"):
        try:
            forall_part = formula.split('.')[0]
            var_list = forall_part.replace("forall", "").strip()
            declared_vars = set(v.strip() for v in var_list.split(',') if v.strip())
        except:
            warnings.append("⚠️ Could not parse forall clause")

    # Find all variables in formula body
    all_vars_in_body = set(re.findall(r'\b([a-z_][a-z0-9_]*)\b', formula))

    # Remove keywords and predicates
    keywords = {'forall', 'exists', 'and', 'or', 'implies', 'not', 'iff', 'xor', 'true', 'false'}
    predicates = {p.lower() for p in ARITY_MAP.keys()}
    used_vars = all_vars_in_body - keywords - predicates

    # Check for unbound variables
    unbound = used_vars - declared_vars
    if unbound:
        warnings.append(f"⚠️ Unbound variables detected: {unbound}, will attempt to fix")

    return formula, warnings, list(unbound) if unbound else []

# -----------------------
# Prompts
# (close to the ones you provided)
# -----------------------
FACT_EXTRACTION_PROMPT_TEMPLATE = """You are a HIPAA compliance expert. Extract ALL relevant entities and facts from this question.

Question: {query}

CRITICAL: Extract facts that describe the ACTUAL SCENARIO, not hypothetical rules.

AVAILABLE PREDICATES (use EXACT arity):
1. Entity types (1 arg):
   - coveredEntity(Entity) - hospitals, clinics, providers
   - protectedHealthInfo(Entity) - medical records, x-rays, lab results
   - publicHealthAuthority(Entity) - CDC, health departments

2. Authorization (3 args):
   - hasAuthorization(CoveredEntity, Recipient, PHI)

3. Requirements (1 arg):
   - requiredByLaw(Purpose)

4. Actions (4 args):
   - disclose(From, To, PHI, Purpose) - ALWAYS 4 args!
   - permittedUseOrDisclosure(From, To, PHI, Purpose) - ALWAYS 4 args!

5. Purpose constants (use as CONSTANTS with @):
   - @Treatment, @Payment, @HealthcareOperations
   - @Research, @PublicHealth, @Emergency

CRITICAL RULES:
- disclose() MUST have exactly 4 arguments: (From, To, PHI, Purpose)
- permittedUseOrDisclosure() MUST have exactly 4 arguments: (From, To, PHI, Purpose)
- Purpose is ALWAYS the 4th argument
- Use @Purpose constants with @ prefix
- If disclosure is PERMITTED by HIPAA (like treatment), include permittedUseOrDisclosure fact
- If patient AUTHORIZED it, include hasAuthorization fact
- If REQUIRED by law (like public health), include requiredByLaw fact

Output ONLY valid JSON:
{{
    "entities": ["entity1", "entity2", ...],
    "facts": [
        ["predicate", "arg1", "arg2", ...],
        ...
    ]
}}
"""

TRANSLATE_PROMPT_TEMPLATE = """You are translating a compliance question into first-order logic.

Question: {query}
Extracted Facts: {validated_facts}

CRITICAL RULES:
1. Start with "forall" listing ALL variables used in formula
2. Use ONLY these predicates with EXACT arity:
   - coveredEntity(X) [1 arg]
   - protectedHealthInfo(X) [1 arg]
   - publicHealthAuthority(X) [1 arg]
   - hasAuthorization(X,Y,Z) [3 args]
   - requiredByLaw(X) [1 arg]
   - disclose(W,X,Y,Z) [4 args - From, To, PHI, Purpose]
   - permittedUseOrDisclosure(W,X,Y,Z) [4 args - From, To, PHI, Purpose]

3. DO NOT use purposeIsPurpose or any equality checks on purpose
4. Purpose is just a variable - don't filter by it in the formula
5. Use constants with @ prefix: @Treatment, @Research, @PublicHealth
6. ALL variables in formula MUST be in forall clause

USE THIS EXACT TEMPLATE FOR ALL QUERIES:
forall ce, recipient, phi, purpose.
  (coveredEntity(ce)
   and protectedHealthInfo(phi)
   and disclose(ce, recipient, phi, purpose))
  implies
  (permittedUseOrDisclosure(ce, recipient, phi, purpose)
   or hasAuthorization(ce, recipient, phi)
   or requiredByLaw(purpose))

Now translate: {query}

CRITICAL: 
- Use the EXACT template above
- DO NOT add "purpose = @Something" anywhere
- DO NOT use purposeIsPurpose
- The purpose checking happens in the FACTS, not the formula

Output ONLY the formula, no explanation:
"""

EXPLAIN_PROMPT_TEMPLATE = """Explain this compliance verification result to a non-technical user.

Question: {query}
Facts Extracted: {validated_facts}
Formula Checked: {formula}
Verification Result: {verification_result}

Provide:
1. Direct YES/NO answer to user's question
2. Brief explanation (2-3 sentences) of why
3. Cite specific HIPAA section: §164.502(a)(1)(i)
4. Actionable guidance if needed

Keep it simple and clear.
"""

# -----------------------
# Orchestrator / Agentic Style System (lightweight)
# -----------------------
class ComplianceAgentSystem:
    def __init__(self, anthropic_api_key: Optional[str] = None, precis_path: str = PRECIS_PATH):
        self.precis_path = precis_path
        if anthropic_api_key is None:
            anthropic_api_key = ANTHROPIC_API_KEY
        self.client = AnthropicClientWrapper(anthropic_api_key)
        self.model = "claude-sonnet-4-20250514"  # adjust if needed

    # Agent: Fact extraction
    def extract_facts(self, query: str, retries: int = 1) -> Tuple[List[Any], List[str]]:
        steps = []
        prompt = FACT_EXTRACTION_PROMPT_TEMPLATE.format(query=query)
        try:
            raw = self.client.create(model=self.model, messages=[{"role": "user", "content": prompt}], max_tokens=800)
            steps.append("LLM returned raw extraction.")
            # try find JSON in response
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if not json_match:
                # Sometimes model returns other text followed by JSON — try to be more flexible
                # Try to salvage by finding first '[' that likely starts facts block
                try:
                    # fallback: if the model returned a python dict repr, try eval-safe parsing
                    potential = raw[raw.find("{"):].strip()
                    parsed = json.loads(potential)
                except Exception:
                    raise ValueError(f"No JSON found in LLM response. Raw response head: {raw[:400]!r}")
            else:
                parsed = json.loads(json_match.group())
            entities = parsed.get("entities", [])
            facts = parsed.get("facts", [])
            validated, warnings = validate_facts(facts)
            steps.extend([f"Validated facts: {len(validated)}", *warnings])
            return validated, steps
        except Exception as e:
            steps.append(f"Fact extraction failed: {e}")
            # fallback minimal facts
            fallback = [
                ["coveredEntity", "Entity1"],
                ["protectedHealthInfo", "PHI1"]
            ]
            return fallback, steps

    # Agent: Translate to formula
    def translate_to_formula(self, query: str, validated_facts: List[list], retries: int = 1) -> Tuple[str, List[str]]:
        steps = []
        prompt = TRANSLATE_PROMPT_TEMPLATE.format(query=query, validated_facts=json.dumps(validated_facts))
        try:
            raw = self.client.create(model=self.model, messages=[{"role": "user", "content": prompt}], max_tokens=400)
            # strip backticks if present
            if "```" in raw:
                m = re.search(r'```.*?\n(.*?)\n```', raw, re.DOTALL)
                if m:
                    raw = m.group(1)
            # The model may return the formula as multi-line; keep first line that looks like 'forall'
            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            formula = None
            for ln in lines:
                if ln.lower().startswith("forall"):
                    formula = ln
                    break
            if formula is None:
                # fallback to entire raw
                formula = lines[0] if lines else raw
            fixed_formula, warnings, unbound = validate_and_fix_formula(formula)
            steps.extend(warnings)
            # If there are unbound variables, attempt a simple fix: add them to forall
            if unbound:
                steps.append(f"Fixing unbound vars: {unbound}")
                try:
                    # insert missing vars into forall clause
                    if fixed_formula.startswith("forall"):
                        parts = fixed_formula.split(".", 1)
                        forall_vars = parts[0].replace("forall", "").strip()
                        new_vars = ", ".join([v for v in forall_vars.split(",") if v.strip()] + unbound)
                        fixed_formula = "forall " + new_vars + "." + parts[1]
                    else:
                        # Prepend a forall clause
                        fixed_formula = "forall " + ", ".join(unbound) + ". " + fixed_formula
                    steps.append("Unbound vars fixed locally.")
                except Exception as e:
                    steps.append(f"Failed local fix for unbound vars: {e}")
            return fixed_formula, steps
        except Exception as e:
            steps.append(f"Formula translation failed: {e}")
            # fallback to canonical template
            fallback = "forall ce, recipient, phi, purpose. (coveredEntity(ce) and protectedHealthInfo(phi) and disclose(ce, recipient, phi, purpose)) implies (permittedUseOrDisclosure(ce, recipient, phi, purpose) or hasAuthorization(ce, recipient, phi) or requiredByLaw(purpose))"
            return fallback, steps

    # Tool: call Ocaml precis
    def call_precis(self, formula: str, validated_facts: List[list], timeout: int = 30) -> Tuple[Dict[str, Any], List[str]]:
        steps = []
        # Prepare facts list for Précis
        facts_for_ocaml = []
        for fact in validated_facts:
            if len(fact) >= 2:
                facts_for_ocaml.append({
                    "predicate": fact[0],
                    "arguments": fact[1:]
                })

        wrapped_formula = f"""regulation HIPAA version "1.0"
policy starts
{formula}
;
policy ends"""

        precis_request = {
            "formula": wrapped_formula,
            "facts": {"facts": facts_for_ocaml},
            "regulation": "HIPAA"
        }

        try:
            proc = subprocess.Popen(
                [self.precis_path, "json"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            req_text = json.dumps(precis_request)
            out, err = proc.communicate(input=req_text, timeout=timeout)
            if proc.returncode != 0:
                steps.append(f"Précis exited with code {proc.returncode}")
                return {"success": False, "output": out, "error": err or "non-zero exit"}, steps
            if not out.strip():
                steps.append("Précis produced no stdout")
                return {"success": False, "output": out, "error": err}, steps
            try:
                parsed = json.loads(out)
                # determine verification result heuristically
                verified = False
                if "evaluations" in parsed and parsed["evaluations"]:
                    eval0 = parsed["evaluations"][0].get("evaluation", {})
                    if isinstance(eval0, dict) and eval0.get("result") == "true":
                        verified = True
                parsed["_verified"] = verified
                steps.append("Précis completed and JSON parsed.")
                return {"success": True, "json": parsed}, steps
            except Exception as e:
                steps.append(f"Failed to parse Précis JSON: {e}")
                return {"success": False, "output": out, "error": f"JSON parse failed: {e}"}, steps
        except subprocess.TimeoutExpired:
            steps.append("Précis timed out")
            return {"success": False, "output": "", "error": "Timeout"}, steps
        except FileNotFoundError:
            steps.append(f"Précis binary not found at '{self.precis_path}'")
            return {"success": False, "output": "", "error": f"Précis not found: {self.precis_path}"}, steps
        except Exception as e:
            steps.append(f"Précis invocation error: {e}")
            return {"success": False, "output": "", "error": str(e)}, steps

    # Agent: explain to user
    def explain_result(self, query: str, validated_facts: List[list], formula: str, verified: bool) -> Tuple[str, List[str]]:
        steps = []
        verification_result = "PASSED (Compliant)" if verified else "FAILED (Violation)"
        prompt = EXPLAIN_PROMPT_TEMPLATE.format(
            query=query,
            validated_facts=json.dumps(validated_facts),
            formula=formula,
            verification_result=verification_result
        )
        try:
            raw = self.client.create(model=self.model, messages=[{"role": "user", "content": prompt}], max_tokens=400)
            steps.append("Explanation generated by LLM.")
            return raw.strip(), steps
        except Exception as e:
            steps.append(f"Failed to generate explanation: {e}")
            return f"Unable to generate explanation: {e}", steps

    # Full pipeline orchestration
    def run(self, query: str) -> Dict[str, Any]:
        start = time.time()
        all_steps = []
        # Step 1: Extract facts
        all_steps.append("🔍 Step 1: Fact extraction")
        validated_facts, s = self.extract_facts(query)
        all_steps.extend(s)

        # Step 2: Translate to formula
        all_steps.append("📐 Step 2: Translate to formula")
        formula, s = self.translate_to_formula(query, validated_facts)
        all_steps.extend(s)

        # Step 3: Call Précis
        all_steps.append("⚙️ Step 3: Run Précis verification")
        precis_res, s = self.call_precis(formula, validated_facts)
        all_steps.extend(s)
        verified = False
        precis_output_for_display = {}
        if precis_res.get("success"):
            parsed = precis_res.get("json", {})
            verified = parsed.get("_verified", False)
            precis_output_for_display = parsed
        else:
            # try to capture helpful fields
            precis_output_for_display = {
                "success": False,
                "error": precis_res.get("error"),
                "output_excerpt": precis_res.get("output", "")[:800]
            }

        # Step 4: Explain
        all_steps.append("💬 Step 4: Explanation")
        explanation, s = self.explain_result(query, validated_facts, formula, verified)
        all_steps.extend(s)

        duration = time.time() - start
        result = {
            "name": "AgenticCompliancePipeline",
            "answer": explanation,
            "duration": duration,
            "steps": all_steps,
            "extracted_facts": validated_facts,
            "formula": formula,
            "precis_result": precis_output_for_display,
            "verified": verified,
            "method": "LLM1 (Extract+Translate) → OCaml Précis → LLM2 (Explain)",
            "compliance_status": "✅ COMPLIANT" if verified else "❌ VIOLATION"
        }
        return result

# -----------------------
# If run as script, demo with an example query
# -----------------------
if __name__ == "__main__":
    # quick self-test (replace with real key and ensure precis binary available)
    if ANTHROPIC_API_KEY is None:
        print("Error: ANTHROPIC_API_KEY not set. Export it and retry.")
        raise SystemExit(1)

    system = ComplianceAgentSystem(anthropic_api_key=ANTHROPIC_API_KEY, precis_path=PRECIS_PATH)

    demo_query = "Can a hospital share a patient's x-ray with a specialist for treatment?"
    print("Running pipeline for demo query:")
    res = system.run(demo_query)

    print("\n=== RESULT SUMMARY ===")
    print(f"Duration: {res['duration']:.2f}s")
    print(f"Verified: {res['verified']}")
    print(f"Compliance status: {res['compliance_status']}")
    print("\nSteps:")
    for s in res["steps"]:
        print(" -", s)
    print("\nExtracted facts:")
    print(json.dumps(res["extracted_facts"], indent=2))
    print("\nFormula:")
    print(res["formula"])
    print("\nExplanation (truncated):")
    print(res["answer"][:800])
