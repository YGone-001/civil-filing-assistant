# Baseline and Assumptions

**Planning artefacts only. No implementation is authorized.**

- Frozen baseline: `488607d11d592c0bd906f7bb38c6530304f4b612`
- Planning date: 2026-10-10

---

## 1. Frozen inputs

Everything below was read as **read-only evidence** and is byte-identical to the baseline commit.

| Input | Count | Role |
|---|---|---|
| `source-registry.json` sources | 7 | source provenance; none approved |
| `case-template-mapping.json` mappings | 15 | candidate mappings; none approved |
| `official-element-inventory.json` elements | 185 | official element inventory |
| `application-field-inventory.json` fields | 52 | application field inventory |
| `field-crosswalk.json` crosswalks | 199 | element ↔ field mapping |
| `gap-register.json` gaps | 131 | recorded differences |
| `document-route-assessment.json` routes | 15 | case × document assessments |

Source of record for the inspected official material:

```text
source_id  : spc-2025-notice-pdf
source_type: OFFICIAL_TEMPLATE
level      : A
verification_status: SOURCE_FILE_VERIFIED
sha256     : 07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88
```

`SOURCE_FILE_VERIFIED` means **the file was retrieved and hashed**. It does **not** mean the content
was legally reviewed, that the mapping is applicable, or that the text may be redistributed. The
adaptation gate treats it as a *precondition*, never as an approval.

---

## 2. Route model

The plan uses the frozen route identity unchanged:

```text
5 case categories × 3 document types = 15 routes
case types   : loan, contract, property, labor, divorce
document types: civil_complaint, evidence_list, service_address_confirmation
```

Each planning route maps 1:1 to one frozen route (`document-route-assessment.json`) and one
governance mapping (`case-template-mapping.json`). No route, case or document type is added or
removed.

---

## 3. Priority model (documented formula)

`gap-prioritization.json` evaluates twelve inputs per gap. Eleven are scored 0–3; the twelfth
(`frozen_severity`) is weighted separately. Every input is derived mechanically from frozen fields,
so the plan is reproducible:

| Input | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| `frozen_severity` (weight 4) | INFORMATIONAL | LOW | MEDIUM | HIGH |
| `factual_integrity_impact` (w 3) | FORMATTING_DIFFERENCE | MISSING_OUTPUT, EVIDENCE_PRESENTATION, PROCEDURAL_APPLICABILITY, SOURCE_VERIFICATION_GAP, PARTY_STRUCTURE, UNRESOLVED_LEGAL_QUESTION | MISSING_INPUT, PARTIAL_FIELD_COVERAGE, SEMANTIC_DIFFERENCE, CONDITIONALITY_DIFFERENCE, CALCULATION_RISK | FACT_INTEGRITY_RISK (or +1 when severity is HIGH) |
| `monetary_calculation_impact` (w 3) | no monetary signal | PARTIAL_FIELD_COVERAGE with field references | gap id contains AMOUNT / INTEREST / PENALTY / ASOF / WAGE / FEE / SUPPORT / PRINCIPAL | CALCULATION_RISK |
| `procedural_applicability` (w 2) | not procedural | id contains JURISDICTION / PRESERVATION / COURT-FEE / ARBITRATION / MEDIATION | PROCEDURAL_APPLICABILITY | PROCEDURAL_APPLICABILITY + HIGH |
| `source_verification_dependency` (w 2) | — | no official element reference | references official elements | SOURCE_VERIFICATION_GAP |
| `legal_content_review_dependency` (w 3) | `legal_review_required` false | — | — | `legal_review_required` true |
| `rights_redistribution_dependency` (w 2) | — | address document | civil complaint document | EVIDENCE_PRESENTATION, SOURCE_VERIFICATION_GAP |
| `engineering_implementation_complexity` (w 2) | — | procedural / evidence / source / calculation / legal-question | MISSING_OUTPUT, SEMANTIC_DIFFERENCE, CONDITIONALITY_DIFFERENCE, PARTY_STRUCTURE | MISSING_INPUT, PARTIAL_FIELD_COVERAGE, FACT_INTEGRITY_RISK |
| `regression_risk` (w 2) | INFORMATIONAL | LOW | MEDIUM | HIGH |
| `reversibility` (w 1) | — | output-only or formatting | MISSING_OUTPUT, CALCULATION_RISK, CONDITIONALITY_DIFFERENCE | MISSING_INPUT, PARTIAL_FIELD_COVERAGE, PARTY_STRUCTURE |
| `cross_case_impact` (w 1) | — | concept in 1 case | concept in 2 cases | concept in ≥ 3 cases |
| `user_facing_consequence` (w 1) | — | other | PARTIAL_FIELD_COVERAGE, SEMANTIC_DIFFERENCE, CONDITIONALITY_DIFFERENCE, CALCULATION_RISK | MISSING_INPUT, MISSING_OUTPUT, EVIDENCE_PRESENTATION, PROCEDURAL_APPLICABILITY |

```text
priority_score = 4·severity + 3·factual + 3·monetary + 2·procedural + 2·source_dependency
               + 3·legal_dependency + 2·rights_dependency + 2·engineering
               + 2·regression + 1·reversibility + 1·cross_case + 1·user_facing
```

Bands (planning aid only):

```text
P0  frozen_severity == HIGH, or priority_score >= 54
P1  priority_score >= 47
P2  priority_score >= 36
P3  otherwise
```

The resulting spread is P0 7 · P1 42 · P2 62 · P3 20. A high score is **not** a legal conclusion and
a low score does **not** waive a review dependency.

---

## 4. Readiness vocabulary

`route-readiness.json` uses these classifications, none of which authorize production work:

```text
ANALYSIS_COMPLETE            analysis finished, no further planning needed (not used)
PLANNING_READY               design could start once reviews clear (not used — reviews are open)
SOURCE_REVIEW_REQUIRED       source version/eligibility still to be verified (not used here)
LEGAL_REVIEW_REQUIRED        legal/content applicability review outstanding
RIGHTS_REVIEW_REQUIRED       redistribution review outstanding (folded into the blockers)
PROCEDURAL_REVIEW_REQUIRED   procedural posture unresolved (labor)
ENGINEERING_DESIGN_REQUIRED  design may be prepared, implementation not authorized
BLOCKED                      a prerequisite is missing (service-address routes)
```

Every route additionally carries `implementation_authorization = NOT_AUTHORIZED`.

---

## 5. Assumptions carried forward

1. The frozen Phase 1-B analysis is correct *as analysis*. This plan does not re-verify it and does
   not treat it as legal advice.
2. The inspected 975-page PDF is the source of record; no new version was substituted.
3. `SOURCE_FILE_VERIFIED` is a precondition for adaptation, not an approval.
4. No reviewer identity, approval date or rights decision exists, so none is recorded.
5. Planning metadata contains no user case data, no reviewer identity and no secrets.
6. Nothing in this directory changes application behaviour.

## 6. Assumptions explicitly rejected

- That "government publication" implies unrestricted redistribution rights.
- That a passing validator or a green CI run constitutes legal or rights clearance.
- That the absence of a counterpart in the inspected source proves no official document exists.
- That a large gap count means a category is unsuitable, or that a small gap count makes a category
  a safe pilot.
