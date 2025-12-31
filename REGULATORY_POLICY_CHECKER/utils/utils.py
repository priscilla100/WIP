
import streamlit as st
import subprocess
import json
import time
from anthropic import Anthropic
import os
from pathlib import Path
import re
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import ast
import PyPDF2
from io import BytesIO
import re
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
PRECIS_PATH = os.environ.get(
    "PRECIS_PATH",
    "/Users/priscilladanso/Documents/STONYBROOK/RESEARCH/TOWARDDISSERTATION/IMPLEMENTATION/policy_checker/precis"
)
load_dotenv()

EXPERIMENTS= {
    "baseline_no_context": {
        "exp_name": "Baseline",
        "description": "Direct LLM call with no external knowledge",
        "use_retrieval": False,
        "use_precis": False
    },
    "rag": {
        "exp_name": "RAG",
        "description": "Retrieve natural language policies from database and provide to LLM",
        "use_retrieval": True,
        "use_precis": False
    },
    "pipeline": {
        "exp_name": "Pipeline4Compliance ⭐",
        "description": "Complete pipeline: LLM1 (extract + translate) → OCaml Précis → LLM2 (explain)",
        "use_retrieval": False,
        "use_precis": True
    },
    "agentic": {
       "exp_name": "Agent4Compliance ⭐",
        "description": "Full Agent Reasoning, tool use, replanning using CrewAI",
        "use_retrieval": False,
        "use_precis": True 
    }
}

ARITY_MAP = {
    # Entity type predicates (1 argument)
    'coveredEntity': 1,
    'protectedHealthInfo': 1,
    'publicHealthAuthority': 1,
    
    # Action predicates (4 arguments)
    'disclose': 4,
    'permittedUseOrDisclosure': 4,
    
    # Authorization predicates (3 arguments)
    'hasAuthorization': 3,
    
    # Requirement predicates (1 argument)
    'requiredByLaw': 1,
    
    # Comparison predicates (2 arguments)
    'purposeIsPurpose': 2,
}
    
def load_policy_database(csv_path: str = "csv/hipaa_policies_all.csv") -> list:
    try:
        df = pd.read_csv(csv_path)

        policies = []
        for _, row in df.iterrows():

            text = str(row["natural_language"]).lower()

            # very simple keyword extraction (you can improve later)
            auto_keywords = [w.strip(".,;:()") for w in text.split() if len(w) > 4]

            policy = {
                "id": row['policy_id'],
                "section": row['section_number'],
                "title": row['category'],
                "text": row['natural_language'],
                "keywords": auto_keywords,  # <-- FIX
            }

            policies.append(policy)

        print(f"Loaded {len(policies)} policies from CSV.")
        return policies
    except FileNotFoundError:
        st.warning(f"CSV file not found: {csv_path}. Using fallback database.")
        return get_fallback_database()
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return get_fallback_database()

def get_fallback_database() -> list:
    """Fallback policy database if CSV not available"""
    return [
        {
            "id": "HIPAA-164.510b",
            "section": "§164.510(b)",
            "title": "Disclosure to Family Members",
            "text": "A covered entity may disclose protected health information to a family member, other relative, or close personal friend who is involved in the individual's care, with the individual's consent or if the individual is unable to agree.",
            "keywords": ["family", "relatives", "care", "disclosure", "consent", "incapacitated"]
        },
        {
            "id": "HIPAA-164.502a5",
            "section": "§164.502(a)(5)",
            "title": "Business Associate Agreements",
            "text": "A covered entity may disclose protected health information to a business associate if the entity obtains satisfactory assurance that the business associate will appropriately safeguard the information.",
            "keywords": ["business", "associate", "agreement", "contract", "disclosure", "safeguard"]
        },
        {
            "id": "HIPAA-164.506",
            "section": "§164.506",
            "title": "Uses and Disclosures for Treatment, Payment, Healthcare Operations",
            "text": "A covered entity may use or disclose protected health information for treatment, payment, or healthcare operations without individual authorization.",
            "keywords": ["treatment", "payment", "operations", "authorization", "use"]
        },
        {
            "id": "HIPAA-164.512b",
            "section": "§164.512(b)",
            "title": "Public Health Activities",
            "text": "A covered entity may disclose protected health information for public health activities without individual authorization.",
            "keywords": ["public health", "disclosure", "reporting", "disease", "surveillance"]
        },
        {
            "id": "HIPAA-164.530b",
            "section": "§164.530(b)",
            "title": "Privacy Officer Requirement",
            "text": "A covered entity must designate a privacy official who is responsible for the development and implementation of the policies and procedures.",
            "keywords": ["privacy", "officer", "official", "responsibility", "policies"]
        }
    ]

# Load the policy database
RAG_POLICY_DATABASE = load_policy_database()

def retrieve_relevant_policies(query: str, top_k: int = 3) -> list:
    """RAG retrieval from natural language policy database"""
    query_lower = query.lower()
    
    scored = []
    for policy in RAG_POLICY_DATABASE:
        # Score based on keyword matches
        score = sum(1 for kw in policy['keywords'] if kw in query_lower)
        # Boost if section/title mentioned
        if policy['section'].lower() in query_lower or policy['title'].lower() in query_lower:
            score += 5
        scored.append((score, policy))
    
    scored.sort(reverse=True, key=lambda x: x[0])
    return [p for s, p in scored[:top_k] if s > 0]

# ============================================
# PRÉCIS INTERFACE
# ============================================

def call_precis_json(formula: str, facts: list) -> dict:
    """
    Call OCaml Précis engine in JSON mode
    
    This is the bridge: Python → OCaml
    """
    
    # Prepare JSON input for OCaml
    request = {
        "formula": formula,
        "facts": {
            "facts": [[pred] + args for pred, *args in facts]
        },
        "regulation": "HIPAA"
    }
    
    try:
        # Call OCaml in JSON mode
        proc = subprocess.Popen(
            [PRECIS_PATH, "json"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(input=json.dumps(request), timeout=30)
        
        if proc.returncode == 0:
            return {
                "success": True,
                "output": stdout,
                "response": json.loads(stdout) if stdout.strip() else {}
            }
        else:
            return {
                "success": False,
                "error": stderr or "Unknown error"
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def analyze_compliance_answer(answer: str, question: str = "") -> dict:
    """
    Intelligently analyze an answer to determine compliance verdict
    Args:
        answer: The LLM's response
        question: The original question (helps with context)
    Returns: {'verdict': 'compliant'|'violation'|'conditional', 'confidence': float, 'reasoning': str}
    """
    
    answer_lower = answer.lower()
    question_lower = question.lower() if question else ""
    
    # Detect question patterns
    is_negative_question = any(word in question_lower for word in [
        'is consent required',
        'is authorization required',
        'must obtain consent',
        'need consent',
        'need authorization'
    ])
    
    is_permission_question = any(phrase in question_lower for phrase in [
        'can', 'may', 'allowed to', 'permitted to'
    ])
    
    is_requirement_question = any(phrase in question_lower for phrase in [
        'must', 'required to', 'shall', 'need to', 'have to'
    ]) and not is_negative_question
    
    # Extract YES/NO
    answer_lines = answer_lower.split('\n')
    first_line = answer_lines[0].strip() if answer_lines else answer_lower
    
    starts_with_yes = first_line.startswith('yes')
    starts_with_no = first_line.startswith('no')
    
    # Also check for yes/no in first few words
    first_words = ' '.join(first_line.split()[:5])
    has_yes = 'yes' in first_words or starts_with_yes
    has_no = 'no' in first_words or starts_with_no
    
    # Decision logic
    if is_negative_question:
        # "Is consent required?" - asking if something restrictive is needed
        if has_no:
            # NO consent required = treatment is ALLOWED = COMPLIANT
            return {
                'verdict': 'compliant',
                'confidence': 0.95,
                'reasoning': 'NO to negative question (consent NOT required) = compliant'
            }
        elif has_yes:
            # YES consent required = more restrictive = COMPLIANT (requirement exists)
            return {
                'verdict': 'compliant',
                'confidence': 0.9,
                'reasoning': 'YES to requirement question = requirement exists'
            }
    
    elif is_permission_question:
        # "Can hospitals share...?"
        if has_yes:
            # Check for conditions
            conditional_words = ['only if', 'provided that', 'must obtain', 'requires authorization']
            has_conditions = any(phrase in answer_lower for phrase in conditional_words)
            
            if has_conditions:
                return {
                    'verdict': 'conditional',
                    'confidence': 0.85,
                    'reasoning': 'YES with conditions to permission question'
                }
            else:
                return {
                    'verdict': 'compliant',
                    'confidence': 0.9,
                    'reasoning': 'YES to permission question = allowed'
                }
        elif has_no:
            return {
                'verdict': 'violation',
                'confidence': 0.9,
                'reasoning': 'NO to permission question = not allowed'
            }
    
    elif is_requirement_question:
        # "Must covered entities have X?"
        if has_yes:
            return {
                'verdict': 'compliant',
                'confidence': 0.9,
                'reasoning': 'YES to requirement = requirement exists'
            }
        elif has_no:
            return {
                'verdict': 'compliant',
                'confidence': 0.85,
                'reasoning': 'NO to requirement = no requirement (compliant by default)'
            }
    
    # Fallback: Look for explicit compliance language
    if any(word in answer_lower for word in ['compliant', 'permitted', 'allowed', 'authorized']):
        return {
            'verdict': 'compliant',
            'confidence': 0.7,
            'reasoning': 'Answer indicates compliance/permission'
        }
    
    if any(word in answer_lower for word in ['violation', 'prohibited', 'not permitted', 'unauthorized']):
        return {
            'verdict': 'violation',
            'confidence': 0.7,
            'reasoning': 'Answer indicates violation/prohibition'
        }
    
    # Unknown
    return {
        'verdict': 'unknown',
        'confidence': 0.3,
        'reasoning': 'Unable to determine clear verdict from answer'
    }


def experiment_baseline(query: str, client: Anthropic) -> dict:
    """
    Enhanced Baseline with verdict analysis
    """
    import time
    
    start = time.time()
    steps = ["📝 Direct LLM call without external knowledge"]
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"""You are a HIPAA compliance expert. Answer this question:

{query}

Provide a clear, direct answer with:
1. YES or NO at the start
2. Brief explanation
3. Key HIPAA requirements if applicable

Be concise but complete."""
            }]
        )
        
        answer = message.content[0].text
        steps.append("✅ LLM response generated")
        
        # Analyze the answer WITH the question for context
        analysis = analyze_compliance_answer(answer, query)
        steps.append(f"✅ Answer analyzed: {analysis['reasoning']}")
        
        # Determine compliance status
        if analysis['verdict'] == 'compliant':
            compliance_status = "✅ COMPLIANT (based on answer)"
            verified = True
        elif analysis['verdict'] == 'violation':
            compliance_status = "❌ VIOLATION (based on answer)"
            verified = False
        elif analysis['verdict'] == 'conditional':
            compliance_status = "⚠️ CONDITIONAL COMPLIANCE"
            verified = True  # Technically compliant if conditions are met
        else:
            compliance_status = "⚠️ UNKNOWN"
            verified = False
        
        return {
            "name": "Baseline",
            "answer": answer,
            "duration": time.time() - start,
            "steps": steps,
            "method": "Direct LLM (No external knowledge)",
            "compliance_status": compliance_status,
            "verified": verified,
            "analysis": analysis
        }
    
    except Exception as e:
        return {
            "name": "Baseline",
            "answer": f"Error: {str(e)}",
            "duration": time.time() - start,
            "steps": steps + [f"❌ Error: {str(e)}"],
            "method": "Direct LLM (Failed)",
            "compliance_status": "❌ ERROR",
            "verified": False
        }


def experiment_rag(query: str, client: Anthropic) -> dict:
    """
    Enhanced RAG with verdict analysis
    """
    import time
    
    start = time.time()
    steps = ["🔍 Retrieving HIPAA policies from database"]
    
    retrieved_policies = retrieve_relevant_policies(query, top_k=3)
    steps.append(f"Retrieved {len(retrieved_policies)} policies from RAG database")

    retrieved_count = len(retrieved_policies)
    steps.append(f"✅ Retrieved {retrieved_count} policies from database")
    steps.append(f"Retrieved {len(retrieved_policies)} policies from RAG database:")

    for p in retrieved_policies:
        steps.append(
            f"\n📌 {p['id']} — {p['title']}\n"
            f"Section: {p['section']}\n"
            f"Text: {p['text'][:200]}..."  # first 200 chars
        )

    try:
        if retrieved_count == 0:
            # No policies retrieved - answer based on general knowledge
            steps.append("⚠️ No relevant policies found, using general knowledge")
            
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"""No specific HIPAA policies were retrieved from the database for this question:

{query}

Provide a general answer based on your knowledge of HIPAA, but clearly note that specific policy citations are not available."""
                }]
            )
            
            answer = message.content[0].text
            analysis = analyze_compliance_answer(answer, query)
            
            # Since no policies were retrieved, mark as lower confidence
            if analysis['verdict'] == 'compliant':
                compliance_status = "⚠️ LIKELY COMPLIANT (no policy verification)"
                verified = False
            elif analysis['verdict'] == 'violation':
                compliance_status = "⚠️ LIKELY VIOLATION (no policy verification)"
                verified = False
            else:
                compliance_status = "⚠️ UNKNOWN (no policies retrieved)"
                verified = False
        
        else:
            # Policies retrieved - generate answer with citations
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"""Based on these HIPAA policies:

{retrieved_policies}

Answer this question: {query}

Cite specific policy sections."""
                }]
            )
            
            answer = message.content[0].text
            analysis = analyze_compliance_answer(answer, query)
            
            if analysis['verdict'] == 'compliant':
                compliance_status = "✅ COMPLIANT (with policy citations)"
                verified = True
            elif analysis['verdict'] == 'violation':
                compliance_status = "❌ VIOLATION (with policy citations)"
                verified = False
            else:
                compliance_status = "⚠️ INCONCLUSIVE"
                verified = False
        
        steps.append("✅ LLM response with policy context generated")
        
        return {
            "name": "RAG",
            "answer": answer,
            "duration": time.time() - start,
            "steps": steps,
            "method": "Retrieval + LLM",
            "compliance_status": compliance_status,
            "verified": verified,
            "retrieved_policies": retrieved_count,
            # "retrieved_policies": retrieved_policies,  # <--- add this
            "analysis": analysis
        }
    
    except Exception as e:
        return {
            "name": "RAG",
            "answer": f"Error: {str(e)}",
            "duration": time.time() - start,
            "steps": steps + [f"❌ Error: {str(e)}"],
            "method": "Retrieval + LLM (Failed)",
            "compliance_status": "❌ ERROR",
            "verified": False,
            "retrieved_policies": 0
        }


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
            declared_vars = set(v.strip() for v in var_list.split(','))
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


# ============================================
# MAIN EXPERIMENT FUNCTION
# ============================================

def experiment_agent4compliance(query: str, client: Anthropic) -> dict:
    """
    Complete pipeline with proper validation and error handling
    """
    start = time.time()
    steps = []
    
    # =====================================
    # STEP 1: LLM1 - Fact Extraction
    # =====================================
    steps.append("🔍 LLM1: Extracting facts from query...")
    
    extract_prompt = f"""You are a HIPAA compliance expert. Extract ALL relevant entities and facts from this question.

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

EXAMPLES:

Q: "Can a hospital share patient records with a specialist for treatment?"
Facts:
[
    ["coveredEntity", "Hospital1"],
    ["protectedHealthInfo", "MedicalRecord1"],
    ["disclose", "Hospital1", "Specialist1", "MedicalRecord1", "@Treatment"],
    ["permittedUseOrDisclosure", "Hospital1", "Specialist1", "MedicalRecord1", "@Treatment"]
]

Q: "Can a clinic share lab results with researchers if the patient authorized it?"
Facts:
[
    ["coveredEntity", "Clinic1"],
    ["protectedHealthInfo", "LabResult1"],
    ["disclose", "Clinic1", "Researcher1", "LabResult1", "@Research"],
    ["hasAuthorization", "Clinic1", "Researcher1", "LabResult1"]
]

Q: "Can a hospital report infectious disease to public health authorities?"
Facts:
[
    ["coveredEntity", "Hospital1"],
    ["protectedHealthInfo", "LabResult1"],
    ["publicHealthAuthority", "PublicHealthDept1"],
    ["disclose", "Hospital1", "PublicHealthDept1", "LabResult1", "@PublicHealth"],
    ["requiredByLaw", "@PublicHealth"]
]

Q: "Can a provider share x-rays with family without authorization?"
Facts:
[
    ["coveredEntity", "Provider1"],
    ["protectedHealthInfo", "XRay1"],
    ["disclose", "Provider1", "FamilyMember1", "XRay1", "@Research"]
]

Now extract from: {query}

Output ONLY valid JSON:
{{
    "entities": ["entity1", "entity2", ...],
    "facts": [
        ["predicate", "arg1", "arg2", ...],
        ...
    ]
}}
"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": extract_prompt}]
        )
        
        facts_text = message.content[0].text
        
        # Parse JSON
        json_match = re.search(r'\{.*\}', facts_text, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON found in LLM response")
        
        facts_json = json.loads(json_match.group())
        extracted_facts = facts_json.get("facts", [])
        
        # Validate facts
        validated_facts, fact_warnings = validate_facts(extracted_facts)
        steps.extend(fact_warnings)
        
        steps.append(f"✅ Extracted and validated {len(validated_facts)} facts")
        
    except Exception as e:
        steps.append(f"❌ Fact extraction failed: {e}")
        validated_facts = [
            ["coveredEntity", "Entity1"],
            ["protectedHealthInfo", "PHI1"]
        ]
    
    # =====================================
    # STEP 2: LLM1 - Formula Translation
    # =====================================
    steps.append("📐 LLM1: Translating to formal logic...")
    
    translate_prompt = f"""You are translating a compliance question into first-order logic.

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

EXAMPLES (ALL questions use the SAME formula):

Q: "Can hospital share data with researchers?"
Formula:
forall ce, recipient, phi, purpose. (coveredEntity(ce) and protectedHealthInfo(phi) and disclose(ce, recipient, phi, purpose)) implies (permittedUseOrDisclosure(ce, recipient, phi, purpose) or hasAuthorization(ce, recipient, phi) or requiredByLaw(purpose))

Q: "Can clinic refer patient to specialist for treatment?"
Formula:
forall ce, recipient, phi, purpose. (coveredEntity(ce) and protectedHealthInfo(phi) and disclose(ce, recipient, phi, purpose)) implies (permittedUseOrDisclosure(ce, recipient, phi, purpose) or hasAuthorization(ce, recipient, phi) or requiredByLaw(purpose))

Q: "Can hospital report to public health?"
Formula:
forall ce, recipient, phi, purpose. (coveredEntity(ce) and protectedHealthInfo(phi) and disclose(ce, recipient, phi, purpose)) implies (permittedUseOrDisclosure(ce, recipient, phi, purpose) or hasAuthorization(ce, recipient, phi) or requiredByLaw(purpose))

Now translate: {query}

CRITICAL: 
- Use the EXACT template above
- DO NOT add "purpose = @Something" anywhere
- DO NOT use purposeIsPurpose
- The purpose checking happens in the FACTS, not the formula

Output ONLY the formula, no explanation:"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": translate_prompt}]
        )
        
        formula = message.content[0].text.strip()
        
        # Clean up formula
        if "```" in formula:
            match = re.search(r'```.*?\n(.*?)\n```', formula, re.DOTALL)
            if match:
                formula = match.group(1).strip()
        
        formula = formula.split('\n')[0].strip()
        
        # Validate and fix formula
        fixed_formula, formula_warnings, unbound_vars = validate_and_fix_formula(formula)
        steps.extend(formula_warnings)
        
        # If unbound variables detected, ask LLM to fix
        if unbound_vars:
            steps.append(f"🔧 Fixing unbound variables: {unbound_vars}")
            
            fix_prompt = f"""This formula has unbound variables: {unbound_vars}

Formula: {fixed_formula}

Add ALL missing variables to the forall clause at the start.

RULE: Every variable used in the formula body MUST appear in the forall clause.

Example:
BAD:  forall x. ... someVar ...
GOOD: forall x, someVar. ... someVar ...

Output ONLY the corrected formula:"""
            
            fix_message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                messages=[{"role": "user", "content": fix_prompt}]
            )
            fixed_formula = fix_message.content[0].text.strip()
            steps.append("✅ Formula fixed")
        
        formula = fixed_formula
        steps.append(f"✅ Formula: {formula[:100]}...")
        
    except Exception as e:
        steps.append(f"❌ Formula translation failed: {e}")
        # Fallback to basic template
        formula = "forall ce, recipient, phi, purpose. (coveredEntity(ce) and protectedHealthInfo(phi) and disclose(ce, recipient, phi, purpose)) implies (permittedUseOrDisclosure(ce, recipient, phi, purpose) or hasAuthorization(ce, recipient, phi) or requiredByLaw(purpose))"
    
    # =====================================
    # STEP 3: Call OCaml Précis
    # =====================================
    steps.append("⚙️ Calling OCaml Précis engine...")
    
    verified = False
    precis_result = {
        "success": False,
        "output": "",
        "error": "Not executed",
        "pipeline_steps": []
    }
    
    # Prepare facts for OCaml
    facts_for_ocaml = []
    for fact in validated_facts:
        if len(fact) >= 2:
            facts_for_ocaml.append({
                "predicate": fact[0],
                "arguments": fact[1:]
            })
    
    # Wrap formula in policy structure
    wrapped_formula = f"""regulation HIPAA version "1.0"
policy starts
{formula}
;
policy ends"""
    
    # Build request
    precis_request = {
        "formula": wrapped_formula,
        "facts": {
            "facts": facts_for_ocaml
        },
        "regulation": "HIPAA"
    }
    
    try:
        proc = subprocess.Popen(
            [PRECIS_PATH, "json"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(PRECIS_PATH) if os.path.dirname(PRECIS_PATH) else "."
        )
        
        precis_output, precis_error = proc.communicate(
            input=json.dumps(precis_request),
            timeout=30
        )
        
        if proc.returncode == 0 and precis_output.strip():
            try:
                precis_json = json.loads(precis_output)
                
                # Check evaluation result
                if "evaluations" in precis_json and len(precis_json["evaluations"]) > 0:
                    eval_result = precis_json["evaluations"][0].get("evaluation", {})
                    if eval_result.get("result") == "true":
                        verified = True
                    else:
                        verified = False
                
                pipeline_steps = [
                    "✅ Step 1: Parsing (Lexer → Parser → AST)",
                    "✅ Step 2: Type Checking",
                    "✅ Step 3: Evaluation Engine",
                    "✅ Step 4: Results Generated",
                ]
                
                if verified:
                    pipeline_steps.append("✅ Verification: PASSED")
                else:
                    pipeline_steps.append("❌ Verification: FAILED")
                
                precis_result = {
                    "success": True,
                    "output": json.dumps(precis_json, indent=2),
                    "error": "",
                    "pipeline_steps": pipeline_steps,
                    "json_response": precis_json
                }
                
            except json.JSONDecodeError:
                precis_result = {
                    "success": False,
                    "output": precis_output,
                    "error": f"JSON parse failed: {precis_output[:200]}",
                    "pipeline_steps": ["❌ JSON parsing failed"]
                }
        else:
            precis_result = {
                "success": False,
                "output": precis_output,
                "error": precis_error,
                "pipeline_steps": ["❌ Précis execution failed"]
            }
    
    except subprocess.TimeoutExpired:
        precis_result = {
            "success": False,
            "output": "",
            "error": "Timeout (30s)",
            "pipeline_steps": ["❌ Timeout"]
        }
    except Exception as e:
        precis_result = {
            "success": False,
            "output": "",
            "error": str(e),
            "pipeline_steps": [f"❌ Error: {str(e)}"]
        }
    
    steps.append(f"✅ OCaml processing complete")
    
    # =====================================
    # STEP 4: LLM2 - Generate Explanation
    # =====================================
    steps.append("💬 LLM2: Generating explanation...")
    
    explain_prompt = f"""Explain this compliance verification result to a non-technical user.

Question: {query}
Facts Extracted: {validated_facts}
Formula Checked: {formula}
Verification Result: {"PASSED (Compliant)" if verified else "FAILED (Violation)"}

Provide:
1. Direct YES/NO answer to user's question
2. Brief explanation (2-3 sentences) of why
3. Cite specific HIPAA section: §164.502(a)(1)(i)
4. Actionable guidance if needed

Keep it simple and clear."""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": explain_prompt}]
        )
        explanation = message.content[0].text
    except Exception as e:
        explanation = f"Unable to generate explanation: {e}"
    
    return {
        "name": "Pipeline4Compliance ⭐",
        "answer": explanation,
        "duration": time.time() - start,
        "steps": steps,
        "extracted_facts": validated_facts,
        "formula": formula,
        "precis_result": precis_result,
        "verified": verified,
        "method": "LLM1 (Extract+Translate) → OCaml Précis → LLM2 (Explain)",
        "compliance_status": "✅ COMPLIANT" if verified else "❌ VIOLATION"
    }

# ============================================
# UNIFIED DISPLAY FOR ALL EXPERIMENTS
# ============================================

def display_experiment_result(result: dict):
    """
    Universal display function for ALL experiments (Baseline, RAG, Pipeline, Agentic)
    Shows verdict with color-coded background for all experiments
    """
    
    # 1. DETERMINE VERDICT (works for all experiment types)
    verdict = determine_verdict(result)
    
    # 2. BIG VERDICT with colored background
    if verdict['status'] == 'compliant':
        st.success(f"## ✅ {verdict['text']}")
    elif verdict['status'] == 'violation':
        st.error(f"## ❌ {verdict['text']}")
    else:
        st.warning(f"## ⚠️ {verdict['text']}")
    
    # 3. METRICS ROW
    display_metrics(result, verdict)
    
    # 4. MAIN ANSWER
    st.markdown("### 💬 Answer")
    st.info(result['answer'])
    
    # 5. TYPE-SPECIFIC DETAILS (only for Pipeline/Agentic)
    if 'precis_result' in result:
        display_pipeline_details(result)
    elif 'retrieved_policies' in result:
        display_rag_details(result)
    
    # 6. TECHNICAL DETAILS (collapsible for all)
    display_technical_details(result)

def determine_verdict(result: dict) -> dict:
    """Extract verdict from any experiment type"""
    
    # Check explicit compliance_status first
    if 'compliance_status' in result:
        status_str = result['compliance_status']
        if "COMPLIANT" in status_str and "NOT" not in status_str:
            return {'status': 'compliant', 'text': 'COMPLIANT'}
        elif "VIOLATION" in status_str or "NOT COMPLIANT" in status_str:
            return {'status': 'violation', 'text': 'VIOLATION DETECTED'}
        else:
            return {'status': 'unknown', 'text': 'INCONCLUSIVE'}
    
    # Check precis_result evaluations (Pipeline/Agentic)
    if 'precis_result' in result:
        precis = result.get('precis_result', {})
        precis_json = precis.get('json_response', {})
        
        # Check if OCaml succeeded
        if not precis.get('success', False):
            return {'status': 'unknown', 'text': 'VERIFICATION FAILED (OCaml Error)'}
        
        # Check overall_compliant flag (most reliable)
        if 'overall_compliant' in precis_json:
            if precis_json['overall_compliant']:
                return {'status': 'compliant', 'text': 'COMPLIANT'}
            else:
                violation_count = len(precis_json.get('violations', []))
                return {
                    'status': 'violation', 
                    'text': f'VIOLATION DETECTED ({violation_count} policies violated)'
                }
        
        # Fallback: check evaluations
        evaluations = precis_json.get('evaluations', [])
        if evaluations:
            violations = [e for e in evaluations if e.get('evaluation', {}).get('result') == 'false']
            if violations:
                return {
                    'status': 'violation',
                    'text': f'VIOLATION DETECTED ({len(violations)}/{len(evaluations)} policies)'
                }
            else:
                return {'status': 'compliant', 'text': 'COMPLIANT'}
    
    # Check verified flag (simple boolean)
    if 'verified' in result:
        if result['verified']:
            return {'status': 'compliant', 'text': 'COMPLIANT'}
        else:
            return {'status': 'violation', 'text': 'VIOLATION DETECTED'}
    
    # For Baseline/RAG: Analyze the answer text
    answer = result.get('answer', '').lower()
    
    # Look for positive indicators
    if any(word in answer for word in ['yes', 'can share', 'permitted', 'allowed', 'compliant']):
        if any(word in answer for word in ['but', 'only if', 'must', 'require', 'authorization']):
            return {'status': 'compliant', 'text': 'CONDITIONAL YES (with requirements)'}
        return {'status': 'compliant', 'text': 'YES'}
    
    # Look for negative indicators
    if any(word in answer for word in ['no', 'cannot', 'prohibited', 'violation', 'not permitted']):
        return {'status': 'violation', 'text': 'NO (Violation)'}
    
    # Default: unknown
    return {'status': 'unknown', 'text': 'NO VERIFICATION PERFORMED'}

def display_metrics(result: dict, verdict: dict):
    """Display metrics row with verdict badge"""
    
    cols = st.columns(4)
    
    # Time
    cols[0].metric("⏱️ Time", f"{result['duration']:.1f}s")
    
    # Status with color
    if verdict['status'] == 'compliant':
        cols[1].metric("Status", "✅ COMPLIANT", delta="Verified")
    elif verdict['status'] == 'violation':
        cols[1].metric("Status", "❌ VIOLATION", delta="Failed", delta_color="inverse")
    else:
        cols[1].metric("Status", "⚠️ UNKNOWN", delta="No verification")
    
    # Policies or analysis
    if 'precis_result' in result:
        precis_json = result.get('precis_result', {}).get('json_response', {})
        
        # Show compliant vs violations
        violations = precis_json.get('violations', [])
        evaluations = precis_json.get('evaluations', [])
        
        if evaluations:
            compliant_count = len(evaluations) - len(violations)
            violation_count = len(violations)
            
            cols[2].metric("✅ Satisfied", compliant_count, 
                          delta=f"of {len(evaluations)} policies")
            cols[3].metric("❌ Violated", violation_count, 
                          delta_color="inverse" if violation_count > 0 else "off")
        else:
            cols[2].metric("📋 Policies", "0")
            cols[3].metric("🔄 Steps", len(result.get('steps', [])))
    else:
        # For Baseline/RAG - show confidence
        if 'analysis' in result:
            confidence = result['analysis'].get('confidence', 0)
            cols[2].metric("🎯 Confidence", f"{confidence*100:.0f}%")
            
            # Show reasoning
            reasoning = result['analysis'].get('reasoning', 'N/A')
            cols[3].metric("📊 Analysis", reasoning[:20] + "..." if len(reasoning) > 20 else reasoning)
        else:
            cols[2].metric("📚 Source", "Internal knowledge" if result['name'] == 'Baseline' else 'Policy DB')
            if 'retrieved_policies' in result:
                cols[3].metric("📄 Retrieved", result['retrieved_policies'])
            else:
                cols[3].metric("🔄 Steps", len(result.get('steps', [])))

def display_pipeline_details(result: dict):
    """Display details specific to Pipeline/Agentic experiments"""
    
    precis_json = result.get('precis_result', {}).get('json_response', {})
    
    # Top Relevant Policies
    matched_policies = precis_json.get('matched_policies', [])
    if matched_policies:
        st.markdown("### 📚 Most Relevant Policies")
        
        top_policies = sorted(matched_policies, key=lambda x: x.get('relevance_score', 0), reverse=True)[:3]
        
        for i, policy in enumerate(top_policies, 1):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"**{i}. {policy['regulation']} {policy['section']}**")
                st.markdown(f"_{policy['description']}_")
            with col_b:
                score = policy['relevance_score']
                if score > 0.5:
                    st.success(f"🎯 {score:.0%}")
                elif score > 0.3:
                    st.warning(f"📊 {score:.0%}")
                else:
                    st.info(f"📉 {score:.0%}")
    
    # Violation Details
    evaluations = precis_json.get('evaluations', [])
    violations = [e for e in evaluations if e.get('evaluation', {}).get('result') == 'false']
    
    if violations:
        st.markdown("### ⚠️ Violations Found")
        for v in violations:
            st.error(f"""
**{v['section']}**: {v['description']}  
{v['explanation']}
            """)

def display_rag_details(result: dict):
    """Display details specific to RAG experiments"""
    
    if result['retrieved_policies'] == 0:
        st.warning("⚠️ No policies were retrieved from the database")

def display_technical_details(result: dict):
    """Collapsible technical details for all experiments"""
    
    with st.expander("🔬 Technical Details", expanded=False):
        
        # Pipeline steps
        if result.get('steps'):
            st.markdown("#### 🔄 Processing Steps")
            for step in result['steps']:
                st.markdown(f"- {step}")
        
        # Extracted facts (Pipeline/Agentic)
        if 'extracted_facts' in result:
            st.markdown("#### 🧩 Extracted Facts")
            st.json(result['extracted_facts'])
        
        # Formula (Pipeline/Agentic)
        if 'formula' in result:
            st.markdown("#### 📐 Formal Logic Formula")
            st.code(result['formula'], language="text")
        
        # OCaml Pipeline (Pipeline/Agentic)
        if 'precis_result' in result:
            st.markdown("#### ⚙️ OCaml Précis Pipeline")
            precis = result['precis_result']
            
            if 'pipeline_steps' in precis:
                for step in precis['pipeline_steps']:
                    st.markdown(f"- {step}")
            
            if precis.get('success'):
                st.markdown("**Full OCaml Output:**")
                st.code(precis.get('output', ''), language="json")
            else:
                st.error(f"OCaml Error: {precis.get('error', 'Unknown')}")



def display_simple_result(r: dict):
    """Simple display for Baseline and RAG experiments"""
    
    # Metrics row
    cols = st.columns(3)
    cols[0].metric("⏱️ Time", f"{r['duration']:.1f}s")
    cols[1].metric("📊 Method", r['method'])
    
    # Status (if available)
    if 'compliance_status' in r:
        status = r['compliance_status']
        if "COMPLIANT" in status and "NOT" not in status:
            cols[2].metric("Status", "✅ COMPLIANT", delta="Verified")
        elif "NOT COMPLIANT" in status or "VIOLATION" in status:
            cols[2].metric("Status", "👎 VIOLATION ❌", delta="Failed")
        else:
            cols[2].metric("Status", "⚠️ UNKNOWN", delta="Inconclusive")
    elif 'verified' in r:
        cols[2].metric("Verified", "✅" if r['verified'] else "❌")
    
    # Pipeline steps (compact)
    with st.expander("🔄 Pipeline Steps", expanded=False):
        for step in r['steps']:
            st.markdown(f"- {step}")
    
    # Main answer
    st.markdown("### 💬 Answer")
    st.info(r['answer'])
    
    # Optional: Show any warnings
    if 'retrieved_policies' in r and r['retrieved_policies'] == 0:
        st.warning("⚠️ No policies were retrieved from the database")


def format_agent4_result_simple(result: dict) -> dict:
    """Transform overwhelming output into user-friendly format"""
    
    precis_json = result.get('precis_result', {}).get('json_response', {})
    evaluations = precis_json.get('evaluations', [])

    violations = [e for e in evaluations if e.get('evaluation', {}).get('result') == 'false']
    compliant = [e for e in evaluations if e.get('evaluation', {}).get('result') == 'true']
    
    if len(violations) > 0:
        verdict = "❌ VIOLATION DETECTED"
        verdict_color = "red"
    else:
        verdict = "✅ COMPLIANT"
        verdict_color = "green"
    
    matched_policies = precis_json.get('matched_policies', [])
    top_policies = sorted(matched_policies, key=lambda x: x.get('relevance_score', 0), reverse=True)[:3]
    
    return {
        "verdict": verdict,
        "verdict_color": verdict_color,
        "summary": {
            "total_policies_checked": len(evaluations),
            "violations": len(violations),
            "compliant": len(compliant)
        },
        "top_relevant_policies": [
            {
                "regulation": p.get('regulation'),
                "section": p.get('section'),
                "description": p.get('description'),
                "relevance_score": p.get('relevance_score', 0)
            }
            for p in top_policies
        ],
        "violations_detail": [
            {
                "policy_id": v.get('policy_id'),
                "section": v.get('section'),
                "description": v.get('description'),
                "explanation": v.get('explanation')
            }
            for v in violations
        ]
    }


def display_agent4_result(result: dict):
    """Display Pipeline4Compliance and Agentic with clean UI but keep technical details available"""
    
    simplified = format_agent4_result_simple(result)
    
    # 1. BIG VERDICT
    if simplified['verdict_color'] == 'green':
        st.success(f"## {simplified['verdict']}")
    else:
        st.error(f"## {simplified['verdict']}")
    
    # 2. Summary Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("⏱️ Time", f"{result['duration']:.1f}s")
    col2.metric("📋 Policies Checked", simplified['summary']['total_policies_checked'])
    col3.metric("✅ Compliant", simplified['summary']['compliant'])
    col4.metric("❌ Violations", simplified['summary']['violations'])
    
    # 3. Main Answer
    st.markdown("### 💬 Answer")
    st.info(result['answer'])
    
    # 4. Top Relevant Policies
    if simplified['top_relevant_policies']:
        st.markdown("### 📚 Most Relevant HIPAA Sections")
        st.caption("These policies were matched based on semantic similarity to your query")
        
        for i, policy in enumerate(simplified['top_relevant_policies'], 1):
            with st.container():
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"**{i}. {policy['regulation']} {policy['section']}**")
                    st.markdown(f"_{policy['description']}_")
                with col_b:
                    # Explain relevance score
                    score = policy['relevance_score']
                    if score > 0.5:
                        st.success(f"🎯 {score:.0%} match")
                    elif score > 0.3:
                        st.warning(f"📊 {score:.0%} match")
                    else:
                        st.info(f"📉 {score:.0%} match")
        
        st.caption("💡 **Relevance Score** = Formula similarity (shared predicates), NOT compliance score")
    
    # 5. Violation Details (if any)
    if simplified['violations_detail']:
        st.markdown("### ⚠️ Violations Found")
        for v in simplified['violations_detail']:
            st.error(f"""
**{v['section']}**: {v['description']}  
{v['explanation']}
            """)
    
    # 6. Pipeline Steps (visible but compact)
    with st.expander("🔄 Processing Pipeline", expanded=False):
        for step in result['steps']:
            st.markdown(f"- {step}")
    
    # 7. Technical Details (collapsed by default - KEEP FOR YOU!)
    with st.expander("🔬 Under The Hood (Technical Details)", expanded=False):
        
        st.markdown("#### 🧩 Extracted Facts")
        st.json(result.get('extracted_facts', []))
        
        st.markdown("#### 📐 Formal Logic Formula")
        st.code(result.get('formula', 'N/A'), language="text")
        
        st.markdown("#### ⚙️ OCaml Précis Pipeline")
        precis = result.get('precis_result', {})
        
        if 'pipeline_steps' in precis:
            for step in precis['pipeline_steps']:
                st.markdown(f"- {step}")
        
        if precis.get('success'):
            st.markdown("#### 📊 Full OCaml Output")
            st.code(precis.get('output', ''), language="json")
        else:
            st.error(f"❌ OCaml Error: {precis.get('error', 'Unknown')}")
        
        # Show validation warnings
        validation_warnings = [s for s in result['steps'] if "⚠️" in s]
        if validation_warnings:
            st.markdown("#### ⚠️ Validation Issues")
            for warning in validation_warnings:
                st.warning(warning)

class DocumentExtractor:
    @staticmethod
    def extract_from_pdf(file_bytes) -> str:
        """Extract text from PDF bytes"""
        pdf_file = BytesIO(file_bytes)
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n\n"
        return text
    
    @staticmethod
    def extract_from_txt(file_bytes) -> str:
        """Extract text from plain text"""
        return file_bytes.decode('utf-8')
    
    @staticmethod
    def extract(uploaded_file) -> str:
        """Auto-detect and extract"""
        file_bytes = uploaded_file.read()
        
        if uploaded_file.name.endswith('.pdf'):
            return DocumentExtractor.extract_from_pdf(file_bytes)
        else:
            return DocumentExtractor.extract_from_txt(file_bytes)

class SectionChunker:
    @staticmethod
    def chunk_by_section_numbers(text: str) -> list:
        """Extract sections based on §XXX.XXX pattern"""
        section_pattern = r'§\s*(\d+\.\d+(?:\([a-z0-9]+\))*)'
        
        sections = []
        matches = list(re.finditer(section_pattern, text))
        
        for i, match in enumerate(matches):
            section_num = match.group(1)
            start = match.start()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            
            section_text = text[start:end].strip()
            
            # Only include sections with substantial text (>100 chars)
            if len(section_text) > 100:
                sections.append({
                    'section': f"§{section_num}",
                    'text': section_text[:1000]  # Limit to 1000 chars for LLM
                })
        
        return sections

# ============================================
# POLICY PIPELINE
# ============================================

class PolicyIdentifier:
    def __init__(self, client: Anthropic):
        self.client = client
    
    def identify_policies(self, section: dict) -> list:
        """Use LLM to identify policy statements"""
        prompt = f"""Analyze this regulatory text and identify POLICY STATEMENTS.

Text:
{section['text']}

A policy statement specifies:
1. Conditions (IF/WHEN)
2. Actions (MAY/SHALL/MUST)
3. Can be formalized as logic

Output JSON array:
[
  {{
    "statement": "exact text",
    "section": "{section['section']}",
    "title": "brief title",
    "conditions": ["cond1", "cond2"],
    "action": "what is permitted/required"
  }}
]

If no policies, return [].
Output ONLY JSON:"""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            
            if json_match:
                return json.loads(json_match.group())
            return []
        except Exception as e:
            st.error(f"Error identifying policies: {e}")
            return []

class FOTLTranslator:
    def __init__(self, client: Anthropic):
        self.client = client
    
    def translate_policy(self, policy: dict) -> dict:
        """Convert policy to FOTL formula"""
        prompt = f"""Convert this policy to first-order temporal logic (FOTL).

Policy: {policy['statement']}
Section: {policy['section']}
Title: {policy['title']}

FOTL SYNTAX:
- Predicates: coveredEntity(X), protectedHealthInfo(X), disclose(W,X,Y,Z)
- Constants: @Treatment, @Research, @PublicHealth
- Quantifiers: forall X, Y. (...)
- Operators: and, or, implies, not
- Pattern: forall vars. (conditions) implies (action)

EXAMPLES:

Policy: "Covered entity may disclose PHI for treatment without authorization"
FOTL:
forall ce, patient, phi, purpose.
  (coveredEntity(ce) and protectedHealthInfo(phi) and purposeIsPurpose(purpose, @Treatment))
  implies permittedUseOrDisclosure(ce, patient, phi, purpose)

Policy: "Authorization required for research"
FOTL:
forall ce, researcher, phi, purpose.
  (coveredEntity(ce) and protectedHealthInfo(phi) and purposeIsPurpose(purpose, @Research))
  implies requiresAuthorization(ce, researcher, phi)

Output ONLY the FOTL formula:"""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            formula = message.content[0].text.strip()
            
            if "```" in formula:
                match = re.search(r'```.*?\n(.*?)\n```', formula, re.DOTALL)
                if match:
                    formula = match.group(1).strip()
            
            # Clean up
            formula = formula.split('\n')[0].strip()
            
            return {
                **policy,
                'fotl_formula': formula
            }
        except Exception as e:
            st.error(f"Error translating policy: {e}")
            return {**policy, 'fotl_formula': 'ERROR'}

class FormulaValidator:
    def __init__(self, precis_path: str):
        self.precis_path = precis_path
    
    def validate(self, formula: str) -> tuple:
        """Validate formula with Précis"""
        wrapped = f"""regulation TEST version "1.0"
policy starts
{formula}
;
policy ends"""
        
        request = {
            "formula": wrapped,
            "facts": {"facts": []},
            "regulation": "TEST"
        }
        
        try:
            proc = subprocess.Popen(
                [self.precis_path, "json"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            stdout, stderr = proc.communicate(input=json.dumps(request))
            
            if proc.returncode == 0:
                response = json.loads(stdout)
                if 'error' in response:
                    return False, response['error']
                return True, "Valid"
            else:
                return False, stderr
        except Exception as e:
            return False, str(e)

##====MULTI-POLICY IMPLEMENTATION========##

class RegulationConfig:
    """Configuration for each regulation"""
    
    HIPAA = {
        'name': 'HIPAA',
        'full_name': 'Health Insurance Portability and Accountability Act',
        'section_pattern': r'§\s*(\d+\.\d+(?:\([a-z0-9]+\))*)',
        'section_prefix': '§',
        'predicates': {
            # Entity types (1 arg)
            'coveredEntity': 1,
            'businessAssociate': 1,
            'protectedHealthInfo': 1,
            'publicHealthAuthority': 1,
            # Relationships (2 args)
            'familyMember': 2,
            'involvedInCare': 2,
            'hasRecord': 2,
            'purposeIsPurpose': 2,
            'hasBAA': 2,
            # Permissions (3 args)
            'hasConsent': 3,
            'hasAuthorization': 3,
            # Disclosure (4 args)
            'disclose': 4,
            'permittedUseOrDisclosure': 4,
        },
        'constants': {
            'Treatment', 'Payment', 'HealthcareOperations',
            'Research', 'PublicHealth', 'Emergency'
        },
        'sorts': {'Entity', 'PHI', 'Purpose'},
        'example_formula': """forall ce, patient, phi, purpose.
  (coveredEntity(ce) and protectedHealthInfo(phi) and purposeIsPurpose(purpose, @Treatment))
  implies permittedUseOrDisclosure(ce, patient, phi, purpose)"""
    }
    
    GDPR = {
        'name': 'GDPR',
        'full_name': 'General Data Protection Regulation',
        'section_pattern': r'Article\s+(\d+)',
        'section_prefix': 'Article ',
        'predicates': {
            # Entity types (1 arg)
            'dataSubject': 1,
            'dataController': 1,
            'dataProcessor': 1,
            'personalData': 1,
            'supervisoryAuthority': 1,
            # Relationships (2 args)
            'processingPurpose': 2,
            'hasLegalBasis': 2,
            'purposeIsPurpose': 2,
            # Rights (2 args)
            'hasRight': 2,
            'hasConsent': 2,
            # Processing (3 args)
            'processData': 3,
            'transferData': 3,
            # Adequacy (1 arg)
            'adequacyDecision': 1,
            'appropriateSafeguards': 1,
        },
        'constants': {
            'Consent', 'Contract', 'LegalObligation', 'VitalInterest',
            'PublicInterest', 'LegitimateInterest'
        },
        'sorts': {'Entity', 'PersonalData', 'Purpose', 'LegalBasis'},
        'example_formula': """forall dc, ds, data, purpose.
  (dataController(dc) and dataSubject(ds) and personalData(data) and purposeIsPurpose(purpose, @Consent))
  implies requiresConsent(dc, ds, data)"""
    }
    
    CCPA = {
        'name': 'CCPA',
        'full_name': 'California Consumer Privacy Act',
        'section_pattern': r'Section\s+(\d+(?:\.\d+)?)',
        'section_prefix': 'Section ',
        'predicates': {
            'business': 1,
            'consumer': 1,
            'personalInformation': 1,
            'serviceProvicer': 1,
            'hasOptOut': 2,
            'sellsData': 3,
            'disclosesData': 3,
        },
        'constants': {'Sale', 'Disclosure', 'BusinessPurpose'},
        'sorts': {'Entity', 'PersonalInfo', 'Purpose'},
        'example_formula': """forall b, c, data.
  (business(b) and consumer(c) and personalInformation(data) and sellsData(b, c, data))
  implies hasOptOutRight(c, b)"""
    }
    
    GLBA = {
        'name': 'GLBA',
        'full_name': 'Gramm-Leach-Bliley Act',
        'section_pattern': r'Section\s+(\d+(?:\.\d+)?)',
        'section_prefix': 'Section ',
        'predicates': {
            'financialInstitution': 1,
            'customer': 1,
            'nonpublicPersonalInformation': 1,
            'hasPrivacyNotice': 2,
            'sharesData': 3,
            'optOutProvided': 2,
        },
        'constants': {'Marketing', 'ServiceProvision', 'LegalCompliance'},
        'sorts': {'Entity', 'NonpublicInfo', 'Purpose'},
        'example_formula': """forall fi, cust, info.
  (financialInstitution(fi) and customer(cust) and nonpublicPersonalInformation(info) and sharesData(fi, cust, info))
  implies optOutProvided(cust, fi)"""
    }
    
    SOX = {
        'name': 'SOX',
        'full_name': 'Sarbanes-Oxley Act',
        'section_pattern': r'Section\s+(\d+(?:\.\d+)?)',
        'section_prefix': 'Section ',
        'predicates': {
            'publicCompany': 1,
            'officer': 1,
            'financialReport': 1,
            'hasInternalControls': 2,
            'certifiesReport': 2,
        },
        'constants': {'Accuracy', 'Timeliness', 'Compliance'},
        'sorts': {'Entity', 'Report', 'Purpose'},
        'example_formula': """forall pc, off, report.
  (publicCompany(pc) and officer(off) and financialReport(report) and certifiesReport(off, report))
  implies hasInternalControls(pc, report)"""
    }
    
    COPPA = {
        'name': 'COPPA',
        'full_name': 'Children\'s Online Privacy Protection Act',
        'section_pattern': r'Section\s+(\d+(?:\.\d+)?)',
        'section_prefix': 'Section ',
        'predicates': {
            'operator': 1,
            'child': 1,
            'personalInformation': 1,
            'hasParentalConsent': 2,
            'collectsData': 3,
        },
        'constants': {'ParentalConsent', 'ServiceProvision', 'LegalCompliance'},
        'sorts': {'Entity', 'PersonalInfo', 'Purpose'},
        'example_formula': """forall op, ch, info.
  (operator(op) and child(ch) and personalInformation(info) and collectsData(op, ch, info))
  implies hasParentalConsent(ch, op)"""
    }
    
    
    
    @classmethod
    def get_config(cls, regulation: str):
        """Get configuration for regulation"""
        configs = {
            'HIPAA': cls.HIPAA,
            'GDPR': cls.GDPR,
            'CCPA': cls.CCPA,
            'GLBA': cls.GLBA,
            'SOX': cls.SOX,
            'COPPA': cls.COPPA
        }
        return configs.get(regulation.upper(), cls.HIPAA)
    
    @classmethod
    def detect_regulation(cls, text: str) -> str:
        """Auto-detect regulation from document"""
        text_sample = text[:10000].lower()
        
        scores = {
            'HIPAA': 0,
            'GDPR': 0,
            'CCPA': 0,
            'GLBA': 0,
            'SOX': 0,
            'COPPA': 0
        }
        
        # HIPAA indicators
        if 'health insurance portability' in text_sample or '§164' in text[:5000]:
            scores['HIPAA'] += 10
        if 'covered entity' in text_sample:
            scores['HIPAA'] += 5
        if 'protected health information' in text_sample:
            scores['HIPAA'] += 5
            
        # GDPR indicators
        if 'general data protection regulation' in text_sample:
            scores['GDPR'] += 10
        if re.search(r'article\s+\d+', text[:5000], re.IGNORECASE):
            scores['GDPR'] += 5
        if 'data controller' in text_sample or 'data subject' in text_sample:
            scores['GDPR'] += 5
            
        # CCPA indicators
        if 'california consumer privacy' in text_sample:
            scores['CCPA'] += 10
        if 'section 1798' in text_sample:
            scores['CCPA'] += 5
        
        # GLBA indicators
        if 'gramm-leach-bliley' in text_sample or 'financial institutions' in text_sample:
            scores['GLBA'] += 10
        if 'nonpublic personal information' in text_sample:
            scores['GLBA'] += 5 
        if 'privacy notice' in text_sample:
            scores['GLBA'] += 5

        # SOX indicators
        if 'sarbanes-oxley' in text_sample or 'public company accounting' in text_sample:
            scores['SOX'] += 10
        if 'financial report' in text_sample:
            scores['SOX'] += 5
        if 'internal controls' in text_sample:
            scores['SOX'] += 5  

        # COPPA indicators
        if "children's online privacy" in text_sample or 'section 1303' in text_sample:
            scores['COPPA'] += 10
        if 'parental consent' in text_sample:
            scores['COPPA'] += 5
        if 'personal information of children' in text_sample:
            scores['COPPA'] += 5  
        
        # Determine highest score
        detected = max(scores, key=scores.get)
        return detected if scores[detected] > 0 else 'UNKNOWN'

class TypeSystemGenerator:
    """Auto-generate type system in YOUR format"""
    
    @staticmethod
    def extract_predicates_from_formula(formula: str) -> dict:
        """Extract predicates and their arities from a formula"""
        predicates = {}
        
        # Pattern: predicate_name(arg1, arg2, ...)
        pattern = r'(\w+)\(((?:\w+(?:,\s*)?)+)\)'
        
        for match in re.finditer(pattern, formula):
            pred_name = match.group(1)
            args = [a.strip() for a in match.group(2).split(',')]
            arity = len(args)
            
            # Skip logical operators and keywords
            if pred_name.lower() in ['forall', 'exists', 'and', 'or', 'implies', 'not']:
                continue
                
            predicates[pred_name] = arity
        
        return predicates
    
    @staticmethod
    def extract_constants_from_formula(formula: str) -> set:
        """Extract constants (@Constant) from formula"""
        constants = set()
        pattern = r'@(\w+)'
        
        for match in re.finditer(pattern, formula):
            constants.add(match.group(1))
        
        return constants
    
    @staticmethod
    def generate_type_system(
        regulation: str,
        formulas: list,
        config: dict
    ) -> str:
        """Generate type system in YOUR actual format"""
        
        # Collect all predicates and constants
        all_predicates = {}
        all_constants = set()
        
        for formula in formulas:
            preds = TypeSystemGenerator.extract_predicates_from_formula(formula)
            all_predicates.update(preds)
            
            consts = TypeSystemGenerator.extract_constants_from_formula(formula)
            all_constants.update(consts)
        
        # Build type system file in YOUR format
        lines = []
        lines.append(f"# AUTO-GENERATED TYPE SYSTEM FOR {regulation}")
        lines.append(f"# Generated: {datetime.now().isoformat()}")
        lines.append("")
        
        # PREDICATES section
        lines.append("PREDICATES")
        
        # Add True/False (standard)
        lines.append("True : Bool")
        lines.append("False : Bool")
        
        # Add extracted predicates
        for pred_name, arity in sorted(all_predicates.items()):
            # Generate signature based on arity
            if arity == 1:
                sig = "Entity -> Bool"
            elif arity == 2:
                sig = "Entity Entity -> Bool"
            elif arity == 3:
                sig = "Entity Entity Entity -> Bool"
            elif arity == 4:
                sig = "Entity Entity PHI Purpose -> Bool"
            else:
                sig = " ".join(["Entity"] * arity) + " -> Bool"
            
            lines.append(f"{pred_name} : {sig}")
        
        lines.append("")
        
        # CONSTANTS section
        lines.append("CONSTANTS")
        for const in sorted(all_constants):
            # Infer type - assume Purpose for now
            lines.append(f"@{const} : Purpose")
        
        lines.append("")
        
        # FUNCTIONS section (empty but include structure)
        lines.append("FUNCTIONS")
        lines.append("# Add custom functions here if needed")
        lines.append("# Example: age : Entity -> Int")
        
        return "\n".join(lines)

# ============================================
# POLICY FILE GENERATOR
# ============================================

class PolicyFileGenerator:
    """Generate regulation-specific .policy files"""
    
    @staticmethod
    def generate(
        regulation: str,
        version: str,
        policies: list,
        output_path: str
    ):
        """Generate .policy file"""
        lines = []
        
        # Header
        lines.append(f'regulation {regulation} version "{version}"')
        lines.append("")
        lines.append("policy starts")
        lines.append("")
        
        # Policies
        for policy in policies:
            # Annotation
            annotation = f'@["{policy["section"]} - {policy["title"]}"]'
            lines.append(annotation)
            
            # Formula (ensure proper formatting)
            formula = policy['fotl_formula'].strip()
            if not formula.endswith(';'):
                formula += ' ;'
            
            lines.append(formula)
            lines.append("")
        
        lines.append("policy ends")
        
        # Write file
        content = '\n'.join(lines)
        
        with open(output_path, 'w') as f:
            f.write(content)
        
        return content

# ============================================
# MULTI-REGULATION DOCUMENT PIPELINE
# ============================================

class MultiRegulationPipeline:
    """Complete pipeline with auto-generation"""
    
    def __init__(self, client: Anthropic, precis_path: str):
        self.client = client
        self.precis_path = precis_path
    
    def process_document(
        self,
        uploaded_file,
        max_sections: int = 5
    ) -> dict:
        """Process document and generate both policy file and type system"""
        
        results = {
            'regulation': None,
            'sections': [],
            'policies': [],
            'type_system': '',
            'policy_file': '',
            'errors': []
        }
        
        # Step 1: Extract text
        from io import BytesIO
        import PyPDF2
        
        file_bytes = uploaded_file.read()
        
        if uploaded_file.name.endswith('.pdf'):
            pdf_file = BytesIO(file_bytes)
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n\n"
        else:
            text = file_bytes.decode('utf-8')
        
        # Step 2: Detect regulation
        regulation = RegulationConfig.detect_regulation(text)
        results['regulation'] = regulation
        
        config = RegulationConfig.get_config(regulation)
        
        # Step 3: Extract sections
        sections = self._extract_sections(text, config, max_sections)
        results['sections'] = sections
        
        # Step 4: Identify policies
        policies = []
        for section in sections:
            section_policies = self._identify_policies(section, regulation)
            policies.extend(section_policies)
        
        # Step 5: Translate to FOTL
        translated_policies = []
        for policy in policies:
            translated = self._translate_policy(policy, config)
            if translated and len(translated.get('fotl_formula', '')) > 20:
                translated_policies.append(translated)
        
        results['policies'] = translated_policies
        
        # Step 6: Generate type system
        formulas = [p['fotl_formula'] for p in translated_policies]
        type_system = TypeSystemGenerator.generate_type_system(
            regulation,
            formulas,
            config
        )
        results['type_system'] = type_system
        
        # Step 7: Generate policy file
        policy_file = PolicyFileGenerator.generate(
            regulation,
            "1.0",
            translated_policies,
            f"policies/{regulation.lower()}_generated.policy"
        )
        results['policy_file'] = policy_file
        
        return results
    
    def _extract_sections(self, text: str, config: dict, max_sections: int) -> list:
        """Extract sections using regulation-specific pattern"""
        sections = []
        pattern = config['section_pattern']
        prefix = config['section_prefix']
        
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        
        for i, match in enumerate(matches[:max_sections]):
            section_num = match.group(1)
            start = match.start()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            
            section_text = text[start:end].strip()[:2000]
            
            if len(section_text) > 100:
                sections.append({
                    'section': f"{prefix}{section_num}",
                    'text': section_text
                })
        
        return sections
    
    def _identify_policies(self, section: dict, regulation: str) -> list:
        """Identify policy statements in section"""
        prompt = f"""Analyze this {regulation} regulatory text and identify POLICY STATEMENTS.

Text:
{section['text']}

A policy statement specifies conditions and actions that can be formalized.

Output JSON array:
[
  {{
    "statement": "exact text of requirement",
    "section": "{section['section']}",
    "title": "brief title",
    "conditions": ["condition1", "condition2"],
    "action": "what is required/permitted"
  }}
]

If no clear policies, return [].
Output ONLY JSON:"""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            
            if json_match:
                policies = json.loads(json_match.group())
                # Filter quality
                return [p for p in policies 
                       if len(p.get('statement', '')) > 50 
                       and p.get('conditions') 
                       and p.get('action')]
            return []
        except:
            return []
    
    def _translate_policy(self, policy: dict, config: dict) -> dict:
        """Translate policy to FOTL"""
        prompt = f"""Convert this {config['name']} policy to first-order logic (FOTL).

Policy: {policy['statement']}
Section: {policy['section']}

AVAILABLE PREDICATES:
{', '.join([f"{p}({a} args)" for p, a in config['predicates'].items()])}

CONSTANTS:
{', '.join([f"@{c}" for c in config['constants']])}

EXAMPLE:
{config['example_formula']}

CRITICAL:
1. Output a COMPLETE formula with both sides of implies
2. Use purposeIsPurpose(var, @Constant) for purposes
3. Formula must end with closing parenthesis
4. Single line output

Output ONLY the formula:"""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            formula = message.content[0].text.strip()
            
            # Clean up
            if "```" in formula:
                formula = re.sub(r'```(?:ocaml|fotl)?\s*\n(.*?)\n```', r'\1', formula, flags=re.DOTALL)
                formula = re.sub(r'```', '', formula)
            
            formula = ' '.join(formula.split())
            
            if len(formula) > 20:
                return {**policy, 'fotl_formula': formula}
            
        except Exception as e:
            pass
        
        return None

