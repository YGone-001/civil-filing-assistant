# Document-Type Boundaries for Adaptation Planning

The application generates **three** document types. They are governed **independently**. A decision
about one never transfers to another.

---

## 1. Civil complaint — `civil_complaint`

- **Candidate counterpart:** an official 民事起诉状 demonstration form exists for all five categories
  (`CANDIDATE_OFFICIAL_COMPLAINT`).
- **Planning classification:** four routes `LEGAL_REVIEW_REQUIRED`; `labor` is
  `PROCEDURAL_REVIEW_REQUIRED`.
- **Boundary:** a legal review of one category's complaint does **not** approve another category's
  complaint. Each of the five is a separate review package.
- **Not claimed:** that the application's narrative output conforms to any official form.

## 2. Evidence list — `evidence_list`

- **Candidate counterpart:** the inspected official texts contain a `证据清单（可另附页）` **section**
  inside each complaint form; no standalone official evidence-list document was found
  (`OFFICIAL_SECTION_ONLY`).
- **Planning classification:** `LEGAL_REVIEW_REQUIRED`, engineering design **blocked**.
- **Boundary:** `STANDALONE_EQUIVALENCE_UNVERIFIED`. The plan does **not** propose replacing the
  independent evidence-list document, and does **not** treat the complaint's embedded evidence
  section as governing it.
- **Not claimed:** that a complaint template's evidence section governs a standalone evidence list.

## 3. Service address confirmation — `service_address_confirmation`

- **Candidate counterpart:** none found in the inspected 975-page source
  (`NO_COUNTERPART_IN_INSPECTED_SOURCE`).
- **Planning classification:** `BLOCKED` (no candidate source identified).
- **Boundary:**

  ```text
  "No matching form found in the inspected PDF"        <- what was observed
  !=
  "No official service-address confirmation exists"    <- NOT claimed
  ```

  Other official materials (court-level practice documents, filing-service guidance) were not
  retrieved or verified. A follow-up retrieval with independent provenance is required before any
  equivalence claim.
- **Not claimed:** that the current document is incorrect, or that it satisfies any court.

## 4. Consequences for this plan

1. All 15 routes carry their own readiness record; none inherits another's status.
2. Each route has its own work package with its own gap and crosswalk references.
3. Each route carries `implementation_authorization = NOT_AUTHORIZED`.
4. No route may be marked approved, and no planning status may be read as a document approval.
5. A future authorization must name the document type explicitly; a complaint authorization cannot
   be reused for the evidence list or the address form.
