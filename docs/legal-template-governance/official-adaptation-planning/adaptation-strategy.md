# Official Template Adaptation Strategy

**RECOMMENDATION_ONLY · NOT_IMPLEMENTED · NOT_AUTHORIZED**

This document compares three possible future strategies for aligning the application's generated
documents with the inspected official demonstration texts. Nothing here is a decision, an approval
or an instruction to change code.

---

## 1. Current state (baseline, unchanged)

The application produces three narrative DOCX documents for five case categories. All fifteen
paths share one rendering implementation:

```text
build_case_model(view) -> <Case>CaseModel.render_claims() / render_facts()
                       -> DocumentGenerator.export_complaint / export_evidence_list / export_address_form
```

Only the claim list, the facts narrative and the evidence-list remark column differ by category.
The official forms are **element/checkbox based**, so the structural difference is material even
where the factual content overlaps.

---

## 2. Strategy A — Preserve the existing narrative DOCX

Keep the party block, numbered claims, continuous facts-and-reasons paragraph, court designation and
signature/date placeholders exactly as they are; add only the missing *data collection* that the
reviewed element set requires, and let the narrative absorb it.

**Potential advantages**

- Minimal implementation disruption; the export transaction and formatting constants are untouched.
- Existing regression tests (document E2E, factual confirmation, navigation, transactional export)
  stay meaningful.
- Lower DOCX pagination/table risk.

**Potential limitations**

- Remains structurally different from the official element-based forms.
- Official element grouping is only partly representable in a narrative.
- Does **not** by itself establish that any court accepts the narrative format.

**Trade-off summary:** lowest engineering cost and lowest fact-integrity risk, lowest structural
fidelity.

---

## 3. Strategy B — Full element-based official-style form

Produce a document that follows the relevant official form's element, checkbox and table
organization.

**Potential advantages**

- Closest structural correspondence with the inspected source.
- Case-specific elements become individually visible.

**Potential limitations**

- Highest UI and Model change cost; the wizard is field-per-question, not table-per-element.
- Conditional sections multiply (the official forms carry many optional and conditional elements).
- Significant DOCX table/pagination risk; the current renderer has one party-block primitive and one
  table primitive.
- Rights and legal applicability questions are unresolved for reproducing form structure.
- **Highest factual-integrity risk**: an official form's *filled example* must never become a default
  value, and an element-based layout invites exactly that mistake.

**This strategy is NOT authorized for implementation.**

**Trade-off summary:** highest structural fidelity, highest cost and highest fact-integrity risk.

---

## 4. Strategy C — Explicitly reviewed hybrid

Preserve the existing factual safeguards and narrative output as the default path, and adopt only
individually reviewed structural or informational elements (for example, an explicit evidence
section, a clearly labelled element table for a specific claim block, or reviewed checkbox semantics
for a tri-state fact).

**Potential advantages**

- Incremental; each adopted element is separately reviewable.
- Existing user workflows and tests are largely preserved.
- Compatibility testing can be scoped per element.

**Potential limitations**

- May still differ materially from the official form.
- Every adopted element needs its own legal/content review — the review burden is *per element*, not
  per document.
- Poorly sequenced adoption can produce internally inconsistent output.

**Trade-off summary:** middle cost, bounded risk, but the review burden is the dominant constraint.

---

## 5. Comparison matrix

| Dimension | A — Narrative | B — Element-based | C — Reviewed hybrid |
|---|---|---|---|
| Source fidelity | Low | High | Medium |
| Legal review burden | Medium (data set) | High (whole form) | High (per adopted element) |
| Rights review burden | Low (no form text copied) | High (form structure/text) | Medium |
| UI changes | Low–medium (missing fields) | High (tables, checkboxes) | Low–medium |
| Model changes | Low–medium | High | Low–medium |
| Presenter changes | Low | Medium | Low |
| DOCX rendering complexity | Low | High | Medium |
| Conditionality handling | Existing tri-state | Complex (many conditional elements) | Explicit per element |
| Fact-integrity risk | Low | **High** | Medium (if reviewed) |
| Calculation risk | Unchanged | Unchanged | Unchanged |
| Regression-test cost | Low | High | Medium |
| Rollback complexity | Low | High | Medium |
| Offline compatibility | Preserved | Preserved | Preserved |
| Maintainability | High | Low | Medium |

---

## 6. Recommendation

**RECOMMENDATION_ONLY · NOT_IMPLEMENTED · NOT_AUTHORIZED**

Strategy **C (explicitly reviewed hybrid)**, sequenced behind Strategy A's data-collection work, is
the recommended future direction:

1. Start from the narrative path (A) and add only the data collection that a *completed legal
   review* establishes as required. This keeps fact-integrity risk and regression cost low.
2. Adopt structural elements (B-like) **only** where a review concludes that a specific element must
   be presented as a discrete form element, and only one element at a time.
3. Never copy an official form's example text into a document; never reproduce form structure without
   a rights decision.

**Unresolved risks of this recommendation**

- It does not resolve whether any court requires an element-based form.
- It does not resolve the rights position for reproducing form structure.
- It assumes the review will conclude that most missing items are *data collection* rather than
  *layout* — that assumption is untested.
- It is a planning recommendation, not a binding legal or engineering decision.
