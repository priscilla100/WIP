(* environment_config.ml - Centralized configuration for types, facts, and functions *)

open Type_checker
open Evaluator

(* ============================================ *)
(* TYPE SYSTEM CONFIGURATION                   *)
(* ============================================ *)

module TypeSystem = struct
  (* Define all predicates used in the system *)
  let predicates : predicate_signature list = [
    (* Core predicates *)
    { name = "True"; arg_types = []; return_type = TBool };
    { name = "False"; arg_types = []; return_type = TBool };
    
    (* HIPAA-related predicates *)
    { name = "disclose"; arg_types = [TEntity; TEntity; TEntity; TEntity]; return_type = TBool };
    { name = "disclose"; arg_types = [TEntity; TEntity; TEntity]; return_type = TBool };
    { name = "inrole"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "authorized"; arg_types = [TEntity; TEntity; TEntity; TEntity]; return_type = TBool };
    { name = "coveredEntity"; arg_types = [TEntity]; return_type = TBool };
    { name = "minimumNecessary"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "requiredByLaw"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "hasConsent"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "hasConsent"; arg_types = [TEntity; TEntity; TEntity]; return_type = TBool };
    { name = "familyMember"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "involvedInCare"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "patientObjected"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "incapacitated"; arg_types = [TEntity]; return_type = TBool };
    { name = "treats"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "owns"; arg_types = [TEntity; TEntity]; return_type = TBool };
    
    (* GDPR-related predicates *)
    { name = "processes"; arg_types = [TEntity; TEntity; TEntity]; return_type = TBool };
    { name = "holds"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "encryptionEnabled"; arg_types = [TEntity]; return_type = TBool };
    { name = "dataProtectionOfficerApproved"; arg_types = [TEntity]; return_type = TBool };
    { name = "purposeLimited"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "safeCountry"; arg_types = [TEntity]; return_type = TBool };
    { name = "dataLocation"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "gdprCompliant"; arg_types = [TEntity]; return_type = TBool };
    
    (* SOX-related predicates *)
    { name = "publishes"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "certified"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "operates"; arg_types = [TEntity]; return_type = TBool };
    { name = "hasInternalControls"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "assessed"; arg_types = [TEntity]; return_type = TBool };
    { name = "auditRecord"; arg_types = [TEntity]; return_type = TBool };
    { name = "preserved"; arg_types = [TEntity; TEntity]; return_type = TBool };
    
    (* Access control predicates *)
    { name = "hasRole"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "suspended"; arg_types = [TEntity]; return_type = TBool };
    { name = "active"; arg_types = [TEntity]; return_type = TBool };
    { name = "canAccess"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "canView"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "canModify"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "canDisclose"; arg_types = [TEntity; TEntity; TEntity; TEntity]; return_type = TBool };
    { name = "authorizedAccess"; arg_types = [TEntity; TEntity]; return_type = TBool };
    
    (* Workflow predicates *)
    { name = "approved"; arg_types = [TEntity]; return_type = TBool };
    { name = "trained"; arg_types = [TEntity]; return_type = TBool };
    { name = "manages"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "canLead"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "hasAuthority"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "willApprove"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "priority"; arg_types = [TEntity; TEntity]; return_type = TBool };
    
    (* Document/Data predicates *)
    { name = "isPublished"; arg_types = [TEntity]; return_type = TBool };
    { name = "hasApproval"; arg_types = [TEntity]; return_type = TBool };
    { name = "visibilitySet"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "verified"; arg_types = [TEntity]; return_type = TBool };
    
    (* Session/Transaction predicates *)
    { name = "loggedIn"; arg_types = [TEntity]; return_type = TBool };
    { name = "inactiveSession"; arg_types = [TEntity]; return_type = TBool };
    { name = "canTransact"; arg_types = [TEntity]; return_type = TBool };
    { name = "fraud"; arg_types = [TEntity]; return_type = TBool };
    
    (* Messaging predicates *)
    { name = "send"; arg_types = [TEntity; TEntity; TEntity]; return_type = TBool };
    { name = "contains"; arg_types = [TEntity; TEntity; TEntity]; return_type = TBool };
    { name = "purpose"; arg_types = [TEntity]; return_type = TBool };
    
    (* Generic predicates *)
    { name = "Person"; arg_types = [TEntity]; return_type = TBool };
    { name = "Doctor"; arg_types = [TEntity]; return_type = TBool };
    { name = "Resource"; arg_types = [TEntity]; return_type = TBool };
    { name = "ProtectedHealthInformation"; arg_types = [TEntity]; return_type = TBool };
    { name = "Approved"; arg_types = [TEntity]; return_type = TBool };
    { name = "emergency"; arg_types = [TEntity]; return_type = TBool };
    { name = "canApprove"; arg_types = [TEntity]; return_type = TBool };
    { name = "canProcessData"; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "canProcessPersonalData"; arg_types = [TEntity; TEntity; TEntity]; return_type = TBool };
    
    (* Comparison operators *)
    { name = "="; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "="; arg_types = [TInt; TInt]; return_type = TBool };
    { name = "!="; arg_types = [TEntity; TEntity]; return_type = TBool };
    { name = "!="; arg_types = [TInt; TInt]; return_type = TBool };
    { name = "<"; arg_types = [TInt; TInt]; return_type = TBool };
    { name = "<="; arg_types = [TInt; TInt]; return_type = TBool };
    { name = ">"; arg_types = [TInt; TInt]; return_type = TBool };
    { name = ">="; arg_types = [TInt; TInt]; return_type = TBool };
  ]
  
  (* Define all functions *)
  let functions : function_signature list = [
    { name = "age"; arg_types = [TEntity]; return_type = TInt };
    { name = "salary"; arg_types = [TEntity]; return_type = TInt };
  ]
  
  (* Define all constants with their types *)
  let constants : (string * expr_type) list = [
    (* Roles *)
    ("physician", TEntity);
    ("doctor", TEntity);
    ("patient", TEntity);
    ("admin", TEntity);
    ("administrator", TEntity);
    ("manager", TEntity);
    ("nurse", TEntity);
    
    (* People *)
    ("alice", TEntity);
    ("bob", TEntity);
    ("charlie", TEntity);
    ("diana", TEntity);
    ("Omar", TEntity);
    ("Priscilla", TEntity);
    ("Hasan", TEntity);
    ("Rob", TEntity);
    ("dr_smith", TEntity);
    ("grandma", TEntity);
    ("user", TEntity);
    
    (* Organizations *)
    ("company1", TEntity);
    ("company2", TEntity);
    ("messaging_system", TEntity);
    ("medical_system", TEntity);
    
    (* Resources/Data *)
    ("phi", TEntity);  (* Protected Health Information *)
    ("psi", TEntity);
    ("dm", TEntity);   (* Direct Message *)
    ("msg1", TEntity);
    ("msg2", TEntity);
    ("record", TEntity);
    ("document", TEntity);
    ("doc1", TEntity);
    ("doc2", TEntity);
    ("resource1", TEntity);
    ("resource2", TEntity);
    ("medical_data", TEntity);
    ("personal_data", TEntity);
    ("public_data", TEntity);
    
    (* Purposes *)
    ("authorization", TEntity);
    ("notification", TEntity);
    ("audit", TEntity);
    ("treatment", TEntity);
    ("research", TEntity);
    
    (* Priorities/Levels *)
    ("high", TEntity);
    ("low", TEntity);
    ("confidential", TEntity);
    ("high_risk", TEntity);
    
    (* Locations *)
    ("EU", TEntity);
    
    (* Accounts/Requests *)
    ("account1", TEntity);
    ("account2", TEntity);
    ("req1", TEntity);
    ("req2", TEntity);
    ("req3", TEntity);
    ("patient_123", TEntity);
    
    (* Roles for comparison *)
    ("ceo", TEntity);
    ("cfo", TEntity);
    ("public", TEntity);
    
    (* Integer constants *)
    ("MAX_AGE", TInt);
    ("MIN_SALARY", TInt);
  ]
  
  (* Build the complete type environment *)
  let build_environment () : type_environment =
    { predicates; functions; constants }
end

(* ============================================ *)
(* FACTS DATABASE CONFIGURATION                *)
(* ============================================ *)

module FactsDB = struct
  (* Sample facts for testing *)
  let sample_facts : (string * string list) list = [
    (* People and roles *)
    ("Person", ["alice"]);
    ("Person", ["bob"]);
    ("Person", ["charlie"]);
    ("Doctor", ["alice"]);
    
    (* Role assignments *)
    ("inrole", ["alice"; "physician"]);
    ("inrole", ["bob"; "patient"]);
    ("inrole", ["charlie"; "patient"]);
    ("hasRole", ["alice"; "admin"]);
    ("hasRole", ["bob"; "manager"]);
    
    (* Status *)
    ("active", ["alice"]);
    ("active", ["bob"]);
    ("suspended", ["charlie"]);
    ("trained", ["alice"]);
    ("trained", ["bob"]);
    
    (* Relationships *)
    ("treats", ["alice"; "bob"]);
    ("manages", ["alice"; "bob"]);
    ("manages", ["bob"; "charlie"]);
    
    (* Consent and authorization *)
    ("hasConsent", ["bob"; "alice"]);
    ("hasConsent", ["bob"; "alice"; "medical_data"]);
    ("authorized", ["alice"; "bob"; "bob"; "medical_data"]);
    
    (* Disclosures *)
    ("disclose", ["alice"; "bob"; "medical_data"]);
    ("disclose", ["alice"; "bob"; "bob"; "medical_data"]);
    ("disclose", ["alice"; "charlie"; "charlie"; "medical_data"]);
    
    (* Approvals *)
    ("Approved", ["alice"]);
    ("Approved", ["bob"]);
    ("approved", ["company1"]);
    
    (* Family/Care relationships *)
    ("familyMember", ["grandma"; "bob"]);
    ("familyMember", ["grandma"; "patient_123"]);
    ("involvedInCare", ["grandma"; "bob"]);
    ("involvedInCare", ["grandma"; "patient_123"]);
    
    (* Messaging *)
    ("send", ["Omar"; "Priscilla"; "phi"]);
    ("send", ["Omar"; "Rob"; "phi"]);
    ("contains", ["Priscilla"; "Rob"; "phi"]);
    
    (* Workflow *)
    ("priority", ["req1"; "high"]);
    ("priority", ["req2"; "low"]);
    ("hasAuthority", ["alice"; "high"]);
    ("willApprove", ["alice"; "req1"]);
    
    (* GDPR compliance *)
    ("processes", ["company1"; "medical_data"; "treatment"]);
    ("holds", ["company1"; "medical_data"]);
    ("encryptionEnabled", ["company1"]);
    ("dataProtectionOfficerApproved", ["company1"]);
    
    (* Documents *)
    ("isPublished", ["doc1"]);
    ("hasApproval", ["doc1"]);
    ("visibilitySet", ["doc1"; "public"]);
    
    (* Accounts *)
    ("verified", ["account1"]);
    ("loggedIn", ["account1"]);
  ]
  
  (* Build facts database *)
  let build_facts_db () : facts_db =
    { facts = sample_facts }
  
  (* Helper: Add facts dynamically *)
  let add_fact (db: facts_db) (pred: string) (args: string list) : facts_db =
    { facts = (pred, args) :: db.facts }
  
  (* Helper: Create empty facts DB *)
  let empty () : facts_db =
    { facts = [] }
end

(* ============================================ *)
(* FUNCTION EVALUATION CONFIGURATION           *)
(* ============================================ *)

module FunctionsDB = struct
  (* Sample function values for testing *)
  let sample_functions : (string * string list * string) list = [
    ("age", ["alice"], "30");
    ("age", ["bob"], "25");
    ("age", ["charlie"], "28");
    ("age", ["doctor"], "40");
    ("age", ["patient"], "35");
    ("age", ["dr_smith"], "45");
    ("age", ["grandma"], "75");
    
    ("salary", ["alice"], "50000");
    ("salary", ["bob"], "40000");
    ("salary", ["charlie"], "45000");
  ]
  
  (* Build functions database *)
  let build_functions_db () : functions_db =
    { func_values = sample_functions }
  
  (* Helper: Add function value dynamically *)
  let add_function_value (db: functions_db) (fname: string) (args: string list) (result: string) : functions_db =
    { func_values = (fname, args, result) :: db.func_values }
  
  (* Helper: Create empty functions DB *)
  let empty () : functions_db =
    { func_values = [] }
end

(* ============================================ *)
(* DOMAIN CONFIGURATION                        *)
(* ============================================ *)

module DomainDB = struct
  (* All entities in the domain *)
  let all_entities : string list = [
    (* People *)
    "alice"; "bob"; "charlie"; "diana";
    "Omar"; "Priscilla"; "Hasan"; "Rob";
    "dr_smith"; "grandma"; "user";
    
    (* Roles *)
    "physician"; "doctor"; "patient"; "admin"; "administrator";
    "manager"; "nurse"; "ceo"; "cfo";
    
    (* Organizations *)
    "company1"; "company2"; "messaging_system"; "medical_system";
    
    (* Resources *)
    "phi"; "psi"; "dm"; "msg1"; "msg2";
    "record"; "document"; "doc1"; "doc2";
    "resource1"; "resource2";
    "medical_data"; "personal_data"; "public_data";
    
    (* Purposes *)
    "authorization"; "notification"; "audit"; "treatment"; "research";
    
    (* Levels *)
    "high"; "low"; "confidential"; "high_risk"; "public";
    
    (* Locations *)
    "EU";
    
    (* Other *)
    "account1"; "account2"; "req1"; "req2"; "req3"; "patient_123";
  ]
  
  (* Build domain database *)
  let build_domain_db () : domain_db =
    { entities = all_entities }
  
  (* Helper: Add entity dynamically *)
  let add_entity (db: domain_db) (entity: string) : domain_db =
    if List.mem entity db.entities then db
    else { entities = entity :: db.entities }
  
  (* Helper: Extract entities from facts automatically *)
  let extract_from_facts (facts: facts_db) : domain_db =
    let entities = List.fold_left (fun acc (_, args) ->
      List.fold_left (fun acc2 arg ->
        if List.mem arg acc2 then acc2 else arg :: acc2
      ) acc args
    ) [] facts.facts in
    { entities = List.sort_uniq String.compare entities }
end

(* ============================================ *)
(* COMPLETE CONFIGURATION                      *)
(* ============================================ *)

module Config = struct
  (* Initialize everything with default values *)
  let initialize () : (type_environment * domain_db * facts_db * functions_db) =
    let env = TypeSystem.build_environment () in
    let domain = DomainDB.build_domain_db () in
    let facts = FactsDB.build_facts_db () in
    let funcs = FunctionsDB.build_functions_db () in
    (env, domain, facts, funcs)
  
  (* Initialize with custom facts *)
  let initialize_with_facts (custom_facts: facts_db) : (type_environment * domain_db * facts_db * functions_db) =
    let env = TypeSystem.build_environment () in
    let domain = DomainDB.extract_from_facts custom_facts in
    let funcs = FunctionsDB.build_functions_db () in
    (env, domain, custom_facts, funcs)
  
  (* Initialize empty (for custom setup) *)
  let initialize_empty () : (type_environment * domain_db * facts_db * functions_db) =
    let env = TypeSystem.build_environment () in
    let domain = { entities = [] } in
    let facts = FactsDB.empty () in
    let funcs = FunctionsDB.empty () in
    (env, domain, facts, funcs)
end

(* ============================================ *)
(* PUBLIC API                                  *)
(* ============================================ *)

(* Get default configuration *)
let get_default_config = Config.initialize

(* Get configuration with custom facts *)
let get_config_with_facts = Config.initialize_with_facts

(* Get empty configuration *)
let get_empty_config = Config.initialize_empty

(* Individual database builders *)
let get_type_environment = TypeSystem.build_environment
let get_domain_db = DomainDB.build_domain_db
let get_facts_db = FactsDB.build_facts_db
let get_functions_db = FunctionsDB.build_functions_db