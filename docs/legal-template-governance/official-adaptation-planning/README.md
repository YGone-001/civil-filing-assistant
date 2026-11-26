# Official Template Adaptation Planning

**Status:** planning artefacts only. **No implementation is authorized.** No source, mapping, legal
conclusion or rights decision is approved by anything in this directory.

- Repository: `YGone-001/civil-filing-assistant`
- Frozen baseline: `488607d11d592c0bd906f7bb38c6530304f4b612`
- Planning date: 2026-10-10
- Production application: **frozen**
- Frozen Phase 1-B analysis: **read-only input**, referenced but never duplicated wholesale

---

## 1. What this directory is

The Phase 1-B analysis (`../official-gap-analysis/`) established *what differs* between the
application's three documents and the inspected official demonstration texts. It deliberately made
no adaptation decision.

This directory answers the next question — **what would it take to change anything, and who has to
decide?** — without changing anything:

| Deliverable | File |
|---|---|
| Baseline and assumptions | `baseline-and-assumptions.md` |
| Fifteen-route readiness | `route-readiness.json` |
| All 131 gaps prioritized | `gap-prioritization.json` |
| Adaptation work packages | `adaptation-work-packages.json` |
| Adaptation strategy comparison | `adaptation-strategy.md` |
| Five case blueprints | `cases/loan.md`, `contract.md`, `property.md`, `labor.md`, `divorce.md` |
| Legal / content review protocol | `legal-review-protocol.md` |
| Source version and rights gate | `source-version-and-rights-gate.md` |
| Authorization gate sequence | `approval-gates.md` |
| Factual-integrity contract | `factual-integrity-contract.md` |
| Document-type boundaries | `document-type-boundaries.md` |
| Regression and rollback plan | `regression-and-rollback-plan.md` |
| Implementation sequence | `implementation-sequence.md` |
| Pilot selection | `pilot-selection.md` |
| Final decision request | `decision-request.md` |
| 租赁合同治理工作包（后置增补） | `rental-contract-work-package.md` / `rental-contract-work-package.json` / `rental-text-and-structure-comparison.md` |
| 租赁合同法律审阅材料（未执行） | `rental-legal-content-review-packet.md` / `rental-legal-review-agenda.md` |

Machine-readable planning records are validated offline by
`tools/check_template_adaptation_plan.py` with regression tests in
`tests/test_template_adaptation_plan.py`.

---

## 2. Headline numbers

```text
Routes assessed                   15  (5 case categories × 3 document types)
Routes authorized                  0
Gaps prioritized                 131  (exactly the frozen gap-register set)
Work packages                     15
Work packages authorized           0
Official elements                185  (frozen, unchanged)
Crosswalk records                199  (frozen, unchanged)
```

Priority distribution (see `gap-prioritization.json`):

```text
P0   7   four frozen HIGH gaps + three amount-basis gaps
P1  42
P2  62
P3  20
```

Readiness distribution (`route-readiness.json`):

```text
LEGAL_REVIEW_REQUIRED        9   five complaint routes minus labor, plus four evidence routes
PROCEDURAL_REVIEW_REQUIRED   1   labor civil complaint (arbitration posture unresolved)
BLOCKED                      5   all five service-address routes (no candidate source identified)
```

Gap distribution by case: `loan` 29 · `contract` 29 · `property` 24 · `labor` 26 · `divorce` 23.
By document: civil complaint 121 · evidence list 5 · service address 5.
By frozen severity: HIGH 4 · MEDIUM 65 · LOW 59 · INFORMATIONAL 3.

> The counts above describe the frozen five-case baseline. The separate rental addendum
> (`rental-contract-work-package.md` / `.json`) is `OPEN` / `SCOPED_FIX_IMPLEMENTED` / `NO-GO`:
> a candidate official rental complaint has been identified, its file verified, a documentary
> comparison recorded 35 open gaps, and the mapping review added three unapproved rental entries to
> the central registry. A non-signatory preflight covers all 21 review questions and recorded four
> output findings. A scoped engineering authorization fixed only PF-01 (payment-status wording) and
> PF-02 (multi-defendant attribution); both await recheck. PF-03 and PF-04 remain open. Formal legal
> review is still pending: no reviewer is assigned and no legal conclusion has been reached. The
> central registry now has 18 entries (15 original + 3 rental), while the frozen planning counts
> stay 15. No mapping, legal review or rights decision is approved. The rental package is validated
> by `tools/check_rental_governance_package.py`.

---

## 3. Current decision

```text
PLANNING_STATUS:            COMPLETE
IMPLEMENTATION_AUTHORIZATION: NOT_AUTHORIZED
CURRENT_GATE_DECISION:      NO-GO
```

Planning readiness is not legal approval. Legal approval is not engineering acceptance.
Engineering acceptance is not release approval. These four decisions remain independent and none of
them has been made.

---

## 4. What is explicitly *not* claimed here

- That any official source is approved for adaptation.
- That any mapping is correct or applicable.
- That the official texts may be redistributed.
- That any proposed change would satisfy any court.
- That a pilot has been chosen. A pilot is *proposed* in `pilot-selection.md` and remains
  `NOT_AUTHORIZED`.

The service-address routes are recorded as `BLOCKED`: no counterpart was found in the inspected
975-page source, which is a statement about *that source only* and is **not** evidence that no such
official document exists.
