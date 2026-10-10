# Implementation Sequence

**Future sequencing only. Nothing in this document is authorized to run.**

The plan separates review work from engineering work so that no engineering step can start before the
review that justifies it. Each stage names its exit condition and its current state.

---

## 1. Stages

| # | Stage | Entry condition | Exit condition | Current state |
|---|---|---|---|---|
| 1 | Source and legal review | planning complete | documented source, mapping, legal/content and rights decisions for the scoped package | `NOT_STARTED` |
| 2 | Engineering design | stage 1 decisions recorded for the scope | written design with field, model, presenter and DOCX changes named | `NOT_STARTED` |
| 3 | Field collection | design accepted | wizard fields added behind the reviewed requirement, all optional unless proven required | `NOT_STARTED` |
| 4 | Data-flow integration | field collection complete | `build_case_model()` maps the new fields; preview and export share one model | `NOT_STARTED` |
| 5 | Document rendering | data flow integrated | reviewed rendering change, no official example text emitted | `NOT_STARTED` |
| 6 | Regression and visual inspection | rendering complete | full suite green; DOCX visually inspected per the regression plan | `NOT_STARTED` |
| 7 | Release review | regression accepted | release approval recorded with its own scope and evidence | `NOT_STARTED` |

**No stage is complete merely because documentation exists** (governance §5).

## 2. Bounded packages

Future engineering packages must be scoped to:

```text
one case category
one document type
a defined subset of gap IDs
a defined subset of official elements
an explicit source version
a defined regression test set
```

The fifteen route-scoped work packages in `adaptation-work-packages.json` satisfy this shape. A
single authorization covering the whole fifteen-document migration is explicitly discouraged.

## 3. Sequence dependencies

```text
stage 1  ──blocks──>  stage 2  ──blocks──>  stage 3  ──blocks──>  stage 4
   ──blocks──>  stage 5  ──blocks──>  stage 6  ──blocks──>  stage 7
```

A failed or missing prerequisite blocks every downstream stage. There is no fast path: a green test
run cannot substitute for stage 1.

## 4. Recommended first scope (proposal only)

If and when stage 1 completes for one package, the smallest defensible engineering scope is the
**single category + single document type** package with the fewest blocking legal questions — see
`pilot-selection.md`. That recommendation is `PROPOSED` and `NOT_AUTHORIZED`.

## 5. Rollback integration

Every stage must leave the legacy document path usable. Rollback is per case and per document, never
all-or-nothing (see `regression-and-rollback-plan.md` §4).
