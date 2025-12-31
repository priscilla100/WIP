(lang dune 3.0)
(name policy_checker)
(version 0.1.0)

(generate_opam_files true)

(package
 (name policy_checker)
 (synopsis "Formal policy verification system")
 (description "A tool for verifying compliance with regulations using temporal logic")
 (depends
  (ocaml (>= 4.14))
  dune
  menhir
  yojson
  (ppx_deriving_yojson :build)
  (alcotest :with-test)))

(using menhir 2.0)