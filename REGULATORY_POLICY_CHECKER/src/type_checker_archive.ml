open Ast

(*All the presently available types in our AST *)
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

(*Gave the types an alias*)
type expr_type = base_type

(*Stack-like type context for bounded variables*)
type type_context = (string * expr_type) list (*represented as x : int, y :  entity,  z :  bool, etc. *)

(*Handling predicates and function of FOL bounded variables - kinda of like how the lexer breaks down these formulas*)
type predicate_signature = 
{
  name: string;
  arg_types: expr_type list; (*list of types of arguments*)
  return_type: expr_type; (*return type of the predicate, usually bool (TBool)*)
}

type function_signature = 
{
  name: string;
  arg_types: expr_type list; 
  return_type: expr_type; 
}

type type_environment = 
{
  predicates: predicate_signature list; (*map from predicate name to its signature*)
  functions: function_signature list; (*map from function name to its signature*)
  constants: (string * expr_type) list; (*map from constant name to its type*)
}

(*Comparsion operators are considered as predicates too*)
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

(*For when the type envrionnment is empty*)
let empty_type_environment = 
  {
    predicates = [];
    functions = [];
    constants = [];
  }

let empty_context = []

(*lets push the bounded variable unto to the type context*)
let push_context ctx var_name var_type =
  (var_name, var_type) :: ctx

(*lookup the type of a variable in the context*)
let lookup_context ctx var_name =
  List.assoc_opt var_name ctx
(*lookup the type of a constant in the type environment*)
let lookup_constant_type (env : type_environment) (const_name:  string) : expr_type option =
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

(*let create some errors for type checking*)
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


let rec typecheck_term (ctx: type_context) (env: type_environment) (t: term) : (expr_type, type_error) result =
  match t with
  | Var v -> 
      (match lookup_context ctx v with
       | Some var_type -> Ok var_type
       | None -> 
           Error (UnboundVariable v))
           
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

(*Since we might have bounded in our formula, lets validate the temporal bounds if they do appear*)
(* FIX: Corrected typo: 'tempporal' -> 'temporal' *)
let validate_temporal_bound = function 
  | None -> Ok ()
  | Some (l, u) when l >= 0 && u >= l -> Ok ()
  | Some (l, u) -> Error (InvalidTemporalBound ("bounds must be: 0 <= l <= u, got [" ^ string_of_int l ^ "," ^ string_of_int u ^ "]"))
(* The GOAL: Traverse AST left-to-right:
   1. Hit quantifier -> push variables to context
   2. Recurse right side with new context
   3. Context naturally clears when returning (immutable stack) *)

let rec typecheck_formula (ctx: type_context) (env: type_environment) (formula: formula) : (unit, type_error) result =
  match formula with
  | True | False -> Ok ()

(* For QUANTIFIERS, we push to the type context "stack", recurse, clear on return*)
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

    (* KEY for Binary Logical Operators: Both left and right formulas must type check *)
  (* Example: Forall x. Person(x) -> Doctor(x)
     Left side (Person(x)) and Right side (Doctor(x)) both see x in context *)
  | BinLogicalOp (_op, f1, f2) ->
      (match typecheck_formula ctx env f1 with
       | Error e -> Error e
       | Ok () ->
           (* Both sides checked in SAME context *)
           typecheck_formula ctx env f2)
  
 (* For Binary Temporal Operators, we need to validate the temporal bounds too *)
 | BinTemporalOp (_op, f1, f2, bound) ->
      (match validate_temporal_bound bound with
       | Error e -> Error e
       | Ok () ->
           (match typecheck_formula ctx env f1 with
            | Error e -> Error e
            | Ok () ->
                typecheck_formula ctx env f2
           )
      ) 

  (* Unary Temporal Operators *)
  | UnTemporalOp (_op, f, bound) ->
      (match validate_temporal_bound bound with
       | Error e -> Error e
       | Ok () ->
           typecheck_formula ctx env f
      )
  | Annotated (f, _cite) ->
      typecheck_formula ctx env f

let typecheck_policy_file (pf: ast) (env: type_environment) : (unit, type_error list) result =
  let errors = ref [] in
  (* FIX: Access the 'policies' field of the record 'pf' (which has type 'ast' or 'policy_file') *)
  List.iter (fun formula ->
    match typecheck_formula empty_context env formula with
    | Ok () -> ()
    | Error e -> errors := e :: !errors
  ) pf.policies; (* <--- FIXED HERE *)
  if !errors = [] then Ok ()
  else Error (List.rev !errors)

(* ============ EXAMPLE USAGE ============ *)

(* Build a type environment for policy formulas *)
(* let example_env = {
  predicates = [
    { name = "Person"; arg_types = [TEntity]; return_type = TBool };
    { name = "Doctor"; arg_types = [TEntity]; return_type = TBool };
    { name = "Approved"; arg_types = [TEntity]; return_type = TBool };
    { name = "disclose"; arg_types = [TEntity; TEntity; TEntity; TEntity]; return_type = TBool };
    { name = "inrole"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "authorized"; arg_types = [TEntity; TEntity; TEntity; TEntity]; return_type = TBool };
    (* { name = "="; arg_types = [TInt; TInt]; return_type = TBool }; *)
    { name = "="; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "<"; arg_types = [TInt; TInt]; return_type = TBool };
  ];
  functions = [
    { name = "age"; arg_types = [TEntity]; return_type = TInt };
    { name = "salary"; arg_types = [TEntity]; return_type = TInt };
  ];
  constants = [
    ("MAX_AGE", TInt);
    ("MIN_SALARY", TInt);
    ("doctor", TEntity);
    ("patient", TEntity);
  ];
}

(* Example 1: Forall x. Person(x) -> Doctor(x) *)
let example1 =
  Quantified (
    Forall ["x"],
    BinLogicalOp (
      Implies,
      Predicate ("Person", [Var "x"]),
      Predicate ("Doctor", [Var "x"])
    )
  )

(* Example 2: Forall x, y. (Person(x) ∧ Person(y)) -> (age(x) = age(y)) *)
let example2 =
  Quantified (
    Forall ["x"; "y"],
    BinLogicalOp (
      Implies,
      BinLogicalOp (
        And,
        Predicate ("Person", [Var "x"]),
        Predicate ("Person", [Var "y"])
      ),
      Predicate ("=", [Func ("age", [Var "x"]); Func ("age", [Var "y"])])
    )
  )

(* Example 3: Eventually[0,10] Approved(x) - with temporal operators *)
let example3 =
  UnTemporalOp (
    Eventually,
    Predicate ("Approved", [Var "x"]),
    Some (0, 10)
  )

  let example4 =
    Quantified (
      Forall ["p1"; "p2"; "q"; "r"],
      BinLogicalOp (
        Implies,
        BinLogicalOp (
          And,
          BinLogicalOp (
            And,
            BinLogicalOp (
              And,
              Predicate ("disclose", [Var "p1"; Var "p2"; Var "q"; Var "r"]),
              Predicate ("inrole", [Var "p1"; Const "doctor"])
            ),
            Predicate ("inrole", [Var "p2"; Const "patient"])
          ),
          Predicate ("=", [Var "p2"; Var "q"])
        ),
        Predicate ("authorized", [Var "p1"; Var "p2"; Var "q"; Var "r"])
      )
    )
let () =
  print_endline "=== Policy Language Type Checker ===\n";
  
  print_endline "Example 1: Forall x. Person(x) -> Doctor(x)";
  (match typecheck_formula empty_context example_env example1 with
   | Ok () -> print_endline "✓ Type checks!\n"
   | Error e -> print_endline ("✗ Type error: " ^ string_of_type_error e ^ "\n"));
  
  print_endline "Example 2: Forall x, y. (Person(x) ∧ Person(y)) -> (age(x) = age(y))";
  (match typecheck_formula empty_context example_env example2 with
   | Ok () -> print_endline "✓ Type checks!\n"
   | Error e -> print_endline ("✗ Type error: " ^ string_of_type_error e ^ "\n"));
  
  print_endline "Example 3: Eventually[0,10] Approved(x)";
  (match typecheck_formula empty_context example_env example3 with
   | Ok () -> print_endline "✓ Type checks!\n"
   | Error e -> print_endline ("✗ Type error: " ^ string_of_type_error e ^ "\n"));

  print_endline "Example 4: forall p1, p2, q, r. (disclose(p1, p2, q, r) and inrole(p1, doctor) and inrole(p2, patient) and p2 = q) implies authorized(p1, p2, q, r)";
  (match typecheck_formula empty_context example_env example4 with
   | Ok () -> print_endline "✓ Type checks!\n"
   | Error e -> print_endline ("✗ Type error: " ^ string_of_type_error e ^ "\n")) *)