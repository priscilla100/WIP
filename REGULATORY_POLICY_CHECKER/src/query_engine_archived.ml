(* query_engine.ml - Match user queries to policies and evaluate *)
open Policy_databases
open Ast
open Type_checker
open Evaluator


type match_result = {
  policy: policy_entry;
  relevance_score: float;
  matched_terms: string list;
}

type evaluation_result = {
  policy_id: string;
  regulation: string;
  section: string;
  description: string;
  formula_text: string;
  evaluation: eval_result;
  explanation: string;
}

type query_response = {
  query_formula: formula;
  matched_policies: match_result list;
  evaluations: evaluation_result list;
  overall_compliant: bool;
  violations: string list;
}

(* Extract predicates from a formula *)
let rec extract_predicates (f: formula) : string list =
  match f with
  | True | False -> []
  | Predicate (name, _) -> [name]
  | Not f' -> extract_predicates f'
  | BinLogicalOp (_, f1, f2) -> extract_predicates f1 @ extract_predicates f2
  | BinTemporalOp (_, f1, f2, _) -> extract_predicates f1 @ extract_predicates f2
  | UnTemporalOp (_, f', _) -> extract_predicates f'
  | Quantified (_, f') -> extract_predicates f'
  | Annotated (f', _) -> extract_predicates f'

(* Calculate relevance score between two formulas based on shared predicates *)
let calculate_relevance (query_formula: formula) (policy_formula: formula) : (float * string list) =
  let query_preds = extract_predicates query_formula in
  let policy_preds = extract_predicates policy_formula in
  
  let unique_query = List.sort_uniq String.compare query_preds in
  let unique_policy = List.sort_uniq String.compare policy_preds in
  
  (* Find intersection *)
  let matched = List.filter (fun p -> List.mem p unique_policy) unique_query in
  
  (* Calculate Jaccard similarity *)
  let intersection_size = float_of_int (List.length matched) in
  let union_size = float_of_int (List.length (List.sort_uniq String.compare (unique_query @ unique_policy))) in
  
  let score = if union_size = 0.0 then 0.0 else intersection_size /. union_size in
  (score, matched)

(* Find relevant policies for a user query *)
let find_relevant_policies 
    (query_formula: formula) 
    (db: policy_database) 
    (min_score: float) : match_result list =
  
  List.filter_map (fun policy ->
    let (score, matched_terms) = calculate_relevance query_formula policy.formula in
    if score >= min_score then
      Some { policy; relevance_score = score; matched_terms }
    else
      None
  ) db.policies
  |> List.sort (fun a b -> compare b.relevance_score a.relevance_score)

(* Evaluate a policy against facts *)
let evaluate_policy
    (policy: policy_entry)
    (domain: domain_db)
    (facts: facts_db)
    (funcs: functions_db) : evaluation_result =
  
  let result = eval_formula [] domain facts funcs policy.formula in
  
  let formula_text = string_of_formula policy.formula in
  
  let explanation = match result with
    | True -> Printf.sprintf "Policy %s is satisfied by current facts" policy.id
    | False -> Printf.sprintf "Policy %s is VIOLATED by current facts" policy.id
  in
  
  {
    policy_id = policy.id;
    regulation = policy.regulation;
    section = policy.section;
    description = policy.description;
    formula_text;
    evaluation = result;
    explanation;
  }

(* Evaluate all matched policies *)
let evaluate_matched_policies
    (matched: match_result list)
    (domain: domain_db)
    (facts: facts_db)
    (funcs: functions_db) : evaluation_result list =
  
  List.map (fun m -> evaluate_policy m.policy domain facts funcs) matched


let process_query
    (query_formula: formula)
    (regulation_filter: string option)
    (domain: domain_db)
    (facts: facts_db)
    (funcs: functions_db)
    (env: type_environment) : query_response =
  
  (* Step 1: Type check query *)
  let type_check_result = typecheck_formula empty_context env query_formula in
  (match type_check_result with
   | Error e ->
       failwith (Printf.sprintf "Query type error: %s" (string_of_type_error e))
   | Ok () -> ());
  
  (* Step 2: Select policy database *)
  let db = match regulation_filter with
    | Some "HIPAA" -> get_hipaa_policies ()
    | Some "GDPR" -> get_gdpr_policies ()
    | Some "SOX" -> get_sox_policies ()
    | _ -> get_all_policy_databases ()
  in
  
  (* Step 3: Find relevant policies *)
  let matched_policies = find_relevant_policies query_formula db 0.1 in
  
  (* Step 4: Evaluate matched policies *)
  let evaluations = evaluate_matched_policies matched_policies domain facts funcs in
  
  (* Step 5: Determine overall compliance *)
  let violations = List.filter_map (fun eval ->
    match eval.evaluation with
    | False -> Some eval.policy_id
    | True -> None
  ) evaluations in
  
  let overall_compliant = List.length violations = 0 in
  
  {
    query_formula;
    matched_policies;
    evaluations;
    overall_compliant;
    violations;
  }


let format_query_response (response: query_response) : string =
  let buffer = Buffer.create 1024 in
  
  Buffer.add_string buffer "=== QUERY EVALUATION RESULTS ===\n\n";
  
  Buffer.add_string buffer (Printf.sprintf "Query Formula: %s\n\n" (string_of_formula response.query_formula));
  
  Buffer.add_string buffer (Printf.sprintf "Matched %d relevant policies\n\n" (List.length response.matched_policies));
  
  Buffer.add_string buffer "--- POLICY EVALUATIONS ---\n\n";
  List.iter (fun eval ->
    let status = match eval.evaluation with
      | True -> "✓ COMPLIANT"
      | False -> "✗ VIOLATION"
    in
    Buffer.add_string buffer (Printf.sprintf "[%s] %s (%s %s)\n" status eval.policy_id eval.regulation eval.section);
    Buffer.add_string buffer (Printf.sprintf "    Description: %s\n" eval.description);
    Buffer.add_string buffer (Printf.sprintf "    Formula: %s\n" eval.formula_text);
    Buffer.add_string buffer (Printf.sprintf "    %s\n\n" eval.explanation);
  ) response.evaluations;
  
  Buffer.add_string buffer "--- OVERALL RESULT ---\n";
  if response.overall_compliant then
    Buffer.add_string buffer "✓ ALL POLICIES SATISFIED - COMPLIANT\n"
  else begin
    Buffer.add_string buffer (Printf.sprintf "✗ %d VIOLATIONS FOUND\n" (List.length response.violations));
    List.iter (fun v ->
      Buffer.add_string buffer (Printf.sprintf "  - %s\n" v)
    ) response.violations
  end;
  
  Buffer.contents buffer


type inferred_fact = {
  predicate: string;
  args: string list;
  confidence: float;
}

(* Placeholder for fact inference - would be integrated with LLM *)
let infer_facts_from_question (question: string) : inferred_fact list =
  (* This is where LLM1 would convert natural language to facts *)
  (* For now, return empty list - facts come from user or database *)
  []


let query_hipaa = process_query
let query_gdpr = process_query
let query_all_regulations = process_query

let print_query_response = fun resp -> print_string (format_query_response resp)