(* policy_databases.ml - Production-ready: Text-based policies *)

open Ast


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
(* STUDENT-FRIENDLY: POLICY TEXT STRINGS       *)
(* Students write policies here in text format *)
(* ============================================ *)

(* HIPAA Policies - Students can edit this text directly! *)
let hipaa_policy_text = {|
regulation "HIPAA Privacy Rule" version "2023.1" effective_date "2023-01-01"

type declaration starts
type Entity
type PHI
type Purpose
type declaration ends

policy starts

@["§164.502(a)(1) - Use and Disclosure of PHI"]
forall entity, phi.
  (coveredEntity(entity))
  implies
  (authorized(entity, phi) or requiredByLaw(entity, phi))
;

@["§164.502(b) - Minimum Necessary Standard"]
forall entity, phi, purpose.
  (coveredEntity(entity) and 
   disclose(entity, phi, purpose))
  implies
  minimumNecessary(phi, purpose)
;

@["§164.508(a) - Authorization Required"]
forall physician, patient, phi.
  (inrole(physician, @physician) and 
   disclose(physician, patient, phi))
  implies
  hasConsent(patient, physician, phi)
;

@["§164.510(b) - Family Member Disclosure"]
forall provider, patient, family, phi.
  (disclose(provider, family, phi) and 
   familyMember(family, patient) and
   involvedInCare(family, patient))
  implies
  (hasConsent(patient, family) or incapacitated(patient))
;

@["§164.524(a) - Individual Access Rights"]
forall patient, phi.
  owns(patient, phi)
  implies
  canAccess(patient, phi)

policy ends
|}

(* GDPR Policies - Students can edit this text directly! *)
let gdpr_policy_text = {|
regulation "GDPR" version "2016/679" effective_date "2018-05-25"

type declaration starts
type Entity
type PersonalData
type Purpose
type declaration ends

policy starts

@["Art. 5(1)(a) - Lawfulness, Fairness, Transparency"]
forall controller, subject, data, purpose.
  (processes(controller, subject, data, purpose))
  implies
  (lawfulBasis(controller, purpose) and 
   fairProcessing(controller, subject) and
   transparentProcessing(controller, subject, purpose))
;

@["Art. 5(1)(b) - Purpose Limitation"]
forall controller, data, purpose1, purpose2.
  (collectedFor(controller, data, purpose1) and 
   usedFor(controller, data, purpose2))
  implies
  (purpose1 = purpose2 or compatiblePurpose(purpose1, purpose2))
;

@["Art. 6(1)(a) - Consent"]
forall controller, subject, data, purpose.
  (processes(controller, subject, data, purpose) and
   legalBasis(controller, purpose, @consent))
  implies
  (hasConsent(subject, controller, data, purpose) and
   validConsent(subject, controller))
;

@["Art. 9(1) - Special Categories Prohibition"]
forall controller, subject, data.
  (specialCategory(data) and
   processes(controller, subject, data))
  implies
  not(allowed(controller, subject, data))
;

@["Art. 9(2)(a) - Exception: Explicit Consent"]
forall controller, subject, data.
  (specialCategory(data) and
   processes(controller, subject, data) and
   explicitConsent(subject, controller, data))
  implies
  allowed(controller, subject, data)

policy ends
|}

(* SOX Policies - Students can edit this text directly! *)
let sox_policy_text = {|
regulation "Sarbanes-Oxley Act" version "2002" effective_date "2002-07-30"

type declaration starts
type Entity
type Report
type Controls
type declaration ends

policy starts

@["§302 - Corporate Responsibility"]
forall company, report.
  (publishes(company, report))
  implies
  (certified(@ceo, report) and certified(@cfo, report))
;

@["§404 - Internal Controls Assessment"]
forall company, controls.
  (operates(company))
  implies
  (hasInternalControls(company, controls) and assessed(controls))
;

@["§802 - Record Retention"]
forall company, record.
  (auditRecord(record))
  implies
  G[0,7] preserved(company, record)

policy ends
|}


let parse_policy_text (text: string) (regulation_name: string) : policy_entry list =
  try
    (* Parse the text with lexer/parser *)
    let ast = Parser.main Lexer.read (Lexing.from_string text) in
    
    (* Extract regulation name from metadata if available *)
    let reg_name = match ast.metadata with
      | Some m -> m.name
      | None -> regulation_name
    in
    
    (* Convert each formula to a policy_entry *)
    List.mapi (fun idx formula ->
      (* Extract section and citation from @["..."] annotation *)
      let (section, description) = match formula with
        | Annotated (_, cite) ->
            (* Parse "§164.508(a) - Description" *)
            (match String.split_on_char '-' cite with
             | section :: desc_parts ->
                 let sec = String.trim section in
                 let desc = String.trim (String.concat "-" desc_parts) in
                 (sec, cite)
             | [] -> ("", cite))
        | _ -> ("", "")
      in
      
      (* Generate ID: REGULATION-SECTION-INDEX *)
      let section_clean = String.map (function
        | '\xA7' | '(' | ')' | '.' | ' ' | '[' | ']' -> '-'
        | c -> c
      ) section in
      
      let policy_id = 
        if section = "" then
          Printf.sprintf "%s-POLICY-%d" regulation_name idx
        else
          Printf.sprintf "%s-%s" regulation_name section_clean
      in
      
      {
        id = policy_id;
        regulation = reg_name;
        section = section;
        description = description;
        formula = formula;
      }
    ) ast.policies
    
  with e ->
    Printf.printf "⚠️  Error parsing %s policies: %s\n" regulation_name (Printexc.to_string e);
    []

(* ============================================ *)
(* BUILD POLICY DATABASES                      *)
(* ============================================ *)

let get_hipaa_policies () : policy_database =
  let policies = parse_policy_text hipaa_policy_text "HIPAA" in
  {
    name = "HIPAA Privacy Rule";
    version = Some "2023.1";
    effective_date = Some "2023-01-01";
    policies = policies;
  }

let get_gdpr_policies () : policy_database =
  let policies = parse_policy_text gdpr_policy_text "GDPR" in
  {
    name = "GDPR";
    version = Some "2016/679";
    effective_date = Some "2018-05-25";
    policies = policies;
  }

let get_sox_policies () : policy_database =
  let policies = parse_policy_text sox_policy_text "SOX" in
  {
    name = "Sarbanes-Oxley Act";
    version = Some "2002";
    effective_date = Some "2002-07-30";
    policies = policies;
  }

let get_all_policy_databases () : policy_database =
  let hipaa = get_hipaa_policies () in
  let gdpr = get_gdpr_policies () in
  let sox = get_sox_policies () in
  
  {
    name = "Combined Regulatory Compliance";
    version = Some "1.0";
    effective_date = None;
    policies = hipaa.policies @ gdpr.policies @ sox.policies;
  }


let find_policy_by_id (id: string) (db: policy_database) : policy_entry option =
  List.find_opt (fun p -> p.id = id) db.policies

let filter_by_regulation (reg: string) (db: policy_database) : policy_database =
  {
    db with
    name = reg;
    policies = List.filter (fun p -> p.regulation = reg) db.policies;
  }

let list_all_policy_ids (db: policy_database) : string list =
  List.map (fun p -> p.id) db.policies

(* ============================================ *)
(* STUDENT SUBMISSION HELPER                   *)
(* ============================================ *)

(* When a student submits new policies, add them here *)
let add_student_policies (student_text: string) (regulation: string) : policy_entry list =
  parse_policy_text student_text regulation

(* Example: Student submits GDPR Articles 5-10 *)
(* 
let student_gdpr_5_10 = {|
policy starts

@["Art. 5(1)(c) - Data Minimization"]
forall controller, data, purpose.
  (collects(controller, data, purpose))
  implies
  (adequate(data, purpose) and 
   relevant(data, purpose) and
   limitedToNecessary(data, purpose))
;

@["Art. 7(1) - Conditions for Consent"]
forall controller, subject, data, purpose.
  (processes(controller, subject, data, purpose) and
   claimsBasis(controller, @consent))
  implies
  (canDemonstrate(controller, hasConsent(subject, controller, data, purpose)) and
   freelyGiven(subject, controller))

policy ends
|}

(* Then integrate: *)
let updated_gdpr_policies () : policy_database =
  let base = get_gdpr_policies () in
  let new_policies = add_student_policies student_gdpr_5_10 "GDPR" in
  {
    base with
    policies = base.policies @ new_policies;
  }
*)

(* ============================================ *)
(* PRETTY PRINTING                             *)
(* ============================================ *)

let print_policy_summary (db: policy_database) : unit =
  Printf.printf "═══════════════════════════════════════════\n";
  Printf.printf "Policy Database: %s\n" db.name;
  (match db.version with
   | Some v -> Printf.printf "Version: %s\n" v
   | None -> ());
  (match db.effective_date with
   | Some d -> Printf.printf "Effective: %s\n" d
   | None -> ());
  Printf.printf "Total Policies: %d\n" (List.length db.policies);
  Printf.printf "═══════════════════════════════════════════\n\n";
  
  Printf.printf "Policies:\n";
  List.iter (fun p ->
    Printf.printf "  • %s: %s\n" p.id p.section;
    Printf.printf "    %s\n" p.description;
  ) db.policies;
  Printf.printf "\n"