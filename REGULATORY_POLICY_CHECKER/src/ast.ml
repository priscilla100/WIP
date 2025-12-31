type binaryLogicalOp =
  | And
  | Or
  | Implies
  | Iff
  | Xor
type binaryTemporalOp =
  | Until
  | Since

type unaryTemporalOp =
  | Always
  | Next
  | Eventually
  | Historically
  | Yesterday
  | Once

type term =
  | Var of string
  | Const of string
  | Func of string * term list

type quantifier =
  | Forall of string list
  | Exists of string list

type formula =
  | True
  | False
  | Predicate of string * term list
  | Not of formula
  | BinLogicalOp of binaryLogicalOp * formula * formula
  | BinTemporalOp of binaryTemporalOp * formula * formula * (int * int) option
  | UnTemporalOp of unaryTemporalOp * formula * (int * int) option
  | Quantified of quantifier * formula
  | Annotated of formula * string 

type type_decl = string

type regulation_metadata = {
  name: string;
  version: string option;
  effective_date: string option;
}

type policy_file = {
  metadata: regulation_metadata option;
  type_decls: type_decl list;
  policies: formula list;
}

type ast = policy_file

(* ============================================ *)
(* TYPE SYSTEM                                 *)
(* ============================================ *)

(* Types for expressions and predicates *)
type expr_type =
  | TBool
  | TInt
  | TString
  | TCustom of string  (* For Entity, PHI, Purpose, etc. *)

(* Predicate signature: name, argument types, return type *)
type predicate_signature = {
  name: string;
  arg_types: expr_type list;
  return_type: expr_type;
}

(* Function signature: name, argument types, return type *)
type function_signature = {
  name: string;
  arg_types: expr_type list;
  return_type: expr_type;
}

(* Type environment containing all type information *)
type type_environment = {
  predicates: predicate_signature list;
  functions: function_signature list;
  constants: (string * expr_type) list;
}

(* Empty type environment *)
let empty_type_environment : type_environment = {
  predicates = [];
  functions = [];
  constants = [];
}

(* ============================================ *)
(* DATABASE TYPES                              *)
(* ============================================ *)

(* Domain database - all entities in the system *)
type domain_db = {
  entities: string list;
}

(* Facts database - ground facts about entities *)
type facts_db = {
  facts: (string * string list) list;  (* (predicate_name, [args]) *)
}

(* Functions database - function evaluations *)
type functions_db = {
  func_values: (string * string list * string) list;  (* (func_name, [args], result) *)
}
let string_of_binary_logical_operator = function
  | And -> "∧"
  | Or -> "∨"
  | Implies -> "→"
  | Iff -> "↔"
  | Xor -> "⊕"

let string_of_binary_temporal_operator = function
  | Until -> "U" 
  | Since -> "S"
  
let string_of_unary_temporal_operator = function
  | Next -> "X"
  | Always -> "G" 
  | Eventually -> "F"
  | Historically -> "H"
  | Once -> "O"
  | Yesterday -> "Y"

let string_of_quantifier = function
  | Forall vars -> "∀" ^ (String.concat "," vars) ^ "."
  | Exists vars -> "∃" ^ (String.concat "," vars) ^ "."

let rec string_of_term = function
  | Var v -> v 
  | Const c -> c
  | Func (f, args) -> f ^ "(" ^ (String.concat ", " (List.map string_of_term args)) ^ ")"

let string_of_bound = function
  | None -> ""
  | Some (l, u) -> "[" ^ string_of_int l ^ "," ^ string_of_int u ^ "]"
  
let rec string_of_formula = function
  | True -> "True"
  | False -> "False"
  | Predicate (p, []) -> p
  | Predicate (p, args) -> 
      p ^ "(" ^ (String.concat ", " (List.map string_of_term args)) ^ ")"
  | Not f -> "¬(" ^ string_of_formula f ^ ")"
  | BinLogicalOp (op, f1, f2) -> "(" ^ string_of_formula f1 ^ " " ^ string_of_binary_logical_operator op ^ " " ^ string_of_formula f2 ^ ")"
  | BinTemporalOp (op, f1, f2, bound) -> "(" ^ string_of_formula f1 ^ " " ^ string_of_binary_temporal_operator op ^ (string_of_bound bound) ^  " " ^ string_of_formula f2 ^ ")"
  | UnTemporalOp (op, f, bound) -> string_of_unary_temporal_operator op ^ (string_of_bound bound) ^ "(" ^ string_of_formula f ^ ")"
  | Quantified (quant, f) -> string_of_quantifier quant ^ "(" ^ string_of_formula f ^ ")"
  | Annotated (f, cite) -> "@[\"" ^ cite ^ "\"] " ^ string_of_formula f

(* ============================================ *)
(* STRING CONVERSION - TYPE SYSTEM             *)
(* ============================================ *)

let string_of_expr_type = function
  | TBool -> "Bool"
  | TInt -> "Int"
  | TString -> "String"
  | TCustom name -> name

let string_of_predicate_sig (ps: predicate_signature) : string =
  let args = String.concat " " (List.map string_of_expr_type ps.arg_types) in
  Printf.sprintf "%s : %s -> %s" ps.name args (string_of_expr_type ps.return_type)

let string_of_function_sig (fs: function_signature) : string =
  let args = String.concat " " (List.map string_of_expr_type fs.arg_types) in
  Printf.sprintf "%s : %s -> %s" fs.name args (string_of_expr_type fs.return_type)

(* ============================================ *)
(* STRING CONVERSION - POLICY FILE             *)
(* ============================================ *)

let string_of_metadata (m: regulation_metadata) : string =
  let version_str = match m.version with
    | Some v -> Printf.sprintf " version \"%s\"" v
    | None -> ""
  in
  let date_str = match m.effective_date with
    | Some d -> Printf.sprintf " effective_date \"%s\"" d
    | None -> ""
  in
  Printf.sprintf "regulation %s%s%s" m.name version_str date_str

let string_of_ast (pf: policy_file) : string =
  let buffer = Buffer.create 1024 in
  
  (* Metadata *)
  (match pf.metadata with
   | Some m -> Buffer.add_string buffer (string_of_metadata m ^ "\n\n")
   | None -> ());
  
  (* Type declarations *)
  if List.length pf.type_decls > 0 then begin
    Buffer.add_string buffer "type declaration starts\n";
    List.iter (fun td ->
      Buffer.add_string buffer (Printf.sprintf "type %s\n" td)
    ) pf.type_decls;
    Buffer.add_string buffer "type declaration ends\n\n"
  end;
  
  (* Policies *)
  Buffer.add_string buffer "policy starts\n\n";
  List.iter (fun policy ->
    Buffer.add_string buffer (string_of_formula policy ^ "\n;\n\n")
  ) pf.policies;
  Buffer.add_string buffer "policy ends\n";
  
  Buffer.contents buffer