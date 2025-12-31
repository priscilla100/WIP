(* policy_databases.ml - Production-ready policy databases with full format *)

open Ast

(* ============================================ *)
(* POLICY ENTRY TYPE                           *)
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

let hipaa_policies : policy_entry list = [
  {
    id = "HIPAA-164.502-a-1";
    regulation = "HIPAA";
    section = "§164.502(a)(1)";
    description = "A covered entity may not use or disclose PHI except as permitted or required";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "phi"],
        BinLogicalOp (
          Implies,
          Predicate ("coveredEntity", [Var "entity"]),
          BinLogicalOp (
            Or,
            Predicate ("authorized", [Var "entity"; Var "phi"]),
            Predicate ("requiredByLaw", [Var "entity"; Var "phi"])
          )
        )
      ),
      "§164.502(a)(1) - Use and Disclosure of PHI"
    );
  };
  {
    id = "HIPAA-164.502-b";
    regulation = "HIPAA";
    section = "§164.502(b)";
    description = "Minimum necessary standard - use/disclose only minimum necessary PHI";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "phi"; "purpose"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            Predicate ("disclose", [Var "entity"; Var "phi"; Var "purpose"])
          ),
          Predicate ("minimumNecessary", [Var "phi"; Var "purpose"])
        )
      ),
      "§164.502(b) - Minimum Necessary Standard"
    );
  };
  {
    id = "HIPAA-164.508-a";
    regulation = "HIPAA";
    section = "§164.508(a)";
    description = "Valid authorization required for use/disclosure of PHI";
    formula = Annotated (
      Quantified (
        Forall ["physician"; "patient"; "phi"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("inrole", [Var "physician"; Const "physician"]),
            Predicate ("disclose", [Var "physician"; Var "patient"; Var "phi"])
          ),
          Predicate ("hasConsent", [Var "patient"; Var "physician"; Var "phi"])
        )
      ),
      "§164.508(a) - Authorization Required for Disclosure"
    );
  };
  {
    id = "HIPAA-164.508-a-2";
    regulation = "HIPAA";
    section = "§164.508(a)(2)";
    description = "Psychotherapy notes require separate authorization";
    formula = Annotated (
      Quantified (
        Forall ["provider"; "patient"; "notes"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("psychotherapyNotes", [Var "notes"]),
            Predicate ("disclose", [Var "provider"; Var "patient"; Var "notes"])
          ),
          Predicate ("hasSpecificAuthorization", [Var "patient"; Var "provider"; Var "notes"])
        )
      ),
      "§164.508(a)(2) - Psychotherapy Notes Require Specific Authorization"
    );
  };
  {
    id = "HIPAA-164.501-psychotherapy";
    regulation = "HIPAA";
    section = "§164.501";
    description = "Psychotherapy notes definition and exclusions";
    formula = Annotated (
      Quantified (
        Forall ["notes"],
        BinLogicalOp (
          Implies,
          Predicate ("psychotherapyNotes", [Var "notes"]),
          BinLogicalOp (
            And,
            Predicate ("recordedByMentalHealthProfessional", [Var "notes"]),
            BinLogicalOp (
              And,
              Predicate ("documentsConversation", [Var "notes"]),
              Not ( 
                BinLogicalOp (
                  Or,
                  BinLogicalOp (
                    Or,
                    Predicate ("medicationPrescription", [Var "notes"]),
                    Predicate ("sessionStartEndTime", [Var "notes"])
                  ),
                  BinLogicalOp (
                    Or,
                    Predicate ("diagnosisCode", [Var "notes"]),
                    Predicate ("treatmentPlan", [Var "notes"])
                  )
                )
              )
            )
          )
        )
      ),
      "§164.501 - Psychotherapy Notes Definition"
    );
  };
  {
    id = "HIPAA-164.510-b";
    regulation = "HIPAA";
    section = "§164.510(b)";
    description = "Disclosure to family members involved in care";
    formula = Annotated (
      Quantified (
        Forall ["provider"; "patient"; "family"; "phi"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            BinLogicalOp (
              And,
              Predicate ("disclose", [Var "provider"; Var "family"; Var "phi"]),
              Predicate ("familyMember", [Var "family"; Var "patient"])
            ),
            Predicate ("involvedInCare", [Var "family"; Var "patient"])
          ),
          BinLogicalOp (
            Or,
            Predicate ("hasConsent", [Var "patient"; Var "family"]),
            Predicate ("incapacitated", [Var "patient"])
          )
        )
      ),
      "§164.510(b) - Uses and Disclosures for Involvement in Care"
    );
  };
  {
    id = "HIPAA-164.524-a";
    regulation = "HIPAA";
    section = "§164.524(a)";
    description = "Individual right to access their own PHI";
    formula = Annotated (
      Quantified (
        Forall ["patient"; "phi"],
        BinLogicalOp (
          Implies,
          Predicate ("owns", [Var "patient"; Var "phi"]),
          Predicate ("canAccess", [Var "patient"; Var "phi"])
        )
      ),
      "§164.524(a) - Access of Individuals to PHI"
    );
  };
{
    id = "HIPAA-164.524-a-3";
    regulation = "HIPAA";
    section = "§164.524(a)(3)";
    description = "Denial of access to psychotherapy notes is permitted";
    formula = Annotated (
      Quantified (
        Forall ["patient"; "notes"],
        BinLogicalOp (
          Implies,
          Predicate ("psychotherapyNotes", [Var "notes"]),
          Not (
            Predicate ("accessRequired", [Var "patient"; Var "notes"])
          )
        )
      ),
      "§164.524(a)(3) - No Access Right to Psychotherapy Notes"
    );
  };
  {
    id = "HIPAA-164.526-a";
    regulation = "HIPAA";
    section = "§164.526(a)";
    description = "Individual right to amend PHI";
    formula = Annotated (
      Quantified (
        Forall ["patient"; "phi"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("owns", [Var "patient"; Var "phi"]),
            Predicate ("inaccurate", [Var "phi"])
          ),
          Predicate ("canRequestAmendment", [Var "patient"; Var "phi"])
        )
      ),
      "§164.526(a) - Right to Amend PHI"
    );
  };
  {
    id = "HIPAA-164.528-a";
    regulation = "HIPAA";
    section = "§164.528(a)";
    description = "Individual right to accounting of disclosures";
    formula = Annotated (
      Quantified (
        Forall ["patient"; "entity"],
        BinLogicalOp (
          Implies,
          Predicate ("coveredEntity", [Var "entity"]),
          Predicate ("mustProvideAccountingOfDisclosures", [Var "entity"; Var "patient"])
        )
      ),
      "§164.528(a) - Accounting of Disclosures"
    );
  };
  {
    id = "HIPAA-164.530-i";
    regulation = "HIPAA";
    section = "§164.530(i)";
    description = "Sanctions for workforce members who violate policies";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "employee"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            Predicate ("violatesPolicy", [Var "employee"; Var "entity"])
          ),
          Predicate ("applySanctions", [Var "entity"; Var "employee"])
        )
      ),
      "§164.530(i) - Sanctions for Policy Violations"
    );
  };
  {
    id = "HIPAA-164.512-a";
    regulation = "HIPAA";
    section = "§164.512(a)";
    description = "Disclosure required by law";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "phi"; "law"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            Predicate ("requiredByLaw", [Var "law"; Var "phi"])
          ),
          Predicate ("mayDisclose", [Var "entity"; Var "phi"])
        )
      ),
      "§164.512(a) - Uses and Disclosures Required by Law"
    );
  };
  {
    id = "HIPAA-164.512-b";
    regulation = "HIPAA";
    section = "§164.512(b)";
    description = "Disclosure for public health activities";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "phi"; "authority"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            Predicate ("publicHealthAuthority", [Var "authority"])
          ),
          Predicate ("mayDisclose", [Var "entity"; Var "phi"; Var "authority"])
        )
      ),
      "§164.512(b) - Public Health Activities"
    );
  };
  {
    id = "HIPAA-164.512-c";
    regulation = "HIPAA";
    section = "§164.512(c)";
    description = "Disclosure about victims of abuse, neglect, or domestic violence";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "patient"; "phi"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            BinLogicalOp (
              Or,
              BinLogicalOp (
                Or,
                Predicate ("victimOfAbuse", [Var "patient"]),
                Predicate ("victimOfNeglect", [Var "patient"])
              ),
              Predicate ("victimOfDomesticViolence", [Var "patient"])
            )
          ),
          Predicate ("mayDiscloseToAuthority", [Var "entity"; Var "phi"])
        )
      ),
      "§164.512(c) - Disclosure for Victims of Abuse or Neglect"
    );
  };
  {
    id = "HIPAA-164.512-e";
    regulation = "HIPAA";
    section = "§164.512(e)";
    description = "Disclosure for judicial and administrative proceedings";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "phi"; "order"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            BinLogicalOp (
              Or,
              Predicate ("courtOrder", [Var "order"]),
              Predicate ("administrativeOrder", [Var "order"])
            )
          ),
          Predicate ("mayDisclose", [Var "entity"; Var "phi"])
        )
      ),
      "§164.512(e) - Judicial and Administrative Proceedings"
    );
  };
  {
    id = "HIPAA-164.512-f";
    regulation = "HIPAA";
    section = "§164.512(f)";
    description = "Disclosure for law enforcement purposes";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "phi"; "officer"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            Predicate ("lawEnforcement", [Var "officer"])
          ),
          BinLogicalOp (
            Implies,
            BinLogicalOp (
              Or,
              Predicate ("courtOrder", [Var "officer"]),
              Predicate ("suspectIdentification", [Var "phi"])
            ),
            Predicate ("mayDisclose", [Var "entity"; Var "phi"; Var "officer"])
          )
        )
      ),
      "§164.512(f) - Law Enforcement Purposes"
    );
  };
  {
    id = "HIPAA-164.512-j";
    regulation = "HIPAA";
    section = "§164.512(j)";
    description = "Disclosure to avert serious threat to health or safety";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "phi"; "person"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            BinLogicalOp (
              Or,
              Predicate ("seriousThreatToHealth", [Var "person"]),
              Predicate ("seriousThreatToSafety", [Var "person"])
            )
          ),
          Predicate ("mayDisclose", [Var "entity"; Var "phi"])
        )
      ),
      "§164.512(j) - Serious Threat to Health or Safety"
    );
  };
  {
    id = "HIPAA-164.514-a";
    regulation = "HIPAA";
    section = "§164.514(a)";
    description = "De-identification of PHI";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "phi"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            Predicate ("deidentified", [Var "phi"])
          ),
          Not (
            Predicate ("accessRequired", [Var "patient"; Var "notes"])
          )
        )
      ),
      "§164.514(a) - De-identification Standards"
    );
  };
  {
    id = "HIPAA-164.514-e";
    regulation = "HIPAA";
    section = "§164.514(e)";
    description = "Limited data set use requirements";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "dataset"; "recipient"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            Predicate ("limitedDataSet", [Var "dataset"])
          ),
          Predicate ("requiresDataUseAgreement", [Var "entity"; Var "recipient"])
        )
      ),
      "§164.514(e) - Limited Data Set"
    );
  };
  {
    id = "HIPAA-164.520-a";
    regulation = "HIPAA";
    section = "§164.520(a)";
    description = "Notice of privacy practices requirement";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "patient"],
        BinLogicalOp (
          Implies,
          Predicate ("coveredEntity", [Var "entity"]),
          Predicate ("mustProvideNotice", [Var "entity"; Var "patient"])
        )
      ),
      "§164.520(a) - Notice of Privacy Practices"
    );
  };
  {
    id = "HIPAA-164.522-a";
    regulation = "HIPAA";
    section = "§164.522(a)";
    description = "Individual right to request restrictions on use and disclosure";
    formula = Annotated (
      Quantified (
        Forall ["patient"; "entity"; "phi"],
        BinLogicalOp (
          Implies,
          Predicate ("coveredEntity", [Var "entity"]),
          Predicate ("canRequestRestriction", [Var "patient"; Var "entity"; Var "phi"])
        )
      ),
      "§164.522(a) - Rights to Request Privacy Protection"
    );
  };
  {
    id = "HIPAA-164.522-a-1-vi";
    regulation = "HIPAA";
    section = "§164.522(a)(1)(vi)";
    description = "Required restriction when patient pays out of pocket";
    formula = Annotated (
      Quantified (
        Forall ["provider"; "patient"; "phi"; "healthplan"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("paidOutOfPocket", [Var "patient"; Var "provider"]),
            Predicate ("requestsRestriction", [Var "patient"; Var "healthplan"])
          ),
          Predicate ("mustComply", [Var "provider"; Var "patient"])
        )
      ),
      "§164.522(a)(1)(vi) - Required Restriction for Out-of-Pocket Payment"
    );
  };
  {
    id = "HIPAA-164.530-c";
    regulation = "HIPAA";
    section = "§164.530(c)";
    description = "Safeguards to protect PHI";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "phi"],
        BinLogicalOp (
          Implies,
          Predicate ("coveredEntity", [Var "entity"]),
          Predicate ("implementSafeguards", [Var "entity"; Var "phi"])
        )
      ),
      "§164.530(c) - Safeguards Requirement"
    );
  };
  {
    id = "HIPAA-164.530-j";
    regulation = "HIPAA";
    section = "§164.530(j)";
    description = "Documentation and retention requirements";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "policy"],
        BinLogicalOp (
          Implies,
          Predicate ("coveredEntity", [Var "entity"]),
          BinLogicalOp (
            And,
            Predicate ("documentInWriting", [Var "entity"; Var "policy"]),
            Predicate ("retainSixYears", [Var "entity"; Var "policy"])
          )
        )
      ),
      "§164.530(j) - Documentation Requirements"
    );
  };
  {
    id = "HIPAA-164.504-e";
    regulation = "HIPAA";
    section = "§164.504(e)";
    description = "Business associate contracts required";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "associate"; "phi"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            Predicate ("businessAssociate", [Var "associate"])
          ),
          Predicate ("requiresContract", [Var "entity"; Var "associate"])
        )
      ),
      "§164.504(e) - Business Associate Contracts"
    );
  };
  {
    id = "HIPAA-164.306-a";
    regulation = "HIPAA";
    section = "§164.306(a)";
    description = "Security standards for electronic PHI";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "ephi"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            Predicate ("electronicPHI", [Var "ephi"])
          ),
          BinLogicalOp (
            And,
            BinLogicalOp (
              And,
              Predicate ("ensureConfidentiality", [Var "entity"; Var "ephi"]),
              Predicate ("ensureIntegrity", [Var "entity"; Var "ephi"])
            ),
            Predicate ("ensureAvailability", [Var "entity"; Var "ephi"])
          )
        )
      ),
      "§164.306(a) - Security Standards General Requirements"
    );
  };
  {
    id = "HIPAA-164.308-a-1";
    regulation = "HIPAA";
    section = "§164.308(a)(1)";
    description = "Security management process required";
    formula = Annotated (
      Quantified (
        Forall ["entity"],
        BinLogicalOp (
          Implies,
          Predicate ("coveredEntity", [Var "entity"]),
          BinLogicalOp (
            And,
            BinLogicalOp (
              And,
              Predicate ("conductRiskAnalysis", [Var "entity"]),
              Predicate ("implementRiskManagement", [Var "entity"])
            ),
            BinLogicalOp (
              And,
              Predicate ("applySanctionPolicy", [Var "entity"]),
              Predicate ("reviewInformationSystemActivity", [Var "entity"])
            )
          )
        )
      ),
      "§164.308(a)(1) - Security Management Process"
    );
  };
  {
    id = "HIPAA-164.312-a-1";
    regulation = "HIPAA";
    section = "§164.312(a)(1)";
    description = "Access control for electronic PHI";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "user"; "ephi"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            Predicate ("electronicPHI", [Var "ephi"])
          ),
          BinLogicalOp (
            Implies,
            Predicate ("accessRequest", [Var "user"; Var "ephi"]),
            Predicate ("hasAuthorization", [Var "user"; Var "ephi"])
          )
        )
      ),
      "§164.312(a)(1) - Access Control"
    );
  };
  {
    id = "HIPAA-164.312-a-2-iv";
    regulation = "HIPAA";
    section = "§164.312(a)(2)(iv)";
    description = "Encryption and decryption of ePHI";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "ephi"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            Predicate ("electronicPHI", [Var "ephi"])
          ),
          Predicate ("implementEncryption", [Var "entity"; Var "ephi"])
        )
      ),
      "§164.312(a)(2)(iv) - Encryption and Decryption"
    );
  };
  {
    id = "HIPAA-164.312-b";
    regulation = "HIPAA";
    section = "§164.312(b)";
    description = "Audit controls to record and examine ePHI access";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "ephi"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            Predicate ("electronicPHI", [Var "ephi"])
          ),
          Predicate ("implementAuditControls", [Var "entity"; Var "ephi"])
        )
      ),
      "§164.312(b) - Audit Controls"
    );
  };
  {
    id = "HIPAA-164.316-b-1";
    regulation = "HIPAA";
    section = "§164.316(b)(1)";
    description = "Maintain security documentation for six years";
    formula = Annotated (
      Quantified (
        Forall ["entity"; "documentation"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("coveredEntity", [Var "entity"]),
            Predicate ("securityDocumentation", [Var "documentation"])
          ),
          Predicate ("retainSixYears", [Var "entity"; Var "documentation"])
        )
      ),
      "§164.316(b)(1) - Documentation Retention"
    );
  };
]
(* ============================================ *)
(* GDPR POLICIES - Production Format           *)
(* ============================================ *)

let gdpr_policies : policy_entry list = [
  {
    id = "GDPR-6-1-a";
    regulation = "GDPR";
    section = "Art. 6(1)(a)";
    description = "Lawfulness of processing - requires consent";
    formula = Annotated (
      Quantified (
        Forall ["controller"; "subject"; "data"],
        BinLogicalOp (
          Implies,
          Predicate ("processes", [Var "controller"; Var "subject"; Var "data"]),
          Predicate ("hasConsent", [Var "subject"; Var "controller"; Var "data"])
        )
      ),
      "Art. 6(1)(a) - Lawfulness of Processing: Consent"
    );
  };
  {
    id = "GDPR-5-1-b";
    regulation = "GDPR";
    section = "Art. 5(1)(b)";
    description = "Purpose limitation - data collected for specified purposes";
    formula = Annotated (
      Quantified (
        Forall ["controller"; "data"; "purpose"],
        BinLogicalOp (
          Implies,
          Predicate ("processes", [Var "controller"; Var "data"; Var "purpose"]),
          Predicate ("purposeLimited", [Var "data"; Var "purpose"])
        )
      ),
      "Art. 5(1)(b) - Principles: Purpose Limitation"
    );
  };
  {
    id = "GDPR-32-1";
    regulation = "GDPR";
    section = "Art. 32(1)";
    description = "Security of processing - encryption required";
    formula = Annotated (
      Quantified (
        Forall ["controller"; "data"],
        BinLogicalOp (
          Implies,
          Predicate ("holds", [Var "controller"; Var "data"]),
          Predicate ("encryptionEnabled", [Var "controller"])
        )
      ),
      "Art. 32(1) - Security of Processing"
    );
  };
  {
    id = "GDPR-37-1";
    regulation = "GDPR";
    section = "Art. 37(1)";
    description = "Data Protection Officer approval for high-risk processing";
    formula = Annotated (
      Quantified (
        Forall ["controller"; "data"],
        BinLogicalOp (
          Implies,
          Predicate ("processes", [Var "controller"; Var "data"; Const "high_risk"]),
          Predicate ("dataProtectionOfficerApproved", [Var "controller"])
        )
      ),
      "Art. 37(1) - Designation of Data Protection Officer"
    );
  };
  {
    id = "GDPR-44";
    regulation = "GDPR";
    section = "Art. 44";
    description = "International transfers only to safe countries";
    formula = Annotated (
      Quantified (
        Forall ["controller"; "country"; "data"],
        BinLogicalOp (
          Implies,
          BinLogicalOp (
            And,
            Predicate ("processes", [Var "controller"; Var "data"; Var "country"]),
            Predicate ("dataLocation", [Var "data"; Var "country"])
          ),
          Predicate ("safeCountry", [Var "country"])
        )
      ),
      "Art. 44 - General Principle for Transfers"
    );
  };
]

(* ============================================ *)
(* SOX (Sarbanes-Oxley) POLICIES              *)
(* ============================================ *)

let sox_policies : policy_entry list = [
  {
    id = "SOX-302";
    regulation = "SOX";
    section = "§302";
    description = "Corporate responsibility - CEO/CFO certification required";
    formula = Annotated (
      Quantified (
        Forall ["company"; "report"],
        BinLogicalOp (
          Implies,
          Predicate ("publishes", [Var "company"; Var "report"]),
          BinLogicalOp (
            And,
            Predicate ("certified", [Const "ceo"; Var "report"]),
            Predicate ("certified", [Const "cfo"; Var "report"])
          )
        )
      ),
      "§302 - Corporate Responsibility for Financial Reports"
    );
  };
  {
    id = "SOX-404";
    regulation = "SOX";
    section = "§404";
    description = "Management assessment of internal controls";
    formula = Annotated (
      Quantified (
        Forall ["company"; "controls"],
        BinLogicalOp (
          Implies,
          Predicate ("operates", [Var "company"]),
          BinLogicalOp (
            And,
            Predicate ("hasInternalControls", [Var "company"; Var "controls"]),
            Predicate ("assessed", [Var "controls"])
          )
        )
      ),
      "§404 - Management Assessment of Internal Controls"
    );
  };
  {
    id = "SOX-802";
    regulation = "SOX";
    section = "§802";
    description = "Record retention - audit records must be preserved";
    formula = Annotated (
      Quantified (
        Forall ["company"; "record"],
        BinLogicalOp (
          Implies,
          Predicate ("auditRecord", [Var "record"]),
          UnTemporalOp (
            Always,
            Predicate ("preserved", [Var "company"; Var "record"]),
            Some (0, 7)  (* 7 years retention *)
          )
        )
      ),
      "§802 - Criminal Penalties for Altering Documents"
    );
  };
]


let get_hipaa_policies () : policy_database =
  {
    name = "HIPAA Privacy Rule";
    version = Some "2023.1";
    effective_date = Some "2023-01-01";
    policies = hipaa_policies;
  }

let get_gdpr_policies () : policy_database =
  {
    name = "GDPR";
    version = Some "2016/679";
    effective_date = Some "2018-05-25";
    policies = gdpr_policies;
  }

let get_sox_policies () : policy_database =
  {
    name = "Sarbanes-Oxley Act";
    version = Some "2002";
    effective_date = Some "2002-07-30";
    policies = sox_policies;
  }

let get_all_policy_databases () : policy_database =
  {
    name = "Combined Regulatory Compliance";
    version = Some "1.0";
    effective_date = None;
    policies = hipaa_policies @ gdpr_policies @ sox_policies;
  }

(* Convert policy database to complete policy file *)
let to_policy_file (db: policy_database) : policy_file =
  let metadata = {
    name = db.name;
    version = db.version;
    effective_date = db.effective_date;
  } in
  
  (* Type declarations for production *)
  let type_decls = [
    "Entity";
    "PHI";
    "Role";
    "Purpose";
    "Resource";
  ] in
  
  (* Extract formulas with citations *)
  let formulas = List.map (fun policy -> policy.formula) db.policies in
  
  {
    metadata = Some metadata;
    type_decls;
    policies = formulas;
  }

let save_to_file (db: policy_database) (filename: string) : unit =
  let policy_file = to_policy_file db in
  let content = Ast.string_of_ast policy_file in
  let oc = open_out filename in
  output_string oc content;
  close_out oc;
  Printf.printf "Saved %s to %s\n" db.name filename

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

let export_all_to_files () : unit =
  save_to_file (get_hipaa_policies ()) "policies/hipaa.policy";
  save_to_file (get_gdpr_policies ()) "policies/gdpr.policy";
  save_to_file (get_sox_policies ()) "policies/sox.policy";
  save_to_file (get_all_policy_databases ()) "policies/combined.policy"