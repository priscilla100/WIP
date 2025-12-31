(* main.ml - Simplified with centralized configuration *)

open Ast
open Type_checker
open Evaluator
open Environment_config

(* ============================================ *)
(* PROCESSING PIPELINE                         *)
(* ============================================ *)

let process_input input env domain facts funcs =
  match Parser.main Lexer.read (Lexing.from_string input) with
  | exception e -> 
      Printf.printf "  [ERROR] Parsing Failed: %s\n" (Printexc.to_string e);
      ()
  | ast ->
      Printf.printf "  [STEP 1] Parsing successful (AST created). ✅\n";
      
      match Type_checker.typecheck_policy_file ast env with
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

let run_json_mode (env: type_environment) : unit =
  Json_interface.run_stdio_mode env

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
(* TEST MODE                                   *)
(* ============================================ *)

let run_test_mode () =
  Printf.printf "Running test suite...\n\n";
  
  (* Use default configuration *)
  let (env, domain, facts, funcs) = get_default_config () in
  
  let test_cases = [
    ("1. Simple Access Control",
     "policy starts\n\
      forall p, d. (inrole(p, @physician) and treats(p, d)) implies canAccess(p, d)\n\
      policy ends");
    
    ("2. HIPAA Consent Check",
     "policy starts\n\
      forall physician, patient. \n\
        (inrole(physician, @physician) and treats(physician, patient))\n\
        implies hasConsent(patient, physician)\n\
      policy ends");
    
    ("3. Family Member Disclosure",
     "policy starts\n\
      forall provider, patient, family, phi.\n\
        (disclose(provider, family, phi) and familyMember(family, patient))\n\
        implies (hasConsent(patient, family) or incapacitated(patient))\n\
      policy ends");
    
    ("4. Person Training Rule",
     "policy starts\n\
      forall x. Person(x) implies trained(x)\n\
      policy ends");
    
    ("5. Admin Access",
     "policy starts\n\
      forall user, resource. \n\
        (hasRole(user, @admin) and active(user))\n\
        implies canModify(user, resource)\n\
      policy ends");
    
    ("6. Existential Quantification",
     "policy starts\n\
      exists d. Doctor(d) and trained(d)\n\
      policy ends");
    
    ("7. Negation",
     "policy starts\n\
      forall user. not(suspended(user)) implies active(user)\n\
      policy ends");
    
    ("8. Complex HIPAA Rule",
     "policy starts\n\
      forall p1, p2, q, r. \n\
        (disclose(p1, p2, q, r) and inrole(p1, @physician) and \n\
         inrole(p2, @patient) and p2 = q)\n\
        implies authorized(p1, p2, q, r)\n\
      policy ends");
  ] in
  
  List.iteri (fun i (name, input) ->
    Printf.printf "==============================================\n";
    Printf.printf "Test %d: %s\n" (i + 1) name;
    Printf.printf "==============================================\n";
    Printf.printf "Input:\n%s\n" input;
    Printf.printf "----------------------------------------------\n";
    
    process_input input env domain facts funcs;
    Printf.printf "\n"
  ) test_cases

(* ============================================ *)
(* INTERACTIVE MODE                            *)
(* ============================================ *)

let run_interactive_mode () =
  Printf.printf "=== Policy Checker Interactive Mode ===\n";
  Printf.printf "Enter policy formulas (Ctrl+D to finish):\n\n";
  
  let (env, domain, facts, funcs) = get_default_config () in
  
  let buffer = Buffer.create 256 in
  try
    while true do
      let line = read_line () in
      Buffer.add_string buffer line;
      Buffer.add_char buffer '\n';
    done
  with End_of_file ->
    let input = Buffer.contents buffer in
    if String.length input > 0 then
      process_input input env domain facts funcs
    else
      Printf.printf "No input provided.\n"

(* ============================================ *)
(* MAIN EXECUTION                              *)
(* ============================================ *)

let print_usage () =
  Printf.printf "Policy Checker - Usage:\n\n";
  Printf.printf "  %s --json           Run in JSON mode (for Python integration)\n" Sys.argv.(0);
  Printf.printf "  %s --file <path>    Process a policy file\n" Sys.argv.(0);
  Printf.printf "  %s --test           Run test suite\n" Sys.argv.(0);
  Printf.printf "  %s --interactive    Run in interactive mode\n" Sys.argv.(0);
  Printf.printf "  %s --help           Show this help message\n\n" Sys.argv.(0);
  Printf.printf "Examples:\n";
  Printf.printf "  echo '{\"formula\":\"...\",\"facts\":{...}}' | %s --json\n" Sys.argv.(0);
  Printf.printf "  %s --file policy.txt\n" Sys.argv.(0);
  Printf.printf "  %s --test\n" Sys.argv.(0);
  Printf.printf "  %s --interactive\n\n" Sys.argv.(0)

let () =
  (* Parse command-line arguments *)
  let mode = 
    if Array.length Sys.argv > 1 then Sys.argv.(1)
    else ""
  in
  
  match mode with
  | "--json" | "-j" ->
      (* JSON mode for Python integration *)
      let env = get_type_environment () in
      run_json_mode env
  
  | "--file" | "-f" when Array.length Sys.argv > 2 ->
      (* File processing mode *)
      run_file_mode Sys.argv.(2)
  
  | "--test" | "-t" ->
      (* Test mode *)
      run_test_mode ()
  
  | "--interactive" | "-i" ->
      (* Interactive mode *)
      run_interactive_mode ()
  
  | "--help" | "-h" ->
      print_usage ()
  
  | "" ->
      (* Default: run test mode *)
      run_test_mode ()
  
  | _ ->
      Printf.printf "Unknown mode: %s\n" mode;
      Printf.printf "Use --help for usage information\n";
      exit 1