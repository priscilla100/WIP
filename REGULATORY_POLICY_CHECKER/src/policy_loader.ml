(* policy_loader.ml - Runtime policy loading from dedicated files *)

open Ast

(* ============================================ *)
(* POLICY METADATA AND STRUCTURE               *)
(* ============================================ *)

type policy_entry = {
  id: string;
  regulation: string;
  section: string;
  description: string;
  formula: formula;
}

type policy_database = {
  name: string;
  version: string option;
  effective_date: string option;
  policies: policy_entry list;
}

(* ============================================ *)
(* FILE-BASED POLICY LOADING                   *)
(* ============================================ *)

(* Load and parse a .policy file *)
let load_policy_file (filename: string) : policy_file =
  let ic = open_in filename in
  let content = really_input_string ic (in_channel_length ic) in
  close_in ic;
  
  (* Use your existing parser - FIXED to use correct entry point *)
  let lexbuf = Lexing.from_string content in
  try
    Parser.main Lexer.read lexbuf  (* Changed from Parser.policy_file *)
  with
  | Parser.Error ->
      let pos = lexbuf.Lexing.lex_curr_p in
      failwith (Printf.sprintf "Parse error at line %d, column %d in file %s"
        pos.Lexing.pos_lnum
        (pos.Lexing.pos_cnum - pos.Lexing.pos_bol)
        filename)
  | e ->
      failwith (Printf.sprintf "Error parsing %s: %s" filename (Printexc.to_string e))

(* Extract metadata from parsed policy file *)
let extract_metadata (pf: policy_file) : (string * string option * string option) =
  match pf.metadata with
  | Some m -> (m.name, m.version, m.effective_date)
  | None -> ("Unknown", None, None)

(* Convert parsed formulas into structured policy entries *)
let formulas_to_entries 
    (regulation: string) 
    (formulas: formula list) 
    : policy_entry list =
  
  List.mapi (fun idx formula ->
    let (section, desc, core_formula) = 
      match formula with
      | Annotated (f, annotation) ->
          (* Parse annotation like "§164.502(a)(1) - Description" *)
          let parts = String.split_on_char '-' annotation in
          let section = String.trim (List.hd parts) in
          let desc = 
            if List.length parts > 1 
            then String.trim (String.concat "-" (List.tl parts))
            else "No description"
          in
          (section, desc, f)
      | f -> 
          (Printf.sprintf "Policy-%d" idx, "Unannotated policy", f)
    in
    
    {
      id = Printf.sprintf "%s-%d" regulation idx;
      regulation;
      section;
      description = desc;
      formula = core_formula;
    }
  ) formulas

(* Load database from a .policy file *)
let load_database (filename: string) : policy_database =
  let pf = load_policy_file filename in
  let (name, version, effective_date) = extract_metadata pf in
  let regulation = 
    match pf.metadata with
    | Some m -> m.name
    | None -> Filename.basename filename
  in
  
  {
    name;
    version;
    effective_date;
    policies = formulas_to_entries regulation pf.policies;
  }

(* ============================================ *)
(* DIRECTORY-BASED POLICY MANAGEMENT           *)
(* ============================================ *)

(* Load all .policy files from a directory *)
let load_all_from_directory (dir: string) : policy_database list =
  if not (Sys.file_exists dir && Sys.is_directory dir) then
    []
  else
    let files = Sys.readdir dir in
    let policy_files = Array.to_list files
      |> List.filter (fun f -> Filename.check_suffix f ".policy")
      |> List.map (fun f -> Filename.concat dir f)
    in
    List.filter_map (fun f ->
      try Some (load_database f)
      with e ->
        Printf.eprintf "Warning: Failed to load %s: %s\n" f (Printexc.to_string e);
        None
    ) policy_files

(* Merge multiple databases into one *)
let merge_databases (dbs: policy_database list) : policy_database =
  let all_policies = List.concat_map (fun db -> db.policies) dbs in
  {
    name = "Combined Regulatory Compliance";
    version = Some "1.0";
    effective_date = None;
    policies = all_policies;
  }

(* ============================================ *)
(* QUERY AND RETRIEVAL FUNCTIONS               *)
(* ============================================ *)

let find_policy_by_id (id: string) (db: policy_database) : policy_entry option =
  List.find_opt (fun p -> p.id = id) db.policies

let filter_by_regulation (reg: string) (db: policy_database) : policy_database =
  {
    db with
    name = reg;
    policies = List.filter (fun p -> p.regulation = reg) db.policies;
  }

let filter_by_section (section: string) (db: policy_database) : policy_entry list =
  List.filter (fun p -> String.equal p.section section) db.policies

let list_all_policy_ids (db: policy_database) : string list =
  List.map (fun p -> p.id) db.policies

let list_all_sections (db: policy_database) : string list =
  List.map (fun p -> p.section) db.policies
  |> List.sort_uniq String.compare

(* ============================================ *)
(* CACHING FOR PERFORMANCE                     *)
(* ============================================ *)

module PolicyCache = struct
  type t = {
    mutable cache: (string, policy_database) Hashtbl.t;
    mutable last_modified: (string, float) Hashtbl.t;
  }
  
  let create () : t = {
    cache = Hashtbl.create 16;
    last_modified = Hashtbl.create 16;
  }
  
  let file_modified_time (filename: string) : float =
    try (Unix.stat filename).Unix.st_mtime
    with _ -> 0.0
  
  let needs_reload (cache: t) (filename: string) : bool =
    if not (Hashtbl.mem cache.cache filename) then true
    else
      let cached_time = Hashtbl.find cache.last_modified filename in
      let current_time = file_modified_time filename in
      current_time > cached_time
  
  let load (cache: t) (filename: string) : policy_database =
    if needs_reload cache filename then begin
      let db = load_database filename in
      let mtime = file_modified_time filename in
      Hashtbl.replace cache.cache filename db;
      Hashtbl.replace cache.last_modified filename mtime;
      db
    end else
      Hashtbl.find cache.cache filename
  
  let clear (cache: t) : unit =
    Hashtbl.clear cache.cache;
    Hashtbl.clear cache.last_modified
end

(* ============================================ *)
(* HOT-RELOAD SUPPORT                          *)
(* ============================================ *)

type policy_manager = {
  policy_dir: string;
  cache: PolicyCache.t;
  mutable databases: policy_database list;
}

let create_manager (dir: string) : policy_manager =
  {
    policy_dir = dir;
    cache = PolicyCache.create ();
    databases = [];
  }

let reload_all (manager: policy_manager) : unit =
  manager.databases <- load_all_from_directory manager.policy_dir

let get_combined_database (manager: policy_manager) : policy_database =
  merge_databases manager.databases

let reload_single (manager: policy_manager) (regulation: string) : unit =
  let filename = Filename.concat manager.policy_dir (regulation ^ ".policy") in
  if Sys.file_exists filename then
    try
      let db = PolicyCache.load manager.cache filename in
      manager.databases <- db :: (List.filter (fun d -> d.name <> regulation) manager.databases)
    with e ->
      Printf.eprintf "Warning: Failed to reload %s: %s\n" regulation (Printexc.to_string e)

(* ============================================ *)
(* USAGE EXAMPLE                               *)
(* ============================================ *)

let example_usage () =
  (* Initialize manager pointing to policies directory *)
  let manager = create_manager "policies/" in
  
  (* Load all policies *)
  reload_all manager;
  
  (* Get combined database *)
  let db = get_combined_database manager in
  Printf.printf "Loaded %d policies\n" (List.length db.policies);
  
  (* Query specific policy *)
  match find_policy_by_id "HIPAA-0" db with
  | Some policy -> 
      Printf.printf "Found: %s - %s\n" policy.section policy.description
  | None -> 
      Printf.printf "Policy not found\n";
  
  (* Hot-reload a specific regulation *)
  reload_single manager "HIPAA";
  Printf.printf "Reloaded HIPAA policies\n"