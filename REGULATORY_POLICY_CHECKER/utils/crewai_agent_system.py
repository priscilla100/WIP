"""
CrewAI Multi-Agent System for HIPAA Compliance Verification
============================================================

Architecture:
- Agent 1: Fact Extractor (parses natural language to structured facts)
- Agent 2: Logic Translator (converts to formal logic)
- Agent 3: Compliance Verifier (calls OCaml Précis engine)
- Agent 4: Explanation Generator (creates human-readable output)
- Agent 5: Validator (checks facts and formulas for correctness)

Each agent has:
- Role, Goal, Backstory (for context)
- Tools (custom functions they can use)
- Memory (remembers previous interactions)
"""

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
import anthropic
import time
import json
import subprocess
import re
from typing import List, Dict, Optional

# ============================================
# CUSTOM TOOLS FOR AGENTS
# ============================================

@tool("fact_validator")
def validate_fact_structure(fact: str) -> str:
    """
    Validates if a fact has correct predicate and arity.
    Input: String like "coveredEntity(Hospital1)" or JSON ["coveredEntity", "Hospital1"]
    Output: Validation result
    """
    
    ARITY_MAP = {
        'coveredEntity': 1,
        'protectedHealthInfo': 1,
        'publicHealthAuthority': 1,
        'hasAuthorization': 3,
        'requiredByLaw': 1,
        'disclose': 4,
        'permittedUseOrDisclosure': 4
    }
    
    try:
        # Parse fact
        if isinstance(fact, str):
            if fact.startswith('['):
                fact_list = json.loads(fact)
            else:
                # Parse "predicate(arg1, arg2)"
                match = re.match(r'(\w+)\((.*)\)', fact)
                if not match:
                    return f"❌ Invalid format: {fact}"
                pred = match.group(1)
                args = [a.strip() for a in match.group(2).split(',')]
                fact_list = [pred] + args
        else:
            fact_list = fact
        
        predicate = fact_list[0]
        args = fact_list[1:]
        
        # Check predicate exists
        if predicate not in ARITY_MAP:
            return f"❌ Unknown predicate: {predicate}"
        
        # Check arity
        expected = ARITY_MAP[predicate]
        if len(args) != expected:
            return f"❌ {predicate} expects {expected} args, got {len(args)}"
        
        return f"✅ Valid: {predicate} with {len(args)} arguments"
    
    except Exception as e:
        return f"❌ Validation error: {str(e)}"


@tool("formula_checker")
def check_formula_syntax(formula: str) -> str:
    """
    Checks if a first-order logic formula has correct syntax.
    Verifies quantifiers, predicates, and variable bindings.
    """
    
    try:
        # Check for quantifier
        if not formula.strip().startswith('forall'):
            return "⚠️ Formula should start with 'forall' quantifier"
        
        # Extract declared variables
        forall_part = formula.split('.')[0]
        var_str = forall_part.replace('forall', '').strip()
        declared_vars = set(v.strip() for v in var_str.split(','))
        
        # Find all variables in formula body
        body = '.'.join(formula.split('.')[1:])
        all_vars = set(re.findall(r'\b([a-z_][a-z0-9_]*)\b', body))
        
        # Remove keywords
        keywords = {'and', 'or', 'implies', 'not', 'true', 'false', 'iff', 'xor'}
        predicates = {'coveredEntity', 'protectedHealthInfo', 'disclose', 
                     'permittedUseOrDisclosure', 'hasAuthorization', 'requiredByLaw',
                     'publicHealthAuthority'}
        
        used_vars = all_vars - keywords - {p.lower() for p in predicates}
        
        # Check for unbound variables
        unbound = used_vars - declared_vars
        if unbound:
            return f"❌ Unbound variables: {unbound}"
        
        return f"✅ Formula syntax valid. Variables: {declared_vars}"
    
    except Exception as e:
        return f"❌ Syntax check error: {str(e)}"


@tool("precis_engine")
def call_precis_verifier(formula: str, facts_json: str) -> str:
    """
    Calls the OCaml Précis verification engine.
    Input: formula (string), facts_json (JSON string of facts)
    Output: Verification result
    """
    
    PRECIS_PATH = "/Users/priscilladanso/Documents/STONYBROOK/RESEARCH/TOWARDDISSERTATION/WIP/REGULATORY_POLICY_CHECKER/precis"
    
    try:
        facts = json.loads(facts_json)
        
        # Wrap formula
        wrapped_formula = f"""regulation HIPAA version "1.0"
policy starts
{formula}
;
policy ends"""
        
        # Build request
        request = {
            "formula": wrapped_formula,
            "facts": {"facts": facts},
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
        
        if proc.returncode == 0:
            result = json.loads(output)
            return json.dumps(result, indent=2)
        else:
            return f"❌ Précis error: {error}"
    
    except Exception as e:
        return f"❌ Tool error: {str(e)}"


@tool("hipaa_knowledge_base")
def query_hipaa_rules(section: str) -> str:
    """
    Retrieves HIPAA rules for a specific section.
    Input: Section number like "164.502"
    Output: Rule description
    """
    
    knowledge_base = {
        "164.502": "Uses and disclosures of PHI: General rules. Covered entities must have authorization or meet specific conditions.",
        "164.506": "Uses and disclosures for treatment, payment, and healthcare operations.",
        "164.510": "Uses and disclosures requiring an opportunity for the individual to agree or object.",
        "164.512": "Uses and disclosures for which authorization or opportunity to agree or object is not required (public health, law enforcement, etc.)"
    }
    
    for key, value in knowledge_base.items():
        if key in section:
            return f"§{key}: {value}"
    
    return f"Section {section} not found in knowledge base."


# ============================================
# DEFINE AGENTS
# ============================================

def create_fact_extractor_agent(llm_config: dict) -> Agent:
    """Agent that extracts structured facts from natural language"""
    
    return Agent(
        role='Fact Extraction Specialist',
        goal='Extract accurate, structured facts from natural language compliance questions',
        backstory="""You are an expert at analyzing HIPAA compliance questions and 
        identifying the key entities, relationships, and predicates. You understand 
        medical terminology and can map real-world scenarios to formal predicates like 
        coveredEntity, protectedHealthInfo, disclose, hasAuthorization, etc.""",
        tools=[validate_fact_structure, hipaa_knowledge_base],
        verbose=True,
        allow_delegation=False,
        llm_config=llm_config
    )


def create_logic_translator_agent(llm_config: dict) -> Agent:
    """Agent that translates facts to formal logic"""
    
    return Agent(
        role='Logic Translation Expert',
        goal='Translate compliance questions into precise first-order logic formulas',
        backstory="""You are a formal methods expert specializing in first-order logic 
        and temporal logic. You know how to express HIPAA compliance rules as logical 
        formulas with proper quantification, predicates, and implications.""",
        tools=[check_formula_syntax],
        verbose=True,
        allow_delegation=False,
        llm_config=llm_config
    )


def create_validator_agent(llm_config: dict) -> Agent:
    """Agent that validates facts and formulas before verification"""
    
    return Agent(
        role='Validation Specialist',
        goal='Ensure all facts and formulas are correct before verification',
        backstory="""You are a meticulous validator who checks that all predicates 
        have correct arity, all variables are bound, and formulas follow proper syntax. 
        You catch errors before they reach the verification engine.""",
        tools=[validate_fact_structure, check_formula_syntax],
        verbose=True,
        allow_delegation=False,
        llm_config=llm_config
    )


def create_verifier_agent(llm_config: dict) -> Agent:
    """Agent that calls the OCaml verification engine"""
    
    return Agent(
        role='Formal Verification Engineer',
        goal='Execute formal verification using the OCaml Précis engine',
        backstory="""You operate the formal verification engine, translating validated 
        facts and formulas into the exact format required by the OCaml system and 
        interpreting the results.""",
        tools=[precis_engine],
        verbose=True,
        allow_delegation=False,
        llm_config=llm_config
    )


def create_explainer_agent(llm_config: dict) -> Agent:
    """Agent that generates human-readable explanations"""
    
    return Agent(
        role='Compliance Communication Specialist',
        goal='Explain verification results in clear, actionable language',
        backstory="""You translate technical verification results into clear guidance 
        for healthcare professionals. You cite specific HIPAA sections and provide 
        practical next steps.""",
        tools=[hipaa_knowledge_base],
        verbose=True,
        allow_delegation=False,
        llm_config=llm_config
    )


# ============================================
# DEFINE TASKS
# ============================================

def create_extraction_task(agent: Agent, query: str) -> Task:
    return Task(
        description=f"""Extract structured facts from this compliance question:
        
        Question: {query}
        
        Identify:
        1. Covered entities (hospitals, clinics, providers)
        2. Protected health information (records, x-rays, lab results)
        3. Recipients (who receives the data)
        4. Actions (disclose, share, transfer)
        5. Purposes (@Treatment, @Research, @PublicHealth, etc.)
        6. Authorization status (hasAuthorization, requiredByLaw)
        7. Permitted uses (permittedUseOrDisclosure)
        
        Output MUST be valid JSON:
        {{
            "facts": [
                ["predicate", "arg1", "arg2", ...],
                ...
            ]
        }}
        
        Use the fact_validator tool to check each fact before including it.""",
        agent=agent,
        expected_output="JSON object containing validated facts list"
    )


def create_translation_task(agent: Agent, extraction_task: Task) -> Task:
    return Task(
        description="""Translate the extracted facts into a first-order logic formula.
        
        Use this exact template:
        forall ce, recipient, phi, purpose.
          (coveredEntity(ce)
           and protectedHealthInfo(phi)
           and disclose(ce, recipient, phi, purpose))
          implies
          (permittedUseOrDisclosure(ce, recipient, phi, purpose)
           or hasAuthorization(ce, recipient, phi)
           or requiredByLaw(purpose))
        
        CRITICAL RULES:
        - ALL variables in formula body MUST appear in forall clause
        - NO equality checks on purpose (no "purpose = @Treatment")
        - NO purposeIsPurpose predicate
        - Use ONLY predicates: coveredEntity, protectedHealthInfo, disclose, 
          permittedUseOrDisclosure, hasAuthorization, requiredByLaw
        
        Use the check_formula_syntax tool to validate before finalizing.""",
        agent=agent,
        expected_output="Valid first-order logic formula string",
        context=[extraction_task]
    )


def create_validation_task(agent: Agent, extraction_task: Task, translation_task: Task) -> Task:
    return Task(
        description="""Validate that facts and formula are ready for verification.
        
        Check:
        1. All facts have correct predicate names and arity
        2. Formula has all variables bound in forall clause
        3. No syntax errors
        4. Facts align with formula (entities match, predicates used correctly)
        
        If errors found, provide specific fixes needed.
        If validation passes, output: "✅ VALIDATION PASSED"
        
        Use both fact_validator and formula_checker tools.""",
        agent=agent,
        expected_output="Validation report with pass/fail status and any corrections needed",
        context=[extraction_task, translation_task]
    )


def create_verification_task(agent: Agent, extraction_task: Task, translation_task: Task, validation_task: Task) -> Task:
    return Task(
        description="""Execute formal verification using the OCaml Précis engine.
        
        Take the validated facts and formula and call the precis_engine tool.
        
        Input format for precis_engine:
        - formula: the first-order logic formula string
        - facts_json: JSON string of facts array
        
        Parse the OCaml output to determine:
        - Whether verification PASSED or FAILED
        - Which policies were checked
        - Any violations found
        
        Return structured verification result.""",
        agent=agent,
        expected_output="Structured verification result with pass/fail status and details",
        context=[extraction_task, translation_task, validation_task]
    )


def create_explanation_task(agent: Agent, query: str, verification_task: Task) -> Task:
    return Task(
        description=f"""Generate a clear explanation of the verification result.
        
        Original question: {query}
        
        Provide:
        1. Direct YES/NO answer to the user's question
        2. Brief explanation (2-3 sentences) of why
        3. Specific HIPAA section citation (use hipaa_knowledge_base tool)
        4. Actionable next steps if violation found
        
        Keep language simple and non-technical.""",
        agent=agent,
        expected_output="Human-readable explanation with answer, reasoning, citation, and guidance",
        context=[verification_task]
    )


# ============================================
# CREWAI SYSTEM ORCHESTRATION
# ============================================

def crewai_agentic_system(query: str, anthropic_client) -> dict:
    """
    Complete multi-agent system for HIPAA compliance verification
    """
    
    start_time = time.time()
    steps = []
    
    try:
        # Configure LLM for agents (using Claude via Anthropic)
        llm_config = {
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.1,
            "api_key": anthropic_client.api_key
        }
        
        steps.append("🤖 Initializing multi-agent system...")
        
        # Create agents
        fact_extractor = create_fact_extractor_agent(llm_config)
        logic_translator = create_logic_translator_agent(llm_config)
        validator = create_validator_agent(llm_config)
        verifier = create_verifier_agent(llm_config)
        explainer = create_explainer_agent(llm_config)
        
        steps.append("✅ Agents created: Extractor, Translator, Validator, Verifier, Explainer")
        
        # Create tasks
        extraction_task = create_extraction_task(fact_extractor, query)
        translation_task = create_translation_task(logic_translator, extraction_task)
        validation_task = create_validation_task(validator, extraction_task, translation_task)
        verification_task = create_verification_task(verifier, extraction_task, translation_task, validation_task)
        explanation_task = create_explanation_task(explainer, query, verification_task)
        
        steps.append("✅ Tasks defined: Extract → Translate → Validate → Verify → Explain")
        
        # Create crew with hierarchical process
        crew = Crew(
            agents=[fact_extractor, logic_translator, validator, verifier, explainer],
            tasks=[extraction_task, translation_task, validation_task, verification_task, explanation_task],
            process=Process.sequential,  # Execute tasks in order
            verbose=True
        )
        
        steps.append("⚙️ Executing crew workflow...")
        
        # Execute crew
        result = crew.kickoff()
        
        steps.append("✅ Crew execution complete")
        
        # Parse results
        # Extract facts from extraction task
        extracted_facts = []
        try:
            facts_match = re.search(r'\{.*"facts".*\}', str(extraction_task.output), re.DOTALL)
            if facts_match:
                facts_json = json.loads(facts_match.group())
                extracted_facts = facts_json.get('facts', [])
        except:
            pass
        
        # Extract formula from translation task
        formula = str(translation_task.output).strip()
        
        # Extract verification result
        verification_output = str(verification_task.output)
        verified = "PASSED" in verification_output or "true" in verification_output
        
        # Get explanation
        explanation = str(explanation_task.output)
        
        return {
            "name": "CrewAI Agentic System 🤖",
            "answer": explanation,
            "duration": time.time() - start_time,
            "steps": steps,
            "extracted_facts": extracted_facts,
            "formula": formula,
            "verified": verified,
            "method": "Multi-Agent System (5 agents: Extract → Translate → Validate → Verify → Explain)",
            "compliance_status": "✅ COMPLIANT" if verified else "❌ VIOLATION",
            "agent_outputs": {
                "extraction": str(extraction_task.output),
                "translation": str(translation_task.output),
                "validation": str(validation_task.output),
                "verification": verification_output,
                "explanation": explanation
            }
        }
    
    except Exception as e:
        steps.append(f"❌ Error: {str(e)}")
        return {
            "name": "CrewAI Agentic System 🤖",
            "answer": f"Error in agent system: {str(e)}",
            "duration": time.time() - start_time,
            "steps": steps,
            "extracted_facts": [],
            "formula": "",
            "verified": False,
            "method": "Multi-Agent System (Failed)",
            "compliance_status": "❌ ERROR"
        }


# ============================================
# USAGE
# ============================================

# if __name__ == "__main__":
#     from anthropic import Anthropic
    
#     client = Anthropic(api_key="your-key-here")
    
#     query = "Can a hospital share patient data with researchers?"
#     result = crewai_agentic_system(query, client)
    
#     print(json.dumps(result, indent=2))