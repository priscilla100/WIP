(* export_policy_files.ml - Export production policy databases to files *)

open Policy_databases

let () =
  (* Create policies directory if it doesn't exist *)
  (try Unix.mkdir "policies" 0o755 with Unix.Unix_error (Unix.EEXIST, _, _) -> ());
  
  Printf.printf "Exporting policy databases to production format...\n\n";
  
  (* Export individual regulations *)
  export_all_to_files ();
  
  Printf.printf "\n✅ Policy files exported successfully!\n\n";
  
  Printf.printf "Generated files:\n";
  Printf.printf "  - policies/hipaa.policy     (HIPAA Privacy Rule)\n";
  Printf.printf "  - policies/gdpr.policy      (GDPR)\n";
  Printf.printf "  - policies/sox.policy       (Sarbanes-Oxley)\n";
  Printf.printf "  - policies/combined.policy  (All regulations)\n\n";
  
  Printf.printf "Example usage:\n";
  Printf.printf "  ./policy_checker --file policies/hipaa.policy\n";
  Printf.printf "  ./policy_checker --file policies/gdpr.policy\n\n"