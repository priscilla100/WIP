open Ast

(* ============================================ *)
(* TYPE SYSTEM - Keep existing types           *)
(* ============================================ *)

(* All the presently available types in our AST *)
type base_type =
  | TInt
  | TBool
  | TString
  | TEntity 
  | TTime

let string_of_base_type = function
  | TInt -> "Int"
  | TBool -> "Bool"
  | TString -> "String"
  | TEntity -> "Entity"
  | TTime -> "Time"

(* Gave the types an alias *)
type expr_type = base_type

(* Stack-like type context for bounded variables *)
type type_context = (string * expr_type) list

(* Handling predicates and function of FOL bounded variables *)
type predicate_signature = 
{
  name: string;
  arg_types: expr_type list;
  return_type: expr_type;
}

type function_signature = 
{
  name: string;
  arg_types: expr_type list; 
  return_type: expr_type; 
}

type type_environment = 
{
  predicates: predicate_signature list;
  functions: function_signature list;
  constants: (string * expr_type) list;
}

(* ============================================ *)
(* TYPE CONVERSION: Ast <-> Type_checker       *)
(* ============================================ *)

(* Convert Ast.expr_type to Type_checker.expr_type *)
let ast_type_to_checker_type (t: Ast.expr_type) : expr_type =
  match t with
  | Ast.TBool -> TBool
  | Ast.TInt -> TInt
  | Ast.TString -> TString
  | Ast.TCustom "Entity" -> TEntity
  | Ast.TCustom "Time" -> TTime
  | Ast.TCustom _ -> TEntity  (* Default custom types to Entity *)

(* Convert Type_checker.expr_type to Ast.expr_type *)
let checker_type_to_ast_type (t: expr_type) : Ast.expr_type =
  match t with
  | TBool -> Ast.TBool
  | TInt -> Ast.TInt
  | TString -> Ast.TString
  | TEntity -> Ast.TCustom "Entity"
  | TTime -> Ast.TCustom "Time"

(* Convert Ast predicate signature to Type_checker signature *)
let ast_pred_to_checker (ps: Ast.predicate_signature) : predicate_signature =
  {
    name = ps.Ast.name;
    arg_types = List.map ast_type_to_checker_type ps.Ast.arg_types;
    return_type = ast_type_to_checker_type ps.Ast.return_type;
  }

(* Convert Ast function signature to Type_checker signature *)
let ast_func_to_checker (fs: Ast.function_signature) : function_signature =
  {
    name = fs.Ast.name;
    arg_types = List.map ast_type_to_checker_type fs.Ast.arg_types;
    return_type = ast_type_to_checker_type fs.Ast.return_type;
  }

(* Convert Ast.type_environment to Type_checker.type_environment *)
let ast_env_to_checker_env (env: Ast.type_environment) : type_environment =
  {
    predicates = List.map ast_pred_to_checker env.Ast.predicates;
    functions = List.map ast_func_to_checker env.Ast.functions;
    constants = List.map (fun (name, typ) -> (name, ast_type_to_checker_type typ)) env.Ast.constants;
  }

(* ============================================ *)
(* COMPARISON OPERATORS                        *)
(* ============================================ *)

type comparison_operator = 
  | Eq  (* = *)
  | Neq (* != *)
  | Lt  (* < *)
  | Leq (* <= *)
  | Gt  (* > *)
  | Geq (* >= *)

let string_of_comparison_operator = function
  | Eq -> "="
  | Neq -> "!="
  | Lt -> "<"
  | Leq -> "<="
  | Gt -> ">"
  | Geq -> ">="

(* ============================================ *)
(* EMPTY CONTEXTS                              *)
(* ============================================ *)

let empty_type_environment = 
  {
    predicates = [];
    functions = [];
    constants = [];
  }

let empty_context = []

(* ============================================ *)
(* CONTEXT OPERATIONS                          *)
(* ============================================ *)

let push_context ctx var_name var_type =
  (var_name, var_type) :: ctx

let lookup_context ctx var_name =
  List.assoc_opt var_name ctx

let lookup_constant_type (env : type_environment) (const_name: string) : expr_type option =
  List.assoc_opt const_name env.constants

let lookup_function_signature (env : type_environment) (func_name: string) : function_signature option =
  List.find_opt (fun sig_ -> sig_.name = func_name) env.functions

let lookup_predicate (env : type_environment) (pred_name : string) : predicate_signature option =
  List.find_opt (fun (p : predicate_signature) -> String.equal p.name pred_name) env.predicates

let type_equals t1 t2 =
  match (t1, t2) with
  | (TInt, TInt) -> true
  | (TBool, TBool) -> true
  | (TString, TString) -> true
  | (TEntity, TEntity) -> true
  | (TTime, TTime) -> true
  | _ -> false

(* ============================================ *)
(* TYPE ERRORS                                 *)
(* ============================================ *)

type type_error =
  | UnknownVar of string
  | UnknownPredicate of string
  | UnknownFunction of string
  | UnknownConst of string
  | ArityMismatch of string * int * int
  | TypeMismatch of expr_type * expr_type
  | InvalidArgumentType of int * expr_type * expr_type
  | UnboundVariable of string
  | InvalidTemporalBound of string
  | InvalidQuantifierBinding of string

let string_of_type_error = function
  | UnknownVar v -> "Unknown variable " ^ v
  | UnknownPredicate p -> "Unknown predicate: " ^ p
  | UnknownFunction f -> "Unknown function: " ^ f
  | UnknownConst c -> "Unknown constant: " ^ c
  | ArityMismatch (name, exp, got) ->
      name ^ " expects " ^ string_of_int exp ^ " arguments, got " ^ string_of_int got
  | TypeMismatch (exp, got) ->
      "Type mismatch: expected " ^ string_of_base_type exp ^ ", got " ^ string_of_base_type got
  | InvalidArgumentType (n, exp, got) ->
      "Argument " ^ string_of_int n ^ ": expected " ^ string_of_base_type exp ^ ", got " ^ string_of_base_type got
  | UnboundVariable v -> "Unbound variable: " ^ v
  | InvalidTemporalBound b -> "Invalid temporal bound: " ^ b
  | InvalidQuantifierBinding v -> "Invalid quantifier binding: " ^ v

(* ============================================ *)
(* TERM TYPE CHECKING                          *)
(* ============================================ *)

let rec typecheck_term (ctx: type_context) (env: type_environment) (t: term) : (expr_type, type_error) result =
  match t with
  | Var v -> 
      (match lookup_context ctx v with
       | Some var_type -> Ok var_type
       | None -> Error (UnboundVariable v))
           
  | Const c -> 
      (match lookup_constant_type env c with
       | Some const_type -> Ok const_type
       | None -> Error (UnknownConst c))
       
  | Func (f, args) ->
      (match lookup_function_signature env f with
       | None -> Error (UnknownFunction f)
       | Some func_sig ->
           if List.length func_sig.arg_types <> List.length args then
            Error (ArityMismatch (f, List.length func_sig.arg_types, List.length args))
           else
            let rec check_args_list args_to_check idx =
              match args_to_check with
              | [] -> Ok ()
              | arg :: rest ->
                  (match typecheck_term ctx env arg with
                   | Error e -> Error e
                   | Ok arg_type ->
                       let expected_type = List.nth func_sig.arg_types idx in
                       if type_equals expected_type arg_type then
                         check_args_list rest (idx + 1)
                       else
                         Error (InvalidArgumentType (idx, expected_type, arg_type))
                  )
            in
            (match check_args_list args 0 with
             | Error e -> Error e
             | Ok () -> Ok func_sig.return_type)
      )

(* ============================================ *)
(* TEMPORAL BOUNDS VALIDATION                  *)
(* ============================================ *)

let validate_temporal_bound = function 
  | None -> Ok ()
  | Some (l, u) when l >= 0 && u >= l -> Ok ()
  | Some (l, u) -> Error (InvalidTemporalBound ("bounds must be: 0 <= l <= u, got [" ^ string_of_int l ^ "," ^ string_of_int u ^ "]"))

(* ============================================ *)
(* FORMULA TYPE CHECKING                       *)
(* ============================================ *)

let rec typecheck_formula (ctx: type_context) (env: type_environment) (formula: formula) : (unit, type_error) result =
  match formula with
  | True | False -> Ok ()

  | Quantified (Forall vars, f) ->
      let new_ctx = List.fold_left (fun acc v -> push_context acc v TEntity) ctx vars in
      typecheck_formula new_ctx env f
      
  | Quantified (Exists vars, f) ->
      let new_ctx = List.fold_left (fun acc v -> push_context acc v TEntity) ctx vars in
      typecheck_formula new_ctx env f
      
  | Predicate (p, args) ->
      (match lookup_predicate env p with
       | None -> Error (UnknownPredicate p)
       | Some pred_sig ->
           if List.length pred_sig.arg_types <> List.length args then
             Error (ArityMismatch (p, List.length pred_sig.arg_types, List.length args))
           else
             let rec check_args_list args_to_check idx =
               match args_to_check with
               | [] -> Ok ()
               | arg :: rest ->
                   (match typecheck_term ctx env arg with
                    | Error e -> Error e
                    | Ok arg_type ->
                        let expected_type = List.nth pred_sig.arg_types idx in
                        if type_equals expected_type arg_type then
                          check_args_list rest (idx + 1)
                        else
                          Error (InvalidArgumentType (idx, expected_type, arg_type))
                   )
             in
             check_args_list args 0
      )
      
  | Not f -> typecheck_formula ctx env f

  | BinLogicalOp (_op, f1, f2) ->
      (match typecheck_formula ctx env f1 with
       | Error e -> Error e
       | Ok () -> typecheck_formula ctx env f2)
  
  | BinTemporalOp (_op, f1, f2, bound) ->
      (match validate_temporal_bound bound with
       | Error e -> Error e
       | Ok () ->
           (match typecheck_formula ctx env f1 with
            | Error e -> Error e
            | Ok () -> typecheck_formula ctx env f2))

  | UnTemporalOp (_op, f, bound) ->
      (match validate_temporal_bound bound with
       | Error e -> Error e
       | Ok () -> typecheck_formula ctx env f)
       
  | Annotated (f, _cite) ->
      typecheck_formula ctx env f

(* ============================================ *)
(* POLICY FILE TYPE CHECKING                   *)
(* ============================================ *)

let typecheck_policy_file (pf: ast) (env: type_environment) : (unit, type_error list) result =
  let errors = ref [] in
  List.iter (fun formula ->
    match typecheck_formula empty_context env formula with
    | Ok () -> ()
    | Error e -> errors := e :: !errors
  ) pf.policies;
  if !errors = [] then Ok ()
  else Error (List.rev !errors)

(* ============================================ *)
(* WRAPPER FOR Ast.type_environment            *)
(* ============================================ *)

(* Convenience function that accepts Ast.type_environment *)
let typecheck_policy_file_with_ast_env (pf: ast) (ast_env: Ast.type_environment) : (unit, type_error list) result =
  let checker_env = ast_env_to_checker_env ast_env in
  typecheck_policy_file pf checker_env