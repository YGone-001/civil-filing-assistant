# Case-Type → Document → Source Mapping

> **Read this first.** Every entry below is a **candidate** record. **No mapping has been
> legally reviewed or approved.** `CANDIDATE_SOURCE_IDENTIFIED` means a plausible official
> source exists and was located — it does **not** mean the application's output conforms to it.
>
> Machine-readable counterpart: `case-template-mapping.json`. Sources: `source-registry.json`.

- Repository: `YGone-001/civil-filing-assistant`
- Audited revision: `eb23e3e8c8ae080d7185309bf69b3e41681a904e`
- Review date: 2026-10-10

---

## 1. Runtime identifiers (unchanged)

Case types: `loan`, `contract`, `property`, `labor`, `divorce`
Document types: `civil_complaint`, `evidence_list`, `service_address_confirmation`

These are the existing runtime identifiers. This document renames nothing and changes no
case-selection behaviour.

## 2. Mapping status vocabulary

| Status | Meaning |
|---|---|
| `CANDIDATE_SOURCE_IDENTIFIED` | A plausible official source was located; applicability is **not** verified |
| `UNVERIFIED` | No applicable source determined; the question is open |
| `MAPPING_REVIEWED` | A documented applicability decision exists (none yet) |
| `APPROVED` | Approved for adaptation (none yet) |
| `REJECTED` | Considered and rejected |
| `NO_OFFICIAL_SOURCE_IDENTIFIED` | No counterpart found in the inspected official material |

Approval status is tracked separately (`approval_status`); all 15 entries are `NOT_REQUESTED`.

---

## 3. The fifteen mappings

| # | Case type | Document type | Candidate source | Mapping status | Evidence / unresolved question |
|---|---|---|---|---|---|
| 1 | `loan` | `civil_complaint` | `spc-2025-notice-pdf` | `CANDIDATE_SOURCE_IDENTIFIED` | `民事起诉状（民间借贷纠纷）` at PDF p134 (instance p144). Open: does the official element set match the application's fields? |
| 2 | `loan` | `evidence_list` | `spc-2025-notice-pdf` | `UNVERIFIED` | 证据清单 exists only as a **section** of the demonstration texts (211 pages mention it); no standalone official evidence-list document was identified. |
| 3 | `loan` | `service_address_confirmation` | — | `NO_OFFICIAL_SOURCE_IDENTIFIED` | The string `送达地址` occurs on **0** of the 975 official pages. |
| 4 | `contract` | `civil_complaint` | `spc-2025-notice-pdf` | `CANDIDATE_SOURCE_IDENTIFIED` | `民事起诉状（买卖合同纠纷）` at PDF p71 (instance p82). Open: the official set also has a separate `房屋买卖合同纠纷` variant — is the generic one the right counterpart? |
| 5 | `contract` | `evidence_list` | `spc-2025-notice-pdf` | `UNVERIFIED` | Same evidence-section reasoning as #2. |
| 6 | `contract` | `service_address_confirmation` | — | `NO_OFFICIAL_SOURCE_IDENTIFIED` | Same as #3. |
| 7 | `property` | `civil_complaint` | `spc-2025-notice-pdf` | `CANDIDATE_SOURCE_IDENTIFIED` | `民事起诉状（物业服务合同纠纷）` at PDF p233 (instance p241). Open: fee-collection element coverage not compared. |
| 8 | `property` | `evidence_list` | `spc-2025-notice-pdf` | `UNVERIFIED` | Same evidence-section reasoning as #2. |
| 9 | `property` | `service_address_confirmation` | — | `NO_OFFICIAL_SOURCE_IDENTIFIED` | Same as #3. |
| 10 | `labor` | `civil_complaint` | `spc-2025-notice-pdf` | `CANDIDATE_SOURCE_IDENTIFIED` | `民事起诉状（劳动争议纠纷）` at PDF p248 (instance p255). Open: arbitration-stage vs litigation-stage applicability is unresolved. |
| 11 | `labor` | `evidence_list` | `spc-2025-notice-pdf` | `UNVERIFIED` | Same evidence-section reasoning as #2. |
| 12 | `labor` | `service_address_confirmation` | — | `NO_OFFICIAL_SOURCE_IDENTIFIED` | Same as #3. |
| 13 | `divorce` | `civil_complaint` | `spc-2025-notice-pdf` | `CANDIDATE_SOURCE_IDENTIFIED` | `民事起诉状（离婚纠纷）` at PDF p57 (instance p64). Open: the application combines divorce + custody + support + property division; one official text may not cover the whole workflow. |
| 14 | `divorce` | `evidence_list` | `spc-2025-notice-pdf` | `UNVERIFIED` | Same evidence-section reasoning as #2. |
| 15 | `divorce` | `service_address_confirmation` | — | `NO_OFFICIAL_SOURCE_IDENTIFIED` | Same as #3. |

---

## 4. Case-specific analysis notes

**Private lending.** An official `民间借贷纠纷` complaint text exists. Whether its element set
(the official texts are element/table based) matches the application's flat field model is not
established.

**Sales contract.** The official set distinguishes a generic `买卖合同纠纷` from
`房屋买卖合同纠纷`. The application models a generic goods sale, so the generic variant is the
natural candidate — but this is an assumption, not a verified decision.

**Property service.** An official `物业服务合同纠纷` complaint text exists. Whether it covers
fee-collection disputes with the same factual elements as the application (alleged
owner/occupier, area-based fee rate, arrears period) is not compared.

**Labor remuneration.** An official `劳动争议纠纷` complaint text exists. Labor disputes
normally require arbitration first, and the application's output is described as usable for
arbitration or litigation, so the correct counterpart depends on the procedural posture. Note
also that the token `劳动报酬` appears in the PDF inside **maritime** documents; it was not
treated as this category.

**Divorce.** An official `离婚纠纷` complaint text exists, but the application's single
combined category (divorce + custody + support + property division) may correspond to more than
one official source category or variant. This is unresolved.

---

## 5. Document-type separation

The three generated document types are governed **independently**:

- The **civil complaint** is a pleading document and is the only type with an identified
  candidate official text.
- The **evidence list** is a supporting evidentiary document. The official texts contain an
  evidence-list *section*; whether that section governs a standalone evidence-list document is
  unverified.
- The **service address confirmation form** is a procedural document about service
  information. **No counterpart was found** in the inspected official material.

Do **not** propagate complaint-template requirements to the other two types.

---

## 6. Standing rules

1. A mapping may only reach `APPROVED` with documented approval metadata (see `governance.md`).
2. Availability of an official text does not prove local court compatibility.
3. Announcement verification is not template verification.
4. The current application output is a software baseline, never an official authority.
5. Any mapping change must follow the change-control lifecycle in `governance.md`.
