# Pilot Selection and Sequencing

**PROPOSED · NOT_AUTHORIZED**

> **No pilot is currently implementation-ready.** Every candidate category carries at least one
> blocking source or legal question, and stage 1 (`SOURCE_AND_LEGAL_REVIEW`) has completed for none
> of them. The ranking below identifies a **first review target**, not an approved pilot.

---

## 1. Candidate metrics (from frozen records)

| Category | Official elements | Crosswalks | Complaint gaps | HIGH gaps | P0 gaps | Procedural blocker |
|---|---|---|---|---|---|---|
| `loan` | 40 | 45 | 27 | 2 | 2 | none (but two HIGH monetary questions) |
| `contract` | 41 | 44 | 27 | 0 | 1 | template-variant question |
| `property` | 34 | 36 | 22 | 0 | 1 | scope question |
| `labor` | 34 | 36 | 24 | 1 | 2 | **arbitration vs litigation posture unresolved** |
| `divorce` | 36 | 38 | 21 | 1 | 1 | combined-relief scope unresolved |

The smallest gap count is **not** the selection criterion. `divorce` has the fewest gaps and is a poor
pilot because its claim-combination semantics are unresolved; `labor` has a mid-range count and is the
worst pilot because its procedural posture is unresolved.

---

## 2. Assessment by criterion

| Criterion | loan | contract | property | labor | divorce |
|---|---|---|---|---|---|
| Source availability | candidate form located | candidate form located, **plus a competing variant** | candidate form located, unambiguous category | candidate form located | candidate form located |
| Verified element coverage | 40 elements recorded | 41 | 34 | 34 | 36 |
| Unresolved legal issues | 2 HIGH (interest basis, repayment) | variant + demand element | scope of a pure fee-collection claim | arbitration precondition | combined relief, visitation, compensation |
| Procedural ambiguity | low | low | low | **high** | medium |
| Financial calculations | **highest** (interest, principal) | medium (penalty) | medium (fee × months) | medium (wages, overtime) | medium (support) |
| Factual-integrity exposure | high (repayment status) | medium (delivery/receipt) | medium (alleged service relationship) | medium | high (optional allegations) |
| UI input gaps | many | many | moderate | moderate | moderate |
| Model / presenter change | moderate | moderate | moderate | moderate | moderate |
| DOCX structural complexity | same for all (one shared renderer) | same | same | same | same |
| Test coverage today | full (all 15 routes tested) | full | full | full | full |
| Rollback practicality | good | good | good | good | good |

Because all five categories share one renderer, DOCX complexity and rollback practicality do **not**
differentiate them. The differentiators are the unresolved legal/source questions and the
factual-integrity exposure.

---

## 3. Ranking (reasoned)

1. **`property`** — the official category is unambiguous (a single 物业服务合同纠纷 form, no
   competing variant), it carries no HIGH-severity gap, and its claim scope is narrow (a fee claim),
   which limits both the calculation surface and the factual-integrity surface. Its blocking question
   (does the official element set cover a pure fee-collection claim?) is a *scope* question, not a
   *which-source* question.
2. **`contract`** — also carries no HIGH-severity gap, but the generic `买卖合同纠纷` vs
   `房屋买卖合同纠纷` variant question is a **source-selection** risk: if the wrong variant was
   chosen, an adaptation would target the wrong form entirely.
3. **`divorce`** — fewest gaps, but the combined relief (divorce + property + custody + support +
   visitation + compensation) makes claim-conditionality and factual-integrity exposure high, and the
   scope question is unresolved.
4. **`loan`** — two HIGH gaps, the largest monetary-calculation surface, and a repayment-history gap
   that creates a direct factual-integrity risk (never infer "no repayment").
5. **`labor`** — worst pilot. The arbitration precondition is unresolved, so it is not yet established
   that the located litigation-stage form is the correct counterpart at all.

---

## 4. Recommendation

```text
recommended_first_review_target : property
recommended_first_work_package  : wp-property-complaint
status                          : PROPOSED
implementation_authorization    : NOT_AUTHORIZED
```

The recommendation is to **complete review package `rp-property-complaint` first**, because resolving
a scope question is cheaper and lower-risk than resolving a source-selection question (`contract`) or
a procedural-posture question (`labor`). It is *not* a recommendation to implement anything.

## 5. Conditions before any authorization

```text
[ ] rp-property-complaint review completed and documented by an authorized reviewer
[ ] source version and hash re-verified and bound to the review
[ ] mapping applicability confirmed for the property service contract category
[ ] rights and redistribution position decided
[ ] scoped engineering design written and accepted
[ ] regression and rollback criteria agreed
```

Until **all** of these hold, the decision remains `NO-GO`.

## 6. Reasons a category may be deferred

- `labor` — procedural posture unresolved; do not choose a litigation template merely because the
  application currently exports a civil complaint.
- `divorce` — combined scope unresolved; do not automatically expand claims.
- `loan` — repayment-history and interest-basis questions unresolved; do not implement a rate rule.
- `contract` — variant unresolved; do not assume the generic form is the right counterpart.

Deferral is a sequencing decision only. It never waives a review dependency.
