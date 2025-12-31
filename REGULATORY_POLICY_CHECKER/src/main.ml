(* main.ml - Updated for data-driven architecture *)

open Ast
open Type_checker
open Evaluator

(* ============================================ *)
(* CONFIGURATION - NEW DATA-DRIVEN APPROACH    *)
(* ============================================ *)

let get_default_config () =
  (* Initialize from files instead of hardcoded data *)
  let runtime_env = Environment_config.Config.initialize () in
  (runtime_env.type_env, runtime_env.domain, runtime_env.facts, runtime_env.functions)

(* ============================================ *)
(* EVALUATION HELPERS                          *)
(* ============================================ *)

let eval_policy (domain: domain_db) (facts: facts_db) (funcs: functions_db) (formulas: formula list) =
  List.map (fun f -> Evaluator.eval_formula [] domain facts funcs f) formulas

let print_eval_results results =
  Printf.printf "  [STEP 4] Evaluation Results:\n";
  List.iteri (fun idx result ->
    let status = match result with
      | Evaluator.True -> "✅ TRUE"
      | Evaluator.False -> "❌ FALSE"
    in
    Printf.printf "    Formula %d: %s\n" (idx + 1) status
  ) results

(* ============================================ *)
(* INPUT PROCESSING                            *)
(* ============================================ *)

let process_input input env domain facts funcs =
  match Parser.main Lexer.read (Lexing.from_string input) with
  | exception e -> 
      Printf.printf "  [ERROR] Parsing Failed: %s\n" (Printexc.to_string e);
      ()
  | ast ->
      Printf.printf "  [STEP 1] Parsing successful (AST created). ✅\n";
      
      (* Convert Ast.type_environment to Type_checker.type_environment *)
      let checker_env = Type_checker.ast_env_to_checker_env env in
      match Type_checker.typecheck_policy_file ast checker_env with
      | Error errors ->
          Printf.printf "  [ERROR] Type Check Failed: %d error(s) found. ❌\n" (List.length errors);
          List.iter (fun e -> 
            Printf.printf "    - %s\n" (Type_checker.string_of_type_error e)
          ) errors
      | Ok () ->
          Printf.printf "  [STEP 2] Type Check successful (Well-Typed). ✅\n";
          Printf.printf "  [STEP 2.5] Formula Translation:\n";
          List.iteri (fun idx f ->
            Printf.printf "    Formula %d: %s\n" (idx + 1) (Ast.string_of_formula f)
          ) ast.policies;
          
          Printf.printf "  [STEP 3] Evaluating formulas...\n";
          let results = eval_policy domain facts funcs ast.policies in
          print_eval_results results;
          Printf.printf "  [SUCCESS] Full pipeline complete.\n"

(* ============================================ *)
(* JSON MODE FOR PYTHON INTEGRATION            *)
(* ============================================ *)

let run_json_mode (runtime_env: Environment_config.Config.runtime_environment) : unit =
  Json_interface.run_stdio_mode runtime_env

(* ============================================ *)
(* FILE PROCESSING MODE                        *)
(* ============================================ *)

let run_file_mode filename =
  Printf.printf "Processing file: %s\n\n" filename;
  try
    let ic = open_in filename in
    let input = really_input_string ic (in_channel_length ic) in
    close_in ic;
    
    (* Use default configuration *)
    let (env, domain, facts, funcs) = get_default_config () in
    process_input input env domain facts funcs
  with
    | Sys_error msg -> Printf.printf "Error reading file: %s\n" msg

(* ============================================ *)
(* QUERY MODE - NEW!                           *)
(* ============================================ *)

let run_query_mode query_string regulation_filter =
  Printf.printf "=== QUERY MODE ===\n\n";
  
  (* Initialize runtime environment *)
  let runtime_env = Environment_config.Config.initialize () in
  
  (* Parse query formula *)
  try
    let query_formula = Parser.main Lexer.read (Lexing.from_string query_string) in
    let query_formula_single = List.hd query_formula.policies in
    
    Printf.printf "Query: %s\n\n" (Ast.string_of_formula query_formula_single);
    
    (* Process query *)
    let response = Query_engine.process_query_with_env 
      query_formula_single 
      regulation_filter 
      runtime_env 
    in
    
    (* Print results *)
    Query_engine.print_query_response response
  with
  | e -> Printf.printf "Error processing query: %s\n" (Printexc.to_string e)

(* ============================================ *)
(* POLICY MANAGEMENT MODE - NEW!               *)
(* ============================================ *)

let run_policy_list_mode () =
  Printf.printf "=== POLICY DATABASE ===\n\n";
  
  let runtime_env = Environment_config.Config.initialize () in
  let all_policies = Environment_config.Config.get_all_policies runtime_env in
  
  Printf.printf "Total policies loaded: %d\n\n" (List.length all_policies.policies);
  
  (* Group by regulation *)
  let regulations = Policy_loader.list_all_sections all_policies
    |> List.map (fun section ->
      let policies = Policy_loader.filter_by_section section all_policies in
      (section, policies)
    )
  in
  
  List.iter (fun (section, policies) ->
    Printf.printf "Section: %s\n" section;
    List.iter (fun policy ->
      Printf.printf "  [%s] %s - %s\n" 
        policy.Policy_loader.id 
        policy.Policy_loader.regulation 
        policy.Policy_loader.description
    ) policies;
    Printf.printf "\n"
  ) regulations

let run_policy_reload_mode regulation =
  Printf.printf "=== RELOADING POLICIES ===\n\n";
  
  let runtime_env = Environment_config.Config.initialize () in
  
  match regulation with
  | Some reg ->
      Printf.printf "Reloading %s policies...\n" reg;
      Environment_config.Config.reload_regulation runtime_env reg;
      Printf.printf "✅ %s policies reloaded\n" reg
  | None ->
      Printf.printf "Reloading all policies...\n";
      Environment_config.Config.reload_policies runtime_env;
      Printf.printf "✅ All policies reloaded\n"

(* ============================================ *)
(* DATA INSPECTION MODE - NEW!                 *)
(* ============================================ *)

let run_inspect_mode () =
  Printf.printf "=== SYSTEM INSPECTION ===\n\n";
  
  let runtime_env = Environment_config.Config.initialize () in
  
  (* Show type system *)
  Printf.printf "Type System:\n";
  Printf.printf "  Predicates: %d\n" (List.length runtime_env.type_env.predicates);
  Printf.printf "  Functions: %d\n" (List.length runtime_env.type_env.functions);
  Printf.printf "  Constants: %d\n\n" (List.length runtime_env.type_env.constants);
  
  (* Show domain *)
  Printf.printf "Domain:\n";
  Printf.printf "  Entities: %d\n" (List.length runtime_env.domain.entities);
  if List.length runtime_env.domain.entities <= 20 then begin
    Printf.printf "  Entities: ";
    let first_10 = 
      let rec take n lst =
        match n, lst with
        | 0, _ | _, [] -> []
        | n, x :: xs -> x :: take (n - 1) xs
      in
      take 10 runtime_env.domain.entities
    in
    List.iter (Printf.printf "%s, ") first_10;
    Printf.printf "...\n"
  end;
  Printf.printf "\n";
  
  (* Show facts *)
  Printf.printf "Facts Database:\n";
  Printf.printf "  Total facts: %d\n\n" (List.length runtime_env.facts.facts);
  
  (* Show policies *)
  let policies = Environment_config.Config.get_all_policies runtime_env in
  Printf.printf "Policies:\n";
  Printf.printf "  Total policies: %d\n" (List.length policies.policies)

(* ============================================ *)
(* COMMAND LINE INTERFACE                      *)
(* ============================================ *)

let print_usage () =
  Printf.printf "Usage:\n";
  Printf.printf "  precis file <filename>              Process a policy file\n";
  Printf.printf "  precis json                         Run in JSON mode (for Python)\n";
  Printf.printf "  precis query \"<formula>\" [reg]      Query policies\n";
  Printf.printf "  precis list                         List all policies\n";
  Printf.printf "  precis reload [regulation]          Reload policies\n";
  Printf.printf "  precis inspect                      Inspect system configuration\n";
  Printf.printf "\n";
  Printf.printf "Examples:\n";
  Printf.printf "  precis file examples/hipaa.policy\n";
  Printf.printf "  precis query \"disclose(hospital, patient, phi)\" HIPAA\n";
  Printf.printf "  precis reload HIPAA\n";
  Printf.printf "  precis list\n"

let () =
  let args = Array.to_list Sys.argv in
  
  match args with
  | [_] -> print_usage ()
  
  (* File mode *)
  | [_; "file"; filename] -> run_file_mode filename
  
  (* JSON mode for Python *)
  | [_; "json"] ->
      let runtime_env = Environment_config.Config.initialize () in
      run_json_mode runtime_env
  
  (* Query mode *)
  | [_; "query"; query] ->
      run_query_mode query None
  | [_; "query"; query; regulation] ->
      run_query_mode query (Some regulation)
  
  (* Policy management *)
  | [_; "list"] ->
      run_policy_list_mode ()
  
  | [_; "reload"] ->
      run_policy_reload_mode None
  | [_; "reload"; regulation] ->
      run_policy_reload_mode (Some regulation)
  
  (* Inspection *)
  | [_; "inspect"] ->
      run_inspect_mode ()
  
  (* Unknown command *)
  | _ -> 
      Printf.printf "Unknown command\n\n";
      print_usage ()