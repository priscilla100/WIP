cd /Users/priscilladanso/Documents/STONYBROOK/RESEARCH/TOWARDDISSERTATION/IMPLEMENTATION/policy_checker

cat > test_simple.json << 'EOF'
{
  "formula": "forall family, patient. familyMember(family, patient) implies hasConsent(patient, family)",
  "facts": {
    "facts": [
      {"predicate": "familyMember", "arguments": ["grandma", "patient"]},
      {"predicate": "hasConsent", "arguments": ["patient", "grandma"]}
    ]
  },
  "regulation": "HIPAA"
}
EOF

cat test_simple.json | ./precis json

cat > test_input.json << 'EOF'
{
  "formula": "familyMember(grandma, patient)",
  "facts": {
    "facts": [
      ["familyMember", "grandma", "patient"],
      ["hasConsent", "patient", "grandma"]
    ]
  },
  "regulation": "HIPAA"
}
EOF

# Test JSON mode
cat test_input.json | ./precis json


cat > test_ocaml_json.sh << 'EOF'
#!/bin/bash

cd /Users/priscilladanso/Documents/STONYBROOK/RESEARCH/TOWARDDISSERTATION/IMPLEMENTATION/policy_checker

echo "=== Test 1: Inspect ==="
./precis inspect

echo -e "\n=== Test 2: JSON Mode ==="
echo '{"formula": "coveredEntity(hospital)", "facts": {"facts": [["coveredEntity", "hospital"]]}, "regulation": "HIPAA"}' | ./precis json

echo -e "\n=== Test 3: List Policies ==="
./precis list | head -20
EOF

chmod +x test_ocaml_json.sh
./test_ocaml_json.sh