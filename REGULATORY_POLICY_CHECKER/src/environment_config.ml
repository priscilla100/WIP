(* environment_config.ml - Modern data-driven configuration *)

open Ast

(* ============================================ *)
(* UNIFIED CONFIGURATION MANAGER               *)
(* ============================================ *)

module Config = struct
  type runtime_config = {
    data_dir: string;
    policies_dir: string;
    cache_enabled: bool;
  }
  
  type runtime_environment = {
    type_env: type_environment;
    domain: domain_db;
    facts: facts_db;
    functions: functions_db;
    policy_manager: Policy_loader.policy_manager;
  }
  
  let get_executable_dir () : string =
  (* Get directory where executable is located *)
  let exe_path = Sys.executable_name in
  Filename.dirname exe_path

let default_config () : runtime_config =
  let exe_dir = get_executable_dir () in
  {
    data_dir = Filename.concat exe_dir "data";
    policies_dir = Filename.concat exe_dir "policies";
    cache_enabled = true;
  }
let load_multi_regulation_types (data_dir: string) : type_environment =
    (* List of type system files to load *)
    let type_files = [
      Filename.concat data_dir "hipaa_types.txt";
      Filename.concat data_dir "gdpr_types.txt";
      Filename.concat data_dir "ccpa_types.txt";
      (* Add more regulations here as needed *)
    ] in
    
    (* Load all files that exist *)
    let systems = List.filter_map (fun file ->
      if Sys.file_exists file then
        Some (Type_system_db.load_type_system_file file)
      else begin
        (* Warn but continue if file doesn't exist *)
        Printf.eprintf "Warning: Type system file not found: %s\n" file;
        None
      end
    ) type_files in
    
    (* Merge all type systems *)
    let merged = Type_system_db.merge_type_systems systems in
    
    (* Convert to type environment *)
    Type_system_db.to_type_environment merged
  (* let default_config () : runtime_config =
    {
      data_dir = "data";
      policies_dir = "policies";
      cache_enabled = true;
    } *)
  
  (* Initialize complete runtime environment *)
  let initialize ?(config = default_config ()) () : runtime_environment =
    (* Load type system - NOW SUPPORTS MULTIPLE FILES *)
    let type_env = load_multi_regulation_types config.data_dir in
    
    (* Load domain, facts, functions (UNCHANGED) *)
    let domain_db = Data_loaders.DomainDB.load_from_file 
      (Filename.concat config.data_dir "domain.txt") in
    let facts_db = Data_loaders.FactsDB.load_from_file 
      (Filename.concat config.data_dir "facts.txt") in
    let funcs_db = Data_loaders.FunctionsDB.load_from_file 
      (Filename.concat config.data_dir "functions.txt") in
    
    (* Initialize policy manager (UNCHANGED) *)
    let policy_manager = Policy_loader.create_manager config.policies_dir in
    Policy_loader.reload_all policy_manager;
    
    {
      type_env;
      domain = Data_loaders.DomainDB.to_domain_db domain_db;
      facts = Data_loaders.FactsDB.to_facts_db facts_db;
      functions = Data_loaders.FunctionsDB.to_functions_db funcs_db;
      policy_manager;
    }
  
  (* Reload all data from files *)
  let reload_all (env: runtime_environment) : runtime_environment =
    let config = default_config () in
    initialize ~config ()
  
  (* Reload only policies *)
  let reload_policies (env: runtime_environment) : unit =
    Policy_loader.reload_all env.policy_manager
  
  (* Reload specific regulation *)
  let reload_regulation (env: runtime_environment) (regulation: string) : unit =
    Policy_loader.reload_single env.policy_manager regulation
  
  (* Get all policies *)
  let get_all_policies (env: runtime_environment) : Policy_loader.policy_database =
    Policy_loader.get_combined_database env.policy_manager
  
  (* Get policies for specific regulation *)
  let get_policies_for_regulation (env: runtime_environment) (regulation: string) 
      : Policy_loader.policy_database =
    let all_policies = get_all_policies env in
    Policy_loader.filter_by_regulation regulation all_policies
end

(* ============================================ *)
(* CACHED CONFIGURATION (PERFORMANCE)          *)
(* ============================================ *)

module CachedConfig = struct
  type t = {
    data_cache: Data_loaders.DataCache.t;
    policy_manager: Policy_loader.policy_manager;
    config: Config.runtime_config;
  }
  
  let create ?(config = Config.default_config ()) () : t =
    let data_config = Data_loaders.DataLoader.{
      type_system_file = Filename.concat config.data_dir "type_system.txt";
      domain_file = Filename.concat config.data_dir "domain.txt";
      facts_file = Filename.concat config.data_dir "facts.txt";
      functions_file = Filename.concat config.data_dir "functions.txt";
    } in
    
    let data_cache = Data_loaders.DataCache.create data_config in
    let policy_manager = Policy_loader.create_manager config.policies_dir in
    
    { data_cache; policy_manager; config }
  
  let get_environment (cache: t) : Config.runtime_environment =
    let loaded_data = Data_loaders.DataCache.load cache.data_cache in
    Policy_loader.reload_all cache.policy_manager;
    
    {
      type_env = loaded_data.type_env;
      domain = loaded_data.domain;
      facts = loaded_data.facts;
      functions = loaded_data.functions;
      policy_manager = cache.policy_manager;
    }
  
  let force_reload (cache: t) : Config.runtime_environment =
    let loaded_data = Data_loaders.DataCache.reload cache.data_cache in
    Policy_loader.reload_all cache.policy_manager;
    
    {
      type_env = loaded_data.type_env;
      domain = loaded_data.domain;
      facts = loaded_data.facts;
      functions = loaded_data.functions;
      policy_manager = cache.policy_manager;
    }
end

(* ============================================ *)
(* BACKWARD COMPATIBILITY                      *)
(* ============================================ *)

(* For existing code that expects old interface *)
module Legacy = struct
  let initialize = Config.initialize
  
  let build_environment () : type_environment =
    let env = Config.initialize () in
    env.type_env
end