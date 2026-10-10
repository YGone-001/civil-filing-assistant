# Phase 1-B Methodology

**Scope:** analytical documentation only. No production behaviour was modified.
**Analyzed revision:** `639179933c51f111ea43060157e897fa0a1e4d30`
**Official source:** `spc-2025-notice-pdf`, sha256 `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88` (re-verified independently on 2026-10-10).

---

## 1. Method

```text
retrieve the official PDF into a temporary directory (outside the repository)
        |
        v
compute SHA-256 independently and compare with the frozen source registry
        |
        v
index the PDF by locating every category form and its neighbours
        |
        v
extract the blank complaint form text for each of the five categories
        |
        v
inventory official elements (form fields, instructions, examples kept separate)
        |
        v
trace the application UI -> Presenter -> Model -> render_* -> DOCX path in source
        |
        v
build the field crosswalk (forward) and the application-only reverse check
        |
        v
classify gaps, assess the 15 routes independently
        |
        v
validate deterministically offline (tools/check_template_crosswalk.py)
```

## 2. Evidence classes

| Class | Meaning |
|---|---|
| `VERIFIED` | Confirmed against the retrieved source bytes or against executed code paths |
| `PARTIALLY_VERIFIED` | Confirmed for part of the claim only |
| `INFERRED_FROM_CODE` | Derived by reading the application source, not by executing it |
| `SOURCE_UNAVAILABLE` | The claim could not be checked against the source |
| `LEGAL_REVIEW_REQUIRED` | The legal meaning/applicability is unresolved |

## 3. Coverage statuses (`field-crosswalk.json`)

| Status | Exact meaning |
|---|---|
| `DIRECT_MATCH` | Same meaning, value type, input provenance, conditionality and output role |
| `PARTIAL_MATCH` | Same subject matter, but at least one of meaning/type/provenance/condition/output differs |
| `SEMANTIC_MISMATCH` | Labels look similar but the underlying meaning differs (e.g. arrears period vs service term) |
| `CONDITIONAL_MISMATCH` | The application emits the item unconditionally while the official form makes it optional, or vice versa |
| `CALCULATION_REVIEW_REQUIRED` | The official element is a monetary figure the application derives; the basis needs review |
| `NO_CURRENT_APPLICATION_FIELD` | The official element has no counterpart in the application |
| `APPLICATION_ONLY_ELEMENT` | The application emits content that has no counterpart in the inspected official form |
| `NOT_APPLICABLE` | The element is not a case field (e.g. filling instructions) |
| `SOURCE_UNVERIFIED` | The element could not be verified against the source |

**A similar label is never sufficient for `DIRECT_MATCH`.** The status is assigned per §6.4 of the task brief, comparing twelve dimensions: meaning, data type, supplier, fact class, required/optional, conditional visibility, empty-value behaviour, repetition, category, output location, factual-integrity risk and manual-review dependency.

## 4. Requirement classifications (`official-element-inventory.json`)

`REQUIRED_IN_SOURCE`, `CONDITIONAL_IN_SOURCE`, `OPTIONAL_IN_SOURCE`, `EXPLANATORY_ONLY`, `UNDETERMINED`.

These describe **what the official form asks for**. They are not statements about what the application must do.

## 5. Origin separation

Form fields, filling instructions and filled examples are recorded separately via `origin_kind`:
`BLANK_FORM`, `FILLING_INSTRUCTION`, `FILLED_EXAMPLE`, `GENERAL_OFFICIAL_GUIDANCE`.

An example answer is never treated as a mandatory factual assertion, and the example pages (which follow the answer forms) were deliberately excluded from the blank-form inventories.

## 6. Tri-state integrity

The application distinguishes `UNKNOWN` / `CONFIRMED_TRUE` / `CONFIRMED_FALSE` for delivery, receipt and IOU. Where an official element corresponds to such a fact, the crosswalk records the conditionality and never proposes inserting the official example as unconditional static text.

## 7. Severity vocabulary (`gap-register.json`)

`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFORMATIONAL`. Severity expresses **potential engineering or legal-review impact**, not a legal conclusion. A formatting observation is not `CRITICAL`.

## 8. Non-claims

- No legal approval, court acceptance or compliance conclusion is made anywhere in this directory.
- Every route record carries `approval_status: NOT_REQUESTED`.
- The governance registries were not modified and no source or mapping was promoted.
- Machine validation proves internal consistency only; it cannot re-verify the PDF, which the validator deliberately does not fetch.

## 9. Reproduction

```bash
python tools/check_template_crosswalk.py          # offline, deterministic
python -m pytest -q tests/test_template_crosswalk.py
python tools/check_template_governance.py         # unchanged, still passes
```
