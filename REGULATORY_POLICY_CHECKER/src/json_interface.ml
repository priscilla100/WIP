(* json_interface.ml - JSON serialization for Python integration *)

open Ast
open Type_checker
open Evaluator
open Query_engine

(* Convert term to JSON *)
let rec term_to_json (t: term) : Yojson.Basic.t =
  match t with
  | Var v -> `Assoc [("type", `String "var"); ("name", `String v)]
  | Const c -> `Assoc [("type", `String "const"); ("name", `String c)]
  | Func (f, args) -> 
      `Assoc [
        ("type", `String "func");
        ("name", `String f);
        ("args", `List (List.map term_to_json args))
      ]

(* Convert formula to JSON *)
let rec formula_to_json (f: formula) : Yojson.Basic.t =
  match f with
  | True -> `Assoc [("type", `String "true")]
  | False -> `Assoc [("type", `String "false")]
  | Predicate (p, args) ->
      `Assoc [
        ("type", `String "predicate");
        ("name", `String p);
        ("args", `List (List.map term_to_json args))
      ]
  | Not f' ->
      `Assoc [
        ("type", `String "not");
        ("formula", formula_to_json f')
      ]
  | BinLogicalOp (op, f1, f2) ->
      let op_str = match op with
        | And -> "and" | Or -> "or" | Implies -> "implies"
        | Iff -> "iff" | Xor -> "xor"
      in
      `Assoc [
        ("type", `String "binary_logical");
        ("operator", `String op_str);
        ("left", formula_to_json f1);
        ("right", formula_to_json f2)
      ]
  | BinTemporalOp (op, f1, f2, bound) ->
      let op_str = match op with Until -> "until" | Since -> "since" in
      let bound_json = match bound with
        | None -> `Null
        | Some (l, u) -> `Assoc [("lower", `Int l); ("upper", `Int u)]
      in
      `Assoc [
        ("type", `String "binary_temporal");
        ("operator", `String op_str);
        ("left", formula_to_json f1);
        ("right", formula_to_json f2);
        ("bound", bound_json)
      ]
  | UnTemporalOp (op, f', bound) ->
      let op_str = match op with
        | Always -> "always" | Eventually -> "eventually" | Next -> "next"
        | Historically -> "historically" | Once -> "once" | Yesterday -> "yesterday"
      in
      let bound_json = match bound with
        | None -> `Null
        | Some (l, u) -> `Assoc [("lower", `Int l); ("upper", `Int u)]
      in
      `Assoc [
        ("type", `String "unary_temporal");
        ("operator", `String op_str);
        ("formula", formula_to_json f');
        ("bound", bound_json)
      ]
  | Quantified (quant, f') ->
      let (quant_type, vars) = match quant with
        | Forall vs -> ("forall", vs)
        | Exists vs -> ("exists", vs)
      in
      `Assoc [
        ("type", `String "quantified");
        ("quantifier", `String quant_type);
        ("variables", `List (List.map (fun v -> `String v) vars));
        ("formula", formula_to_json f')
      ]
  | Annotated (f', cite) ->
      `Assoc [
        ("type", `String "annotated");
        ("citation", `String cite);
        ("formula", formula_to_json f')
      ]

(* Parse JSON to term *)
let rec json_to_term (j: Yojson.Basic.t) : term =
  let open Yojson.Basic.Util in
  match j |> member "type" |> to_string with
  | "var" -> Var (j |> member "name" |> to_string)
  | "const" -> Const (j |> member "name" |> to_string)
  | "func" ->
      let name = j |> member "name" |> to_string in
      let args = j |> member "args" |> to_list |> List.map json_to_term in
      Func (name, args)
  | _ -> failwith "Invalid term JSON"

(* Parse JSON to formula *)
let rec json_to_formula (j: Yojson.Basic.t) : formula =
  let open Yojson.Basic.Util in
  match j |> member "type" |> to_string with
  | "true" -> True
  | "false" -> False
  | "predicate" ->
      let name = j |> member "name" |> to_string in
      let args = j |> member "args" |> to_list |> List.map json_to_term in
      Predicate (name, args)
  | "not" ->
      let f = j |> member "formula" |> json_to_formula in
      Not f
  | "binary_logical" ->
      let op_str = j |> member "operator" |> to_string in
      let op = match op_str with
        | "and" -> And | "or" -> Or | "implies" -> Implies
        | "iff" -> Iff | "xor" -> Xor
        | _ -> failwith ("Unknown operator: " ^ op_str)
      in
      let f1 = j |> member "left" |> json_to_formula in
      let f2 = j |> member "right" |> json_to_formula in
      BinLogicalOp (op, f1, f2)
  | "binary_temporal" ->
      let op_str = j |> member "operator" |> to_string in
      let op = match op_str with
        | "until" -> Until | "since" -> Since
        | _ -> failwith ("Unknown temporal operator: " ^ op_str)
      in
      let f1 = j |> member "left" |> json_to_formula in
      let f2 = j |> member "right" |> json_to_formula in
      let bound = 
        try
          let b = j |> member "bound" in
          if b = `Null then None
          else Some (b |> member "lower" |> to_int, b |> member "upper" |> to_int)
        with _ -> None
      in
      BinTemporalOp (op, f1, f2, bound)
  | "unary_temporal" ->
      let op_str = j |> member "operator" |> to_string in
      let op = match op_str with
        | "always" -> Always | "eventually" -> Eventually | "next" -> Next
        | "historically" -> Historically | "once" -> Once | "yesterday" -> Yesterday
        | _ -> failwith ("Unknown unary temporal operator: " ^ op_str)
      in
      let f = j |> member "formula" |> json_to_formula in
      let bound = 
        try
          let b = j |> member "bound" in
          if b = `Null then None
          else Some (b |> member "lower" |> to_int, b |> member "upper" |> to_int)
        with _ -> None
      in
      UnTemporalOp (op, f, bound)
  | "quantified" ->
      let quant_type = j |> member "quantifier" |> to_string in
      let vars = j |> member "variables" |> to_list |> List.map to_string in
      let f = j |> member "formula" |> json_to_formula in
      let quant = match quant_type with
        | "forall" -> Forall vars
        | "exists" -> Exists vars
        | _ -> failwith ("Unknown quantifier: " ^ quant_type)
      in
      Quantified (quant, f)
  | "annotated" ->
      let cite = j |> member "citation" |> to_string in
      let f = j |> member "formula" |> json_to_formula in
      Annotated (f, cite)
  | t -> failwith ("Unknown formula type: " ^ t)

(* Convert facts database to JSON *)
let facts_to_json (facts: Ast.facts_db) : Yojson.Basic.t =
  `Assoc [
    ("facts", `List (List.map (fun (pred, args) ->
      `Assoc [
        ("predicate", `String pred);
        ("arguments", `List (List.map (fun a -> `String a) args))
      ]
    ) facts.facts))
  ]

(* Parse JSON to facts database *)
let json_to_facts (j: Yojson.Basic.t) : Ast.facts_db =
  let open Yojson.Basic.Util in
  let facts_list = j |> member "facts" |> to_list in
  let facts = List.map (fun fact ->
    let pred = fact |> member "predicate" |> to_string in
    let args = fact |> member "arguments" |> to_list |> List.map to_string in
    (pred, args)
  ) facts_list in
  { facts }

(* Convert evaluation result to JSON *)
let eval_result_to_json (result: eval_result) : Yojson.Basic.t =
  match result with
  | True -> `Assoc [("result", `String "true")]
  | False -> `Assoc [("result", `String "false")]

(* Convert query response to JSON *)
let query_response_to_json (response: query_response) : Yojson.Basic.t =
  `Assoc [
    ("query_formula", formula_to_json response.query_formula);
    ("matched_policies", `List (List.map (fun m ->
      `Assoc [
        ("policy_id", `String m.policy.id);
        ("regulation", `String m.policy.regulation);
        ("section", `String m.policy.section);
        ("description", `String m.policy.description);
        ("relevance_score", `Float m.relevance_score);
        ("matched_terms", `List (List.map (fun t -> `String t) m.matched_terms))
      ]
    ) response.matched_policies));
    ("evaluations", `List (List.map (fun e ->
      `Assoc [
        ("policy_id", `String e.policy_id);
        ("regulation", `String e.regulation);
        ("section", `String e.section);
        ("description", `String e.description);
        ("formula_text", `String e.formula_text);
        ("evaluation", eval_result_to_json e.evaluation);
        ("explanation", `String e.explanation)
      ]
    ) response.evaluations));
    ("overall_compliant", `Bool response.overall_compliant);
    ("violations", `List (List.map (fun v -> `String v) response.violations))
  ]

type query_request = {
  formula_string: string;
  facts: Ast.facts_db;
  regulation_filter: string option;
}

(* Parse a query request from JSON *)
let parse_query_request (json_str: string) : query_request =
  try
    let open Yojson.Basic.Util in
    let json = Yojson.Basic.from_string json_str in
    
    let formula_str = json |> member "formula" |> to_string in
    let facts = json |> member "facts" |> json_to_facts in
    let regulation = 
      try Some (json |> member "regulation" |> to_string)
      with _ -> None
    in
    
    { formula_string = formula_str; facts; regulation_filter = regulation }
  with e ->
    failwith (Printf.sprintf "Failed to parse query request: %s" (Printexc.to_string e))

(* Helper: Extract unique entities from facts *)
let extract_entities_from_facts (facts: Ast.facts_db) : string list =
  List.fold_left (fun acc (_, args) ->
    List.fold_left (fun acc2 arg ->
      if List.mem arg acc2 then acc2 else arg :: acc2
    ) acc args
  ) [] facts.facts
  |> List.sort_uniq String.compare


(* In handle_query_json *)
let rec handle_query_json (json_str: string) (ast_env: Ast.type_environment) (policy_manager: Policy_loader.policy_manager) : string =
  try
    let request = parse_query_request json_str in
    
    (* Parse the formula string *)
    let formula = 
      try
        let lexbuf = Lexing.from_string request.formula_string in
        (* Add position tracking *)
        lexbuf.lex_curr_p <- { lexbuf.lex_curr_p with pos_fname = "query" };
        
        Parser.main Lexer.read lexbuf
      with
      | Parser.Error ->
          let pos = Lexing.lexeme_start_p (Lexing.from_string request.formula_string) in
          failwith (Printf.sprintf "Parse error at position %d in formula: %s" 
            pos.pos_cnum request.formula_string)
      | e ->
          failwith (Printf.sprintf "Parse error: %s\nFormula: %s" 
            (Printexc.to_string e) request.formula_string)
    in
    
    (* Extract the first formula from the policy file *)
    let query_formula = match formula.policies with
      | [] -> failwith "No formula provided"
      | f :: _ -> f
    in
    
    (* Setup databases *)
    let domain = { Ast.entities = extract_entities_from_facts request.facts } in
    let funcs = { Ast.func_values = [] } in (* Empty for now *)
    
    (* Process the query - now with correct types *)
    let response = Query_engine.process_query 
      query_formula 
      request.regulation_filter
      domain 
      request.facts 
      funcs 
      ast_env
      policy_manager
    in
    
    (* Return JSON response *)
    query_response_to_json response |> Yojson.Basic.to_string
    
  with e ->
    (* Return error as JSON *)
    `Assoc [
      ("error", `String (Printexc.to_string e));
      ("success", `Bool false)
    ] |> Yojson.Basic.to_string

(* ============================================ *)
(* COMMAND-LINE INTERFACE                      *)
(* ============================================ *)

(* Read JSON from stdin, process, write JSON to stdout *)
let run_stdio_mode (runtime_env: Environment_config.Config.runtime_environment) : unit =
  try
    (* Read ALL lines from stdin, not just first line *)
    let rec read_all_lines acc =
      try
        let line = read_line () in
        read_all_lines (line :: acc)
      with End_of_file ->
        List.rev acc
    in
    let lines = read_all_lines [] in
    let input = String.concat "\n" lines in
    
    if String.length input = 0 then
      let error_json = `Assoc [
        ("error", `String "No input provided");
        ("success", `Bool false)
      ] |> Yojson.Basic.to_string in
      print_endline error_json
    else
      let output = handle_query_json input runtime_env.type_env runtime_env.policy_manager in
      print_endline output
  with e -> 
      let error_json = `Assoc [
        ("error", `String (Printexc.to_string e));
        ("success", `Bool false)
      ] |> Yojson.Basic.to_string in
      print_endline error_json

(* File-based mode: read JSON from file, write response to stdout *)
let run_file_mode (filename: string) (runtime_env: Environment_config.Config.runtime_environment) : unit =
  try
    let ic = open_in filename in
    let input = really_input_string ic (in_channel_length ic) in
    close_in ic;
    let output = handle_query_json input runtime_env.type_env runtime_env.policy_manager in
    print_endline output
  with e ->
    let error_json = `Assoc [
      ("error", `String (Printexc.to_string e));
      ("success", `Bool false)
    ] |> Yojson.Basic.to_string in
    print_endline error_json