(* test_multi_regulation.ml *)

let test_multi_regulation () =
  (* Setup *)
  let type_env = load_multi_regulation_types () in
  let policy_manager = Policy_loader.create_manager "policies/" in
  Policy_loader.reload_all policy_manager;
  
  (* Test 1: List all loaded regulations *)
  let all_db = Policy_loader.get_combined_database policy_manager in
  Printf.printf "Loaded %d total policies\n" (List.length all_db.policies);
  
  (* Group by regulation *)
  let by_regulation = List.fold_left (fun acc policy ->
    let reg = policy.regulation in
    let count = try List.assoc reg acc with Not_found -> 0 in
    (reg, count + 1) :: (List.remove_assoc reg acc)
  ) [] all_db.policies in
  
  List.iter (fun (reg, count) ->
    Printf.printf "  %s: %d policies\n" reg count
  ) by_regulation;
  
  (* Test 2: Query HIPAA *)
  Printf.printf "\n=== Testing HIPAA Query ===\n";
  let hipaa_db = Policy_loader.filter_by_regulation "HIPAA" all_db in
  Printf.printf "HIPAA policies: %d\n" (List.length hipaa_db.policies);
  
  (* Test 3: Query GDPR *)
  Printf.printf "\n=== Testing GDPR Query ===\n";
  let gdpr_db = Policy_loader.filter_by_regulation "GDPR" all_db in
  Printf.printf "GDPR policies: %d\n" (List.length gdpr_db.policies);
  
  (* Test 4: Verify type system has both HIPAA and GDPR predicates *)
  Printf.printf "\n=== Type System Check ===\n";
  Printf.printf "Total predicates: %d\n" (List.length type_env.predicates);
  
  (* Check for HIPAA predicate *)
  if List.mem_assoc "coveredEntity" type_env.predicates then
    Printf.printf "  ✓ HIPAA predicate found (coveredEntity)\n"
  else
    Printf.printf "  ✗ HIPAA predicate missing\n";
  
  (* Check for GDPR predicate *)
  if List.mem_assoc "dataSubject" type_env.predicates then
    Printf.printf "  ✓ GDPR predicate found (dataSubject)\n"
  else
    Printf.printf "  ✗ GDPR predicate missing\n"

let () = test_multi_regulation ()