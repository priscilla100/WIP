# agentic.py - Enhanced CrewAI Agentic System

from crewai import Agent, Task, Crew, Process
from typing import Dict, List, Any, Optional
import json
import re

# ---------------------------
# Tool Wrappers - Use Baseline Utils Directly
# ---------------------------

# The agentic system uses the EXACT SAME utility functions as baseline.
# These wrappers just make them available to CrewAI agents.

def tool_extract_atomic_propositions(nl_req: str, claude_helper) -> tuple:
    """
    Extract atomic propositions using Claude API
    Returns: (aps: List[str], explanation: str)
    """
    prompt = f"""Extract atomic propositions from this requirement using maximal logical revelation.

Requirement: {nl_req}

List each atomic proposition and provide a brief explanation.

Format:
APs: prop1, prop2, prop3
Explanation: Brief description of the extraction logic."""

    response = claude_helper.client.messages.create(
        model=claude_helper.model,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    content = response.content[0].text.strip()
    
    # Parse response
    aps = []
    explanation = ""
    
    for line in content.split('\n'):
        if line.startswith('APs:'):
            aps_str = line.replace('APs:', '').strip()
            aps = [ap.strip() for ap in aps_str.split(',')]
        elif line.startswith('Explanation:'):
            explanation = line.replace('Explanation:', '').strip()
    
    return aps, explanation

def tool_generate_ltl_detailed(nl_req: str, aps: List[str], claude_helper) -> tuple:
    """
    Generate detailed LTL formula
    Returns: (formula: str, explanation: str)
    """
    prompt = f"""Generate a detailed LTL formula for this requirement.

Requirement: {nl_req}
Atomic Propositions: {', '.join(aps)}

Use standard LTL operators: G, F, X, U, ->, &, |, !
Provide the formula and a brief explanation.

Format:
FORMULA: <your formula>
EXPLANATION: <brief explanation>"""

    response = claude_helper.client.messages.create(
        model=claude_helper.model,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    content = response.content[0].text.strip()
    
    formula = ""
    explanation = ""
    
    for line in content.split('\n'):
        if line.startswith('FORMULA:'):
            formula = line.replace('FORMULA:', '').strip()
        elif line.startswith('EXPLANATION:'):
            explanation = line.replace('EXPLANATION:', '').strip()
    
    if not formula:
        formula = content.split('\n')[0]
    
    return formula, explanation

def tool_generate_ltl_python(nl_req: str, aps: List[str], claude_helper) -> tuple:
    """
    Generate Python-style LTL formula
    Returns: (formula: str, explanation: str)
    """
    prompt = f"""Generate a Python-style LTL formula for this requirement.

Requirement: {nl_req}
Atomic Propositions: {', '.join(aps)}

Use Python operators: and, or, not, ->, G(), F(), X(), U()
Provide the formula and a brief explanation.

Format:
FORMULA: <your formula>
EXPLANATION: <brief explanation>"""

    response = claude_helper.client.messages.create(
        model=claude_helper.model,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    content = response.content[0].text.strip()
    
    formula = ""
    explanation = ""
    
    for line in content.split('\n'):
        if line.startswith('FORMULA:'):
            formula = line.replace('FORMULA:', '').strip()
        elif line.startswith('EXPLANATION:'):
            explanation = line.replace('EXPLANATION:', '').strip()
    
    if not formula:
        formula = content.split('\n')[0]
    
    return formula, explanation

def tool_generate_constraint_traces(formulas: Dict[str, str], aps: List[str]) -> Dict[str, Any]:
    """
    Generate 2² constraint traces using baseline utility functions
    
    This is EXACTLY what baseline Step 3 does:
    1. Use CONSTRAINTS to get 4 combinations
    2. Build constraint formula for each
    3. Generate NuSMV model
    4. Run NuSMV
    5. Parse trace to canonical format
    """
    # Import baseline utilities
    from utils import (
        CONSTRAINTS,
        build_constraint_formula,
        generate_nusmv_model,
        run_nusmv,
        nusmv_trace_to_canonical
    )
    
    constraint_traces = {}
    
    # Use the exact same CONSTRAINTS dict as baseline
    for name, flags in CONSTRAINTS.items():
        # Build constraint formula (baseline function)
        constraint = build_constraint_formula(
            formulas["D"],
            formulas["P"],
            flags
        )
        
        # Generate NuSMV model (baseline function)
        nusmv_input = generate_nusmv_model(constraint, aps)
        
        # Run NuSMV (baseline function)
        result = run_nusmv(nusmv_input)
        
        # Parse trace to canonical format (baseline function)
        # This returns None if UNSAT
        canonical_trace = nusmv_trace_to_canonical(result["raw"], aps)
        
        # Store with same structure as baseline
        constraint_traces[name] = {
            "constraint_formula": constraint,
            "nusmv_input": nusmv_input,
            "trace": canonical_trace,  # This is None for UNSAT
            "raw_output": result["raw"],
            "satisfiable": result["satisfiable"]  # This is the key flag!
        }
    
    return constraint_traces

def tool_semantic_evaluation(trace: Optional[str], nl_req: str, claude_helper) -> Dict[str, Any]:
    """
    Get LLM semantic evaluation of trace
    Uses the same logic as baseline Step 4
    """
    if trace is None:
        return {
            "should_satisfy": True,
            "reasoning": "UNSAT region — vacuously satisfies the requirement."
        }
    
    # Use the claude_helper method directly (same as baseline)
    return claude_helper.get_trace_feedback(trace, nl_req)

def tool_syslite_synthesize(pos_traces: List[str], neg_traces: List[str], aps: List[str]) -> List[str]:
    """
    Synthesize formulas using SySLite
    Uses baseline utilities for trace conversion
    """
    from utils import SySLiteWrapper, convert_ast_to_standard_ltl, trace_to_syslite_format
    
    if not pos_traces or not neg_traces:
        return []
    
    # Convert traces to SySLite format (baseline function)
    pos_syslite = [trace_to_syslite_format(t, aps) for t in pos_traces]
    neg_syslite = [trace_to_syslite_format(t, aps) for t in neg_traces]
    
    # Run SySLite (baseline function)
    syslite = SySLiteWrapper()
    formulas, debug, trace_file = syslite.synthesize(pos_syslite, neg_syslite, aps, size=5)
    
    # Convert to standard LTL (baseline function)
    std_formulas = [convert_ast_to_standard_ltl(f) for f in formulas]
    return std_formulas

def tool_llm_repair(formula_name: str, formula: str, misalignments: List[Dict], 
                    nl_req: str, aps: List[str], claude_helper) -> str:
    """
    Use LLM to repair formula based on misalignments
    Same approach as baseline Step 5 LLM re-prompting
    """
    mismatch_info = []
    for m in misalignments:
        if m["formula"] == formula_name:
            feedback = "SHOULD satisfy" if m["expected"] else "should NOT satisfy"
            trace_snippet = m["trace"][:80] + "..." if m["trace"] else "UNSAT"
            mismatch_info.append(f"{m['constraint']}: {trace_snippet} → {feedback}")
    
    if not mismatch_info:
        return formula
    
    prompt = f"""The current formula doesn't match user intent.

Requirement: {nl_req}
APs: {', '.join(aps)}

Current formula ({formula_name}): {formula}

User feedback on traces:
{chr(10).join(mismatch_info)}

Generate a NEW LTL formula that matches these expectations.
Use: G, F, X, U, ->, &, |, !

Return ONLY the formula."""
    
    response = claude_helper.client.messages.create(
        model=claude_helper.model,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    refined = response.content[0].text.strip()
    # Clean up markdown (same as baseline)
    refined = re.sub(r'```.*?\n|```', '', refined).strip()
    
    return refined

# ---------------------------
# Enhanced Agent Definitions
# ---------------------------

def create_formalization_agent():
    """Agent responsible for initial LTL generation"""
    return Agent(
        role="LTL Formalization Specialist",
        goal="Generate accurate LTL formulas from natural language requirements",
        backstory="""You are an expert in formal methods and temporal logic. 
        Your specialty is translating natural language requirements into precise 
        LTL (Linear Temporal Logic) formulas. You understand both detailed 
        spot-compatible syntax and Python-style operator syntax.""",
        verbose=True,
        memory=True,
        allow_delegation=False
    )

def create_verification_agent():
    """Agent responsible for verification and semantic evaluation"""
    return Agent(
        role="Formal Verification Engineer",
        goal="Verify LTL formulas against traces and identify semantic misalignments",
        backstory="""You are a verification expert who checks whether formal 
        specifications correctly capture intended behavior. You use model checking 
        and semantic analysis to identify discrepancies between formulas and 
        requirements.""",
        verbose=True,
        memory=True,
        allow_delegation=False
    )

def create_repair_agent():
    """Agent responsible for formula repair"""
    return Agent(
        role="Formula Repair Specialist",
        goal="Fix misaligned formulas using synthesis and LLM-guided repair",
        backstory="""You are an expert in automated program synthesis and repair. 
        You use both data-driven synthesis (SySLite) and LLM-guided refinement 
        to fix formulas that don't match their intended semantics.""",
        verbose=True,
        memory=True,
        allow_delegation=False
    )

def create_orchestration_agent():
    """Agent responsible for overall workflow coordination"""
    return Agent(
        role="Workflow Orchestrator",
        goal="Coordinate the formalization-verification-repair cycle efficiently",
        backstory="""You are a senior formal methods engineer who orchestrates 
        complex verification workflows. You decide when to continue repair attempts, 
        when to accept results, and when to escalate to human review.""",
        verbose=True,
        memory=True,
        allow_delegation=True
    )

# ---------------------------
# Enhanced Task Definitions
# ---------------------------

def create_formalization_task(agent: Agent, nl_req: str, claude_helper) -> Task:
    """Task: Generate candidate LTL formulas"""
    return Task(
        description=f"""Generate two candidate LTL formulas for this requirement:
        
        Requirement: {nl_req}
        
        Generate:
        1. A detailed spot-compatible formula
        2. A Python-style formula with operators like 'and', 'or', 'not'
        
        Also extract atomic propositions from the requirement.""",
        agent=agent,
        expected_output="Dictionary with 'detailed_formula', 'python_formula', and 'aps'",
        context={
            "nl_req": nl_req,
            "claude_helper": claude_helper
        }
    )

def create_trace_generation_task(agent: Agent, formulas: Dict[str, str], aps: List[str]) -> Task:
    """Task: Generate truth table traces"""
    return Task(
        description=f"""Generate truth table traces for formula comparison.
        
        Formulas to evaluate:
        {json.dumps(formulas, indent=2)}
        
        Atomic Propositions: {', '.join(aps)}
        
        Generate 2^n constraint traces covering all combinations.""",
        agent=agent,
        expected_output="Dictionary of constraint traces with satisfiability info",
        context={
            "formulas": formulas,
            "aps": aps
        }
    )

def create_semantic_evaluation_task(agent: Agent, traces: Dict, nl_req: str, claude_helper) -> Task:
    """Task: Evaluate traces semantically"""
    return Task(
        description=f"""Evaluate each trace semantically against the requirement:
        
        Requirement: {nl_req}
        
        For each trace, determine:
        1. Should this trace satisfy the requirement? (Ground Truth)
        2. Does each formula (D, P) correctly classify it?
        3. Identify misalignments
        
        Provide reasoning for each evaluation.""",
        agent=agent,
        expected_output="Dictionary with ground truth and misalignment analysis",
        context={
            "traces": traces,
            "nl_req": nl_req,
            "claude_helper": claude_helper
        }
    )

def create_repair_task(agent: Agent, misalignments: List[Dict], formulas: Dict, 
                       traces: Dict, aps: List[str], nl_req: str, claude_helper) -> Task:
    """Task: Repair misaligned formulas"""
    return Task(
        description=f"""Repair the misaligned formulas using available techniques:
        
        Identified Misalignments:
        {json.dumps(misalignments, indent=2)}
        
        Techniques available:
        1. SySLite synthesis (data-driven from positive/negative traces)
        2. LLM-guided repair (feedback-based refinement)
        
        Choose the best approach and generate refined formulas.""",
        agent=agent,
        expected_output="List of refined formulas with metadata",
        context={
            "misalignments": misalignments,
            "formulas": formulas,
            "traces": traces,
            "aps": aps,
            "nl_req": nl_req,
            "claude_helper": claude_helper
        }
    )

def create_orchestration_task(agent: Agent, workflow_state: Dict) -> Task:
    """Task: Orchestrate overall workflow"""
    return Task(
        description=f"""Orchestrate the verification workflow:
        
        Current State:
        - Formulas generated: {workflow_state.get('formulas_ready', False)}
        - Traces generated: {workflow_state.get('traces_ready', False)}
        - Semantic evaluation done: {workflow_state.get('eval_done', False)}
        - Misalignments found: {workflow_state.get('has_misalignments', False)}
        - Repair attempts: {workflow_state.get('repair_attempts', 0)}
        
        Decide next action:
        - Continue to next step
        - Trigger repair
        - Accept current result
        - Escalate to human review""",
        agent=agent,
        expected_output="Decision on next workflow action",
        context=workflow_state
    )

# ---------------------------
# Main Agentic Pipeline
# ---------------------------

def run_agentic_pipeline(nl_req: str, claude_helper, max_repair_attempts: int = 3) -> Dict[str, Any]:
    """
    Run the complete agentic formalization-verification-repair pipeline
    Matches the baseline workflow exactly through Step 7
    
    Returns:
        Dictionary containing all workflow results
    """
    from utils import CONSTRAINTS, generate_truth_table_constraints, generate_nusmv_model, run_nusmv, nusmv_trace_to_canonical
    
    execution_log = []
    
    # ========================================
    # Step 1: Atomic Proposition Extraction
    # ========================================
    execution_log.append({"step": "ap_extraction", "status": "started"})
    
    aps, aps_explanation = tool_extract_atomic_propositions(nl_req, claude_helper)
    
    execution_log.append({
        "step": "ap_extraction",
        "status": "completed",
        "aps": aps,
        "explanation": aps_explanation
    })
    
    # ========================================
    # Step 2: Formula Generation (D & P)
    # ========================================
    execution_log.append({"step": "formula_generation", "status": "started"})
    
    detailed_formula, detailed_explanation = tool_generate_ltl_detailed(nl_req, aps, claude_helper)
    python_formula, python_explanation = tool_generate_ltl_python(nl_req, aps, claude_helper)
    
    formulas = {
        "D": detailed_formula,
        "P": python_formula
    }
    
    execution_log.append({
        "step": "formula_generation",
        "status": "completed",
        "formulas": formulas,
        "detailed_explanation": detailed_explanation,
        "python_explanation": python_explanation
    })
    
    # ========================================
    # Step 3: Constraint Trace Generation (2²)
    # ========================================
    execution_log.append({"step": "trace_generation", "status": "started"})
    
    constraint_traces = tool_generate_constraint_traces(formulas, aps)
    
    execution_log.append({
        "step": "trace_generation",
        "status": "completed",
        "num_traces": len(constraint_traces),
        "traces": list(constraint_traces.keys())
    })
    
    # ========================================
    # Step 4: Semantic Evaluation
    # ========================================
    execution_log.append({"step": "semantic_evaluation", "status": "started"})
    
    semantic_oracle = {}
    semantic_ground_truth = {}
    
    for cname, trace_data in constraint_traces.items():
        trace = trace_data.get("trace")
        
        # Get LLM evaluation
        oracle = tool_semantic_evaluation(trace, nl_req, claude_helper)
        semantic_oracle[cname] = oracle
        
        # Initialize ground truth to LLM judgment
        semantic_ground_truth[cname] = oracle["should_satisfy"]
    
    # Check alignment - MATCH BASELINE EXACTLY
    misalignments = []
    for cname, trace_data in constraint_traces.items():
        flags = CONSTRAINTS[cname]
        
        # This is what baseline does - just check the flags
        # negate_D=False means we're testing D (positive)
        # negate_D=True means we're testing !D (negative)
        d_satisfies = not flags["negate_D"]
        p_satisfies = not flags["negate_P"]
        gt = semantic_ground_truth[cname]
        
        if d_satisfies != gt:
            misalignments.append({
                "constraint": cname,
                "formula": "D",
                "expected": gt,
                "actual": d_satisfies,
                "trace": trace_data.get("trace")
            })
        
        if p_satisfies != gt:
            misalignments.append({
                "constraint": cname,
                "formula": "P",
                "expected": gt,
                "actual": p_satisfies,
                "trace": trace_data.get("trace")
            })
    
    execution_log.append({
        "step": "semantic_evaluation",
        "status": "completed",
        "num_misalignments": len(misalignments),
        "misalignments_summary": f"D: {sum(1 for m in misalignments if m['formula'] == 'D')}, P: {sum(1 for m in misalignments if m['formula'] == 'P')}"
    })
    
    # ========================================
    # Step 5: Repair (if needed)
    # ========================================
    refined_formulas = []
    repair_attempts = 0
    
    if misalignments and repair_attempts < max_repair_attempts:
        execution_log.append({"step": "repair", "status": "started"})
        
        # Categorize traces for SySLite
        pos_traces = []
        neg_traces = []
        
        for cname, trace_data in constraint_traces.items():
            trace = trace_data.get("trace")
            if trace and semantic_ground_truth[cname]:
                pos_traces.append(trace)
            elif trace and not semantic_ground_truth[cname]:
                neg_traces.append(trace)
        
        # Try SySLite synthesis (if we have positive traces)
        syslite_formulas = []
        if pos_traces and neg_traces:
            try:
                syslite_formulas = tool_syslite_synthesize(pos_traces, neg_traces, aps)
                for formula in syslite_formulas[:3]:  # Limit to top 3
                    refined_formulas.append({
                        "method": "SySLite",
                        "formula": formula
                    })
            except Exception as e:
                execution_log.append({
                    "step": "repair_syslite",
                    "status": "failed",
                    "error": str(e)
                })
        
        # Try LLM repair for each misaligned formula
        for formula_name in ["D", "P"]:
            formula_misalignments = [m for m in misalignments if m["formula"] == formula_name]
            if formula_misalignments:
                try:
                    repaired = tool_llm_repair(
                        formula_name,
                        formulas[formula_name],
                        formula_misalignments,
                        nl_req,
                        aps,
                        claude_helper
                    )
                    refined_formulas.append({
                        "method": "LLM",
                        "formula": repaired,
                        "original": formula_name
                    })
                except Exception as e:
                    execution_log.append({
                        "step": f"repair_llm_{formula_name}",
                        "status": "failed",
                        "error": str(e)
                    })
        
        repair_attempts += 1
        
        execution_log.append({
            "step": "repair",
            "status": "completed",
            "num_refined": len(refined_formulas),
            "refined_formulas": refined_formulas,
            "syslite_count": len(syslite_formulas),
            "llm_count": len(refined_formulas) - len(syslite_formulas)
        })
    
    # ========================================
    # Step 6: Reintegration (auto-select best refined formula)
    # ========================================
    reintegrated_traces = None
    selected_refined_formula = None
    
    if refined_formulas:
        execution_log.append({"step": "reintegration", "status": "started"})
        
        # Auto-select first refined formula (agents decide: prefer SySLite over LLM)
        selected_refined_formula = refined_formulas[0]
        
        # Generate 2³ traces for D, P, R
        formulas_with_r = {
            "D": detailed_formula,
            "P": python_formula,
            "R": selected_refined_formula["formula"]
        }
        
        # Use generate_truth_table_constraints for 2³ combinations
        constraints_2_3 = generate_truth_table_constraints(formulas_with_r, max_formulas=3)
        reintegrated_traces = {}
        
        for c in constraints_2_3:
            nusmv = generate_nusmv_model(c["formula"], aps)
            result = run_nusmv(nusmv)
            trace = nusmv_trace_to_canonical(result["raw"], aps)
            
            reintegrated_traces[c["name"]] = {
                "constraint_formula": c["formula"],
                "trace": trace,
                "satisfiable": result["satisfiable"],
                "negation_flags": c["negation_flags"]
            }
        
        execution_log.append({
            "step": "reintegration",
            "status": "completed",
            "selected_formula": selected_refined_formula,
            "num_traces": len(reintegrated_traces)
        })
    
    # ========================================
    # Step 7: Re-evaluation (if reintegration done)
    # ========================================
    reevaluation_results = None
    
    if reintegrated_traces:
        execution_log.append({"step": "reevaluation", "status": "started"})
        
        # Evaluate R formula alignment
        r_misalignments = []
        
        for cname, art in reintegrated_traces.items():
            trace = art.get("trace")
            flags = art.get("negation_flags", {})
            
            # Get ground truth (reuse from Step 4 or get new)
            if trace is None:
                gt = True
            else:
                # Reuse semantic oracle if constraint exists, otherwise evaluate
                if cname in semantic_oracle:
                    gt = semantic_oracle[cname]["should_satisfy"]
                else:
                    oracle = tool_semantic_evaluation(trace, nl_req, claude_helper)
                    semantic_oracle[cname] = oracle
                    gt = oracle["should_satisfy"]
                    semantic_ground_truth[cname] = gt
            
            # Check R alignment
            r_satisfies = not flags.get("R", True)
            if r_satisfies != gt:
                r_misalignments.append({
                    "constraint": cname,
                    "formula": "R",
                    "expected": gt,
                    "actual": r_satisfies,
                    "trace": trace
                })
        
        reevaluation_results = {
            "r_misalignments": r_misalignments,
            "r_aligned": len(r_misalignments) == 0
        }
        
        execution_log.append({
            "step": "reevaluation",
            "status": "completed",
            "r_aligned": reevaluation_results["r_aligned"],
            "num_r_misalignments": len(r_misalignments)
        })
    
    # Determine final status
    if reintegrated_traces and reevaluation_results and reevaluation_results["r_aligned"]:
        final_status = "fully_aligned"
    elif not misalignments:
        final_status = "aligned"
    elif refined_formulas:
        final_status = "partially_aligned"
    else:
        final_status = "needs_human_review"
    
    return {
        "nl_requirement": nl_req,
        "aps": aps,
        "aps_explanation": aps_explanation,
        "formulas": formulas,
        "formula_explanations": {
            "D": detailed_explanation,
            "P": python_explanation
        },
        "constraint_traces": constraint_traces,
        "semantic_oracle": semantic_oracle,
        "semantic_ground_truth": semantic_ground_truth,
        "misalignments": misalignments,
        "refined_formulas": refined_formulas,
        "selected_refined_formula": selected_refined_formula,
        "reintegrated_traces": reintegrated_traces,
        "reevaluation_results": reevaluation_results,
        "execution_log": execution_log,
        "final_status": final_status,
        "repair_attempts": repair_attempts
    }
