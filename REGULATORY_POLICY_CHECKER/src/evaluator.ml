(* evaluator.ml - Evaluates formulas against facts to determine compliance *)
open Ast


(* 4. Variable Assignment Context: Tracks variable bindings *)
type var_assignment = (string * string) list

(* Evaluation Result *)
type eval_result = 
  | True
  | False

(* Helper: Evaluate a term to get its concrete value *)
let rec eval_term (assignment: var_assignment) (funcs: functions_db) (t: term) : string option =
  match t with
  | Var v -> 
    List.assoc_opt v assignment
  | Const c -> 
      Some c (* Constants evaluate to themselves *)
  | Func (f, args) ->
      (* Evaluate all arguments *)
      let eval_args = List.map (eval_term assignment funcs) args in
      (* Check if all arguments evaluated *)
      if List.exists (fun x -> x = None) eval_args then
        None
      else
        let arg_values = List.filter_map (fun x -> x) eval_args in
        (* Look up function result in database *)
        (match List.find_opt (fun (fname, fargs, _) -> 
          fname = f && fargs = arg_values
        ) funcs.func_values with
         | Some (_, _, result) -> Some result
         | None -> None)

(* Helper: Check if a ground fact is true *)
let check_fact (facts: facts_db) (pred_name: string) (args: string list) : bool =
  List.exists (fun (name, fact_args) ->
    name = pred_name && fact_args = args
  ) facts.facts

(* Helper: Evaluate comparison operators *)
let eval_comparison (op: string) (v1: string) (v2: string) : bool =
  match op with
  | "=" -> v1 = v2
  | "!=" -> v1 <> v2
  | "<" -> (try int_of_string v1 < int_of_string v2 with _ -> false)
  | "<=" -> (try int_of_string v1 <= int_of_string v2 with _ -> false)
  | ">" -> (try int_of_string v1 > int_of_string v2 with _ -> false)
  | ">=" -> (try int_of_string v1 >= int_of_string v2 with _ -> false)
  | _ -> false

(* Main Evaluation Engine *)
let rec eval_formula (assignment: var_assignment) (domain: domain_db) 
                     (facts: facts_db) (funcs: functions_db) (f: formula) : eval_result =
  match f with
  | True -> 
      True
  
  | False -> 
      False
  
  | Predicate (p, args) ->
      (* Evaluate all arguments *)
      let eval_args = List.map (eval_term assignment funcs) args in
      if List.exists (fun x -> x = None) eval_args then
        False (* If any arg is unbound, predicate is false *)
      else
        let arg_values = List.filter_map (fun x -> x) eval_args in
        (* Check if it's a comparison operator *)
        (match p with
         | "=" | "!=" | "<" | "<=" | ">" | ">=" ->
             (match arg_values with
              | [v1; v2] ->
                  if eval_comparison p v1 v2 then True else False
              | _ -> False)
         | _ ->
             (* Regular predicate: check facts database *)
             if check_fact facts p arg_values then True else False)
  
  | Not f ->
      (match eval_formula assignment domain facts funcs f with
       | True -> False
       | False -> True)
  
  | BinLogicalOp (And, f1, f2) ->
      (match eval_formula assignment domain facts funcs f1 with
       | False -> False
       | True ->
           (match eval_formula assignment domain facts funcs f2 with
            | True -> True
            | False -> False))
  
  | BinLogicalOp (Or, f1, f2) ->
      (match eval_formula assignment domain facts funcs f1 with
       | True -> True
       | False ->
           (match eval_formula assignment domain facts funcs f2 with
            | True -> True
            | False -> False))
  
  | BinLogicalOp (Implies, f1, f2) ->
      (match eval_formula assignment domain facts funcs f1 with
       | False -> True (* False implies anything *)
       | True ->
           (match eval_formula assignment domain facts funcs f2 with
            | True -> True
            | False -> False))
  
  | BinLogicalOp (Iff, f1, f2) ->
      let v1 = eval_formula assignment domain facts funcs f1 in
      let v2 = eval_formula assignment domain facts funcs f2 in
      (match (v1, v2) with
       | (True, True) | (False, False) -> True
       | _ -> False)
  
  | BinLogicalOp (Xor, f1, f2) ->
      let v1 = eval_formula assignment domain facts funcs f1 in
      let v2 = eval_formula assignment domain facts funcs f2 in
      (match (v1, v2) with
       | (True, False) | (False, True) -> True
       | _ -> False)
  
  (* Quantifiers: Iterate over domain *)
  | Quantified (Forall vars, f) ->
      (* Generate all possible assignments for vars *)
      let rec generate_assignments vars_list domain_vals =
        match vars_list with
        | [] -> [[]]
        | v :: rest ->
            let rest_assignments = generate_assignments rest domain_vals in
            List.concat (List.map (fun entity ->
              List.map (fun assignment -> (v, entity) :: assignment) rest_assignments
            ) domain_vals)
      in
      let all_assignments = generate_assignments vars domain.entities in
      (* Forall is true if formula is true for ALL assignments *)
      (match List.find_opt (fun assign ->
        let new_assignment = List.fold_left (fun acc (v, e) ->
          (v, e) :: acc
        ) assignment assign in
        match eval_formula new_assignment domain facts funcs f with
        | False -> true
        | True -> false
      ) all_assignments with
       | Some _ -> False
       | None -> True)
  
  | Quantified (Exists vars, f) ->
      let rec generate_assignments vars_list domain_vals =
        match vars_list with
        | [] -> [[]]
        | v :: rest ->
            let rest_assignments = generate_assignments rest domain_vals in
            List.concat (List.map (fun entity ->
              List.map (fun assignment -> (v, entity) :: assignment) rest_assignments
            ) domain_vals)
      in
      let all_assignments = generate_assignments vars domain.entities in
      (* Exists is true if formula is true for SOME assignment *)
      (match List.find_opt (fun assign ->
        let new_assignment = List.fold_left (fun acc (v, e) ->
          (v, e) :: acc
        ) assignment assign in
        match eval_formula new_assignment domain facts funcs f with
        | True -> true
        | False -> false
      ) all_assignments with
       | Some _ -> True
       | None -> False)
  
  | BinTemporalOp (_, f1, f2, _) ->
      (* Simplified: Evaluate both sides with AND semantics *)
      (match eval_formula assignment domain facts funcs f1 with
       | True ->
           (match eval_formula assignment domain facts funcs f2 with
            | True -> True
            | False -> False)
       | False -> False)
  
  | UnTemporalOp (_, f, _) ->
      (* Simplified: Just evaluate the formula *)
      eval_formula assignment domain facts funcs f
  
  | Annotated (f, _) ->
      eval_formula assignment domain facts funcs f

(* Evaluate all formulas in a policy *)
let eval_policy (domain: domain_db) (facts: facts_db) (funcs: functions_db) 
                (formulas: formula list) : (string * eval_result) list =
  List.mapi (fun idx f ->
    let result = eval_formula [] domain facts funcs f in
    (Printf.sprintf "Formula %d" (idx + 1), result)
  ) formulas

(* Pretty print results *)
let string_of_eval_result = function
  | True -> "✓ True"
  | False -> "✗ False"

let print_eval_results results =
  List.iter (fun (label, result) ->
    Printf.printf "  %s: %s\n" label (string_of_eval_result result)
  ) results