(* data_loaders.ml - Load domains, facts, and functions from files *)

open Ast

(* ============================================ *)
(* DOMAIN DATABASE                             *)
(* ============================================ *)

module DomainDB = struct
  type t = {
    entities: string list;
  }
  
  (* File format: One entity per line
     alice
     bob
     charlie
     dr_smith
  *)
  let load_from_file (filename: string) : t =
    if not (Sys.file_exists filename) then
      { entities = [] }
    else
      let ic = open_in filename in
      let entities = ref [] in
      (try
        while true do
          let line = String.trim (input_line ic) in
          if line <> "" && String.get line 0 <> '#' then
            entities := line :: !entities
        done
      with End_of_file -> close_in ic);
      { entities = List.rev !entities }
  
  let to_domain_db (db: t) : domain_db =
    { entities = db.entities }
  
  let add_entity (db: t) (entity: string) : t =
    if List.mem entity db.entities then db
    else { entities = entity :: db.entities }
  
  let has_entity (db: t) (entity: string) : bool =
    List.mem entity db.entities
  
  let list_all (db: t) : string list =
    db.entities
end

(* ============================================ *)
(* FACTS DATABASE                              *)
(* ============================================ *)

module FactsDB = struct
  type t = {
    facts: (string * string list) list;
  }
  
  (* File format:
     # Predicate facts
     Person(alice)
     Person(bob)
     coveredEntity(hospital_a)
     hasConsent(alice, dr_smith, phi_123)
  *)
  let parse_fact_line (line: string) : (string * string list) option =
    try
      (* Remove whitespace *)
      let line = String.trim line in
      
      (* Find predicate name and arguments *)
      let paren_pos = String.index line '(' in
      let pred_name = String.sub line 0 paren_pos in
      let args_part = String.sub line (paren_pos + 1) (String.length line - paren_pos - 2) in
      
      (* Split arguments by comma *)
      let args = String.split_on_char ',' args_part
        |> List.map String.trim
        |> List.filter (fun s -> s <> "")
      in
      
      Some (pred_name, args)
    with _ -> None
  
  let load_from_file (filename: string) : t =
    if not (Sys.file_exists filename) then
      { facts = [] }
    else
      let ic = open_in filename in
      let facts = ref [] in
      (try
        while true do
          let line = String.trim (input_line ic) in
          if line <> "" && String.get line 0 <> '#' then
            match parse_fact_line line with
            | Some fact -> facts := fact :: !facts
            | None -> ()
        done
      with End_of_file -> close_in ic);
      { facts = List.rev !facts }
  
  let to_facts_db (db: t) : facts_db =
    { facts = db.facts }
  
  let add_fact (db: t) (pred: string) (args: string list) : t =
    { facts = (pred, args) :: db.facts }
  
  let find_facts (db: t) (pred: string) : string list list =
    List.filter_map (fun (p, args) ->
      if p = pred then Some args else None
    ) db.facts
  
  let has_fact (db: t) (pred: string) (args: string list) : bool =
    List.exists (fun (p, a) -> p = pred && a = args) db.facts
  
  let list_all_predicates (db: t) : string list =
    List.map fst db.facts
    |> List.sort_uniq String.compare
end

(* ============================================ *)
(* FUNCTIONS DATABASE                          *)
(* ============================================ *)

module FunctionsDB = struct
  type t = {
    func_values: (string * string list * string) list;
  }
  
  (* File format:
     # Function values
     age(alice) = 30
     age(bob) = 25
     salary(alice) = 75000
     distance(hospital_a, alice) = 5
  *)
  let parse_function_line (line: string) : (string * string list * string) option =
    try
      let parts = String.split_on_char '=' line in
      if List.length parts <> 2 then None
      else
        let left = String.trim (List.nth parts 0) in
        let result = String.trim (List.nth parts 1) in
        
        (* Parse left side: fname(arg1, arg2, ...) *)
        let paren_pos = String.index left '(' in
        let fname = String.sub left 0 paren_pos in
        let args_part = String.sub left (paren_pos + 1) (String.length left - paren_pos - 2) in
        
        let args = String.split_on_char ',' args_part
          |> List.map String.trim
          |> List.filter (fun s -> s <> "")
        in
        
        Some (fname, args, result)
    with _ -> None
  
  let load_from_file (filename: string) : t =
    if not (Sys.file_exists filename) then
      { func_values = [] }
    else
      let ic = open_in filename in
      let func_values = ref [] in
      (try
        while true do
          let line = String.trim (input_line ic) in
          if line <> "" && String.get line 0 <> '#' then
            match parse_function_line line with
            | Some func_val -> func_values := func_val :: !func_values
            | None -> ()
        done
      with End_of_file -> close_in ic);
      { func_values = List.rev !func_values }
  
  let to_functions_db (db: t) : functions_db =
    { func_values = db.func_values }
  
  let add_function_value (db: t) (fname: string) (args: string list) (result: string) : t =
    { func_values = (fname, args, result) :: db.func_values }
  
  let lookup (db: t) (fname: string) (args: string list) : string option =
    List.find_map (fun (f, a, r) ->
      if f = fname && a = args then Some r else None
    ) db.func_values
  
  let list_all_functions (db: t) : string list =
    List.map (fun (f, _, _) -> f) db.func_values
    |> List.sort_uniq String.compare
end

(* ============================================ *)
(* UNIFIED LOADER                              *)
(* ============================================ *)

module DataLoader = struct
  type config = {
    type_system_file: string;
    domain_file: string;
    facts_file: string;
    functions_file: string;
  }
  
  type loaded_data = {
    type_env: type_environment;
    domain: domain_db;
    facts: facts_db;
    functions: functions_db;
  }
  
  let load_all (config: config) : loaded_data =
    (* Load type system *)
    let type_db = Type_system_db.load_type_system_file config.type_system_file in
    let type_env = Type_system_db.to_type_environment type_db in
    
    (* Load domain *)
    let domain_loader = DomainDB.load_from_file config.domain_file in
    let domain = DomainDB.to_domain_db domain_loader in
    
    (* Load facts *)
    let facts_loader = FactsDB.load_from_file config.facts_file in
    let facts = FactsDB.to_facts_db facts_loader in
    
    (* Load functions *)
    let functions_loader = FunctionsDB.load_from_file config.functions_file in
    let functions = FunctionsDB.to_functions_db functions_loader in
    
    { type_env; domain; facts; functions }
  
  let default_config () : config =
    {
      type_system_file = "data/type_system.txt";
      domain_file = "data/domain.txt";
      facts_file = "data/facts.txt";
      functions_file = "data/functions.txt";
    }
end

(* ============================================ *)
(* CACHING LAYER                               *)
(* ============================================ *)

module DataCache = struct
  type t = {
    mutable data: DataLoader.loaded_data option;
    config: DataLoader.config;
    mutable last_modified: float;
  }
  
  let create (config: DataLoader.config) : t =
    { data = None; config; last_modified = 0.0 }
  
  let get_latest_modification_time (config: DataLoader.config) : float =
    let files = [
      config.type_system_file;
      config.domain_file;
      config.facts_file;
      config.functions_file;
    ] in
    List.fold_left (fun acc file ->
      try
        let mtime = (Unix.stat file).Unix.st_mtime in
        max acc mtime
      with _ -> acc
    ) 0.0 files
  
  let needs_reload (cache: t) : bool =
    let current_time = get_latest_modification_time cache.config in
    current_time > cache.last_modified
  
  let load (cache: t) : DataLoader.loaded_data =
    if needs_reload cache || cache.data = None then begin
      let data = DataLoader.load_all cache.config in
      cache.data <- Some data;
      cache.last_modified <- get_latest_modification_time cache.config;
      data
    end else
      match cache.data with
      | Some data -> data
      | None -> failwith "Unexpected: cache.data is None"
  
  let reload (cache: t) : DataLoader.loaded_data =
    let data = DataLoader.load_all cache.config in
    cache.data <- Some data;
    cache.last_modified <- get_latest_modification_time cache.config;
    data
end