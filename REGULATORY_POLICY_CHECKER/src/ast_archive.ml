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

let string_of_metadata = function
| None -> ""
| Some {name; version; effective_date} ->
    let ver = match version with
      | None -> ""
        | Some v -> " version \"" ^ v ^ "\""
    in
    let date = match effective_date with
      | None -> ""
      | Some d -> ", effective \"" ^ d ^ "\""
  in 
    "Regulation " ^ name ^ ver ^ date ^ "\n\n"

let string_of_ast (pf: ast) : string =
  let metadata_section = string_of_metadata pf.metadata in

  let type_section = 
    if pf.type_decls = [] then ""
    else "type declaration starts\n" ^ (String.concat "\n" (List.map (fun t -> "type " ^ t) pf.type_decls)) ^ 
    "\ntype declaration ends\n\n"
  in
  let policies_section = 
    if pf.policies = [] then "No policies defined."
    else "policy starts\n" ^ (String.concat ";\n\n" (List.map string_of_formula pf.policies ) ) ^
    "\npolicy ends"
  in
  metadata_section ^ type_section ^ policies_section