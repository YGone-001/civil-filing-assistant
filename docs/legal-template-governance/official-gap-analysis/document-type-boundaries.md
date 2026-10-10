# Document-Type Boundaries

The application generates **three** document types. They must be assessed **independently**. An
official complaint template does not govern the other two.

---

## 1. Civil complaint — `civil_complaint`

- **Nature:** pleading document.
- **Official counterpart:** a candidate official 民事起诉状 demonstration text exists for all five
  categories (`CANDIDATE_OFFICIAL_COMPLAINT`).
- **Comparison scope:** the blank complaint form pages only (see `source-verification.md`).
- **Structural difference:** the official forms are **element/checkbox based** (a tabular form with
  blank fields, checkboxes and optional narrative areas); the application produces a **narrative**
  complaint (party block, numbered claims, continuous facts-and-reasons paragraph, 此致/落款).
  Factual content can be similar while the structure is materially different.
- **Formatting:** the application uses fixed project conventions (SimSun title 22 pt, SimHei
  headings 16 pt, FangSong_GB2312 body 16 pt, 2.54/3.17 cm margins, 28 pt line spacing). **No
  inspected official source mandates these values**; they remain project conventions.

## 2. Evidence list — `evidence_list`

- **Nature:** supporting evidentiary document.
- **Official counterpart classification:** `OFFICIAL_SECTION_ONLY`.
- **Finding:** the inspected official texts contain a `证据清单（可另附页）` **section** inside each
  complaint form. No standalone official evidence-list document was found in the 975-page source.
- **Equivalence:** `STANDALONE_EQUIVALENCE_UNVERIFIED`. The application emits an independent
  four-column table (序号 / 证据名称 / 证明对象·目的 / 备注). Whether that document is equivalent to
  the official embedded section is **not established**, and the application document must not be
  described as officially approved.
- **Do not** apply complaint-form requirements to this document type.

## 3. Service address confirmation — `service_address_confirmation`

- **Nature:** procedural document concerning service information.
- **Official counterpart classification:** `NO_COUNTERPART_IN_INSPECTED_SOURCE`.
- **Finding:** `送达地址` occurs on **0** of the 975 inspected pages.
- **Critical distinction:**

  ```text
  "No matching form found in the inspected PDF"       <- what was observed
  !=
  "No official service-address confirmation exists"   <- NOT claimed
  ```

  Other official materials (court-level practice documents, filing-service guidance) were **not**
  retrieved or verified in this analysis. A follow-up retrieval with independent provenance would be
  required before any equivalence claim.
- **Do not** treat an unverified webpage as an authoritative form.

## 4. Consequences for the analysis

1. Each of the 15 routes has its own record in `document-route-assessment.json`.
2. The five complaint routes are compared element by element against the official form.
3. The five evidence-list routes are compared **only** at the level of "does an official
   standalone document exist?" — answer: no; section only.
4. The five address-form routes are compared **only** at the level of "is there an official
   counterpart in the inspected source?" — answer: no.
5. No route may carry `APPROVED`; all are `NOT_REQUESTED`.
