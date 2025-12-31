(* type_system_db.ml - Load type system from external files *)

(* ============================================ *)
(* TYPE SYSTEM DATABASE STRUCTURE              *)
(* ============================================ *)

type type_system_db = {
  predicates: Ast.predicate_signature list;
  functions: Ast.function_signature list;
  constants: (string * Ast.expr_type) list;
}


(* ============================================ *)
(* FILE FORMAT PARSER                          *)
(* ============================================ *)

(* Parse type from string: "Entity", "PHI", "Bool", "Int" *)
let parse_type (s: string) : Ast.expr_type =
  match String.trim s with
  | "Bool" -> Ast.TBool
  | "Int" -> Ast.TInt
  | "String" -> Ast.TString
  | custom -> Ast.TCustom custom

(* Parse predicate signature line:
   "coveredEntity : Entity -> Bool"
   "disclose : Entity Entity PHI -> Bool" *)
let parse_predicate_line (line: string) : Ast.predicate_signature option =
  try
    let parts = String.split_on_char ':' line in
    if List.length parts <> 2 then None
    else
      let name = String.trim (List.nth parts 0) in
      let type_part = String.trim (List.nth parts 1) in
      let type_tokens = String.split_on_char ' ' type_part
        |> List.map String.trim
        |> List.filter (fun s -> s <> "" && s <> "->")
      in
      
      (* Last token is return type, rest are arg types *)
      let return_type = parse_type (List.nth type_tokens (List.length type_tokens - 1)) in
      let arg_types = List.init (List.length type_tokens - 1) (fun i -> 
        parse_type (List.nth type_tokens i)
      ) in
      
      Some { Ast.name; arg_types; return_type }
  with _ -> None

(* Parse function signature line:
   "age : Entity -> Int" *)
let parse_function_line (line: string) : Ast.function_signature option =
  try
    let parts = String.split_on_char ':' line in
    if List.length parts <> 2 then None
    else
      let name = String.trim (List.nth parts 0) in
      let type_part = String.trim (List.nth parts 1) in
      let type_tokens = String.split_on_char ' ' type_part
        |> List.map String.trim
        |> List.filter (fun s -> s <> "" && s <> "->")
      in
      
      let return_type = parse_type (List.nth type_tokens (List.length type_tokens - 1)) in
      let arg_types = List.init (List.length type_tokens - 1) (fun i -> 
        parse_type (List.nth type_tokens i)
      ) in
      
      Some { Ast.name; arg_types; return_type }
  with _ -> None

(* Parse constant line:
   "physician : Entity" *)
let parse_constant_line (line: string) : (string * Ast.expr_type) option =
  try
    let parts = String.split_on_char ':' line in
    if List.length parts <> 2 then None
    else
      let name = String.trim (List.nth parts 0) in
      let type_str = String.trim (List.nth parts 1) in
      Some (name, parse_type type_str)
  with _ -> None

(* ============================================ *)
(* FILE LOADER                                 *)
(* ============================================ *)

(* Load type system from file format:
   
   PREDICATES
   coveredEntity : Entity -> Bool
   disclose : Entity Entity PHI -> Bool
   
   FUNCTIONS
   age : Entity -> Int
   salary : Entity -> Int
   
   CONSTANTS
   physician : Entity
   hospital : Entity
*)
let load_type_system_file (filename: string) : type_system_db =
  if not (Sys.file_exists filename) then
    { predicates = []; functions = []; constants = [] }
  else
    let ic = open_in filename in
    let lines = ref [] in
    (try
      while true do
        lines := input_line ic :: !lines
      done
    with End_of_file -> close_in ic);
    
    let lines = List.rev !lines in
    
    let predicates = ref [] in
    let functions = ref [] in
    let constants = ref [] in
    let current_section = ref "" in
    
    List.iter (fun line ->
      let line = String.trim line in
      if line = "" || (String.length line > 0 && String.get line 0 = '#') then ()
      else if line = "PREDICATES" then current_section := "predicates"
      else if line = "FUNCTIONS" then current_section := "functions"
      else if line = "CONSTANTS" then current_section := "constants"
      else
        match !current_section with
        | "predicates" ->
            (match parse_predicate_line line with
             | Some pred -> predicates := pred :: !predicates
             | None -> ())
        | "functions" ->
            (match parse_function_line line with
             | Some func -> functions := func :: !functions
             | None -> ())
        | "constants" ->
            (match parse_constant_line line with
             | Some const -> constants := const :: !constants
             | None -> ())
        | _ -> ()
    ) lines;
    
    {
      predicates = List.rev !predicates;
      functions = List.rev !functions;
      constants = List.rev !constants;
    }

(* Convert to type_environment *)
let to_type_environment (db: type_system_db) : Ast.type_environment =
  {
    Ast.predicates = db.predicates;
    functions = db.functions;
    constants = db.constants;
  }

(* ============================================ *)
(* CACHE SUPPORT                               *)
(* ============================================ *)

module TypeSystemCache = struct
  type t = {
    mutable cache: type_system_db option;
    mutable filename: string;
    mutable last_modified: float;
  }
  
  let create (filename: string) : t =
    { cache = None; filename; last_modified = 0.0 }
  
  let file_modified_time (filename: string) : float =
    try (Unix.stat filename).Unix.st_mtime
    with _ -> 0.0
  
  let needs_reload (cache: t) : bool =
    let current_time = file_modified_time cache.filename in
    current_time > cache.last_modified
  
  let load (cache: t) : type_system_db =
    if needs_reload cache then begin
      let db = load_type_system_file cache.filename in
      cache.cache <- Some db;
      cache.last_modified <- file_modified_time cache.filename;
      db
    end else
      match cache.cache with
      | Some db -> db
      | None ->
          let db = load_type_system_file cache.filename in
          cache.cache <- Some db;
          cache.last_modified <- file_modified_time cache.filename;
          db
end

(* ============================================ *)
(* QUERY FUNCTIONS                             *)
(* ============================================ *)

let find_predicate (name: string) (db: type_system_db) : Ast.predicate_signature option =
  List.find_opt (fun (p : Ast.predicate_signature) -> p.name = name) db.predicates

let find_function (name: string) (db: type_system_db) : Ast.function_signature option =
  List.find_opt (fun (f : Ast.function_signature) -> f.name = name) db.functions

let find_constant (name: string) (db: type_system_db) : Ast.expr_type option =
  List.assoc_opt name db.constants

let list_all_predicates (db: type_system_db) : string list =
  List.map (fun (p : Ast.predicate_signature) -> p.name) db.predicates

let list_all_functions (db: type_system_db) : string list =
  List.map (fun (f : Ast.function_signature) -> f.name) db.functions


(* ============================================ *)
(* MERGE MULTIPLE TYPE SYSTEM FILES            *)
(* ============================================ *)
let merge_unique_by_name : type a. (a -> string) -> a list -> a list =
 fun key items ->
  List.sort_uniq
    (fun x y -> String.compare (key x) (key y))
    items

let merge_type_systems (systems: type_system_db list) : type_system_db =
  (* Helper: Remove duplicates based on name: use the generic merger with explicit key functions *)
  
  let unique_constants list =
    List.fold_left (fun acc (name, typ) ->
      if List.mem_assoc name acc then acc
      else (name, typ) :: acc
    ) [] list
    |> List.rev
  in
  
  {
    predicates = List.concat (List.map (fun s -> s.predicates) systems)
                 |> merge_unique_by_name (fun (p : Ast.predicate_signature) -> p.name);
    functions = List.concat (List.map (fun s -> s.functions) systems)
                |> merge_unique_by_name (fun (f : Ast.function_signature) -> f.name);
    constants = List.concat (List.map (fun s -> s.constants) systems)
                |> unique_constants;
  }