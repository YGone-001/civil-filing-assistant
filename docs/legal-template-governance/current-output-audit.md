# Current Output Audit — Civil Filing Assistant

> **Status:** Baseline audit of the *existing* generator. This document records what the
> application currently produces. It is **not** a statement that any output conforms to, or is
> equivalent to, any official demonstration text.
>
> **Scope:** documentation only. No production behaviour was modified to produce this audit.

- Repository: `YGone-001/civil-filing-assistant`
- Audited revision: `eb23e3e8c8ae080d7185309bf69b3e41681a904e`
- Audit date: 2026-10-10

---

## 1. Document-generation architecture

```text
QWizard inputs (views/wizard_pages.py)
        |
        v
presenters/model_builder.py :: build_case_model(view)
        |
        v
models/case_model.py :: <Case>CaseModel   (CaseTemplate subclass)
        |
        +---- render_claims()  -> list[str]
        +---- render_facts()   -> str
        |
        v
utils/doc_generator.py :: DocumentGenerator
        |
        +---- export_complaint(model, path)
        +---- export_evidence_list(model, path)
        +---- export_address_form(model, path)
        |
        v
utils/batch_manager.py :: BatchExportManager.run_batch_export(model, base_path)
        |
        v
Three .docx files in one case directory (single same-filesystem directory rename)
```

The same `build_case_model()` result feeds both the on-screen preview
(`views/wizard_pages.py :: ExportPage.show_preview()`) and the exported DOCX, so preview and
export cannot drift apart.

### Case-model classes

| Runtime case id | Model class | `case_type_name` |
|---|---|---|
| `loan` | `LoanCaseModel` | 民间借贷纠纷 |
| `contract` | `ContractCaseModel` | 买卖合同纠纷 |
| `property` | `PropertyCaseModel` | 物业服务合同纠纷 |
| `labor` | `LaborCaseModel` | 劳动争议 |
| `divorce` | `DivorceCaseModel` | 离婚析产/抚养费纠纷 |

---

## 2. Five-category × three-document output matrix

All fifteen paths are implemented. **They do not use fifteen independent layouts**: the three
export functions in `DocumentGenerator` are shared by all five categories, and only the
model-supplied `render_claims()` / `render_facts()` text differs.

| Case category | Civil complaint | Evidence list | Service address confirmation |
|---|---|---|---|
| Private lending (`loan`) | `export_complaint(LoanCaseModel)` | `export_evidence_list(LoanCaseModel)` | `export_address_form(LoanCaseModel)` |
| Sales contract (`contract`) | `export_complaint(ContractCaseModel)` | `export_evidence_list(ContractCaseModel)` | `export_address_form(ContractCaseModel)` |
| Property service (`property`) | `export_complaint(PropertyCaseModel)` | `export_evidence_list(PropertyCaseModel)` | `export_address_form(PropertyCaseModel)` |
| Labor remuneration (`labor`) | `export_complaint(LaborCaseModel)` | `export_evidence_list(LaborCaseModel)` | `export_address_form(LaborCaseModel)` |
| Divorce (`divorce`) | `export_complaint(DivorceCaseModel)` | `export_evidence_list(DivorceCaseModel)` | `export_address_form(DivorceCaseModel)` |

**Shared across all 15 paths:** page size (library default), margins, fonts, line spacing,
title/heading/body paragraph styles, party-block renderer, page-number footer, the export
transaction, the output directory/filename scheme, and the DOCX integrity check.

**Case-specific:** the claim list, the facts-and-reasons narrative, and the evidence-list
"备注" (remark) column.

---

## 3. Shared rendering components

| Component | Location | Behaviour |
|---|---|---|
| Global style | `DocumentGenerator._set_global_style` | margins: top/bottom 2.54 cm, left/right 3.17 cm |
| Text primitive | `DocumentGenerator._add_text` | exact line spacing 28 pt, optional first-line indent |
| Title | `DocumentGenerator.add_title` | SimSun 22 pt, bold, centred |
| Heading | `DocumentGenerator.add_heading` | SimHei 16 pt, bold, left |
| Body | `DocumentGenerator.add_body` | FangSong_GB2312 16 pt, justify, 32 pt first-line indent |
| Party block | `DocumentGenerator.add_party_block` | label SimHei 16 pt; content FangSong_GB2312 16 pt; company vs individual variants |
| Claims | `DocumentGenerator.add_claims` | `诉讼请求：` heading + numbered `n. …` body lines |
| Facts | `DocumentGenerator.add_facts` | `事实与理由：` heading + body paragraph |
| Footer | `DocumentGenerator._add_pagination` | centred `- PAGE -` field |
| Cell text | `DocumentGenerator._set_cell_text` | 28 pt exact line spacing, explicit east-Asian font |

---

## 4. Document-specific rendering

### 4.1 Civil complaint — `export_complaint`

Title `民 事 起 诉 状`; blank paragraph; 原告 block; 被告 block; blank paragraph;
`诉讼请求：` (numbered claims); blank paragraph; `事实与理由：`; two blank paragraphs;
footer block (`此致` / court name / `具状人：` / `年   月   日`); page-number footer.

- Party blocks use `原告：` / `被告：` when there is a single party, otherwise `原告1：`…`原告N：`.
- A company party prints `名称，统一社会信用代码：…，[法定代表人：…，]住所地：…，联系电话：…。`
- An individual prints `姓名，身份证号：…，住址：…，联系电话：…。`

### 4.2 Evidence list — `export_evidence_list`

Title `证 据 清 单`; blank paragraph; a 4-column `Table Grid` with headers
`序号 | 证据名称 | 证明对象/目的 | 备注`; one row per `model.evidences` entry; the 备注 column is
`原件核对` by default, `原件核对；计算公式已在起诉状中载明` for 物业服务合同纠纷, and
`原件核对；欠薪计算公式已在起诉状中载明` for 劳动争议. No signature block; no page-number footer.

### 4.3 Service address confirmation — `export_address_form`

Title `送 达 地 址 确 认 书`; blank paragraph; a fixed intro paragraph; then, **per party**, a
6-row × 2-column `Table Grid` with labels `当事人 | 姓名/名称 | 证件号码/统一社会信用代码 |
联系电话 | 送达地址 | 备注`; the 备注 value is `如地址、电话变更，应及时告知人民法院。`;
followed by `确认人：` and `年   月   日`; page-number footer.

Multi-party labelling: `原告` / `被告` when a role has one member, otherwise `原告1`…`原告N`,
`被告1`…`被告N`.

### 4.4 File naming and output location

- Output root: `os.path.join(os.path.expanduser("~"), "Desktop")` (resolved at export time).
- Case directory: `{plaintiff}_vs_{defendant}_{YYYYMMDD}`, with a numeric suffix on collision.
- Files: `{plaintiff}_vs_{defendant}_{YYYYMMDD_HHMMSS}_民事起诉状.docx`, `…_证据清单.docx`,
  `…_送达地址确认书.docx`.
- Publication: staged in `.cfa_staging_<uuid8>` on the destination filesystem, then published
  with one `os.rename`.

---

## 5. Formatting specification (as implemented)

| Attribute | Value |
|---|---|
| Page margins | top/bottom 2.54 cm, left/right 3.17 cm |
| Title font | SimSun, 22 pt, bold, centred |
| Heading font | SimHei, 16 pt, bold |
| Body font | FangSong_GB2312, 16 pt |
| Line spacing | exactly 28 pt |
| Body first-line indent | 32 pt |
| Tables | `Table Grid` |
| Page numbering | footer `- PAGE -` field (complaint and address form only) |
| Output format | `.docx` (OOXML zip) |

---

## 6. Facts-and-claims generation boundaries

`render_claims()` returns the numbered 诉讼请求; `render_facts()` returns the 事实与理由
narrative. Both are deterministic functions of the model fields — no randomness, no network, no
clock dependence except the loan interest cut-off (`datetime.date.today()`), which is labelled
as an estimate in the text.

| Category | Claims emitted | Facts emitted |
|---|---|---|
| loan | principal; interest (only when rate + start date supplied, with a manual-review fallback); court fee | loan date/reason/method/principal; IOU sentence only when the IOU state is confirmed; interest only when supplied; demand sentence only when date **and** method are supplied |
| contract | unpaid principal; penalty only when supplied; court fee | contract date/name/product/total; delivery sentence by tri-state; receipt sentence by tri-state; unpaid balance; no invented demand |
| property | period fee total (`_resolved_principal`); late fee only when supplied; court fee | claimed service relationship; alleged fee liability with a `人工核对` note; fee rate; claimed arrears; partial-period warning; demand sentence only when a demand record is supplied |
| labor | unpaid wages (computed or an explicit manual-confirmation placeholder); overtime only when supplied; double-wage only when confirmed; court fee | employment dates/title/salary; unpaid period; arrears amount or a manual-review statement; overtime only when supplied; double-wage only when confirmed |
| divorce | divorce request; custody only when child + preference supplied; support only when child + amount supplied; property division only when supplied; court fee | marriage date; child only when named; separation only when supplied; reason only when supplied; property only when supplied |

**Factual-integrity rule already in force:** the application must never turn absent or
unconfirmed user input into an affirmative factual allegation. Tri-state controls
(`None` / `True` / `False`) exist for delivery, receipt and IOU status.

---

## 7. Existing validation mechanisms

| Mechanism | Location | Purpose |
|---|---|---|
| Mandatory-field registration (`field*`) | `views/wizard_pages.py` | base QWizard completion |
| Conditional `isComplete()` overrides | `views/wizard_pages.py` | scenario-dependent requirements (delivery date, demand pair, child fields) |
| On-page conditional hint labels | `views/wizard_pages.py` | explain a disabled Next button |
| Party validation | `PartyPage.validate_parties()` | require at least one named plaintiff and defendant; soft phone/credit-code warnings |
| Presenter pre-accept guard | `presenters/main_presenter.py` | blocks export on incomplete parties or contradictory delivery/receipt states |
| DOCX integrity check | `utils/batch_manager.py :: _verify_docx` | zip validity, `word/document.xml` presence, `testzip()` |
| Preview | `ExportPage.show_preview()` | shows the same claims/facts text as the export |

---

## 8. Existing conditional-content behaviour

- **Tri-state facts** (delivery / receipt / IOU): `None` omits the assertion; `True`/`False`
  emit the confirmed positive/negative sentence.
- **Contradiction:** `未交货` + `已签收` blocks export and renders a review note instead.
- **Optional amounts:** an empty penalty / overtime / late-fee / property-division input
  removes the corresponding clause rather than inventing one.
- **Calculation uncertainty:** unparseable or reversed periods fall back to explicit
  manual-review placeholders; a user-entered property total is never silently overwritten.
- **Evidence:** rows are user-editable; blank rows are ignored.

---

## 9. Known risks requiring future review

1. **No verified equivalence.** None of the three document types has been compared against, or
   verified as equivalent to, a specific official demonstration text. See §10.
2. **The service address confirmation form has no counterpart in the official demonstration
   text set** inspected for this audit (see `source-registry.json` / `case-template-mapping.json`).
3. **The evidence list** corresponds to a *section* inside the official demonstration texts
   rather than a standalone official document.
4. **Divorce scope.** The application models divorce + custody + support + property division in
   one combined category; the official set may require more than one variant.
5. **Labor forum.** The application produces a document usable for arbitration or litigation;
   the applicable official text depends on the procedural posture.
6. **Fixed formatting constants** (fonts, sizes, spacing) are project conventions, not verified
   court requirements.
7. **Local court requirements** may vary by court, jurisdiction, filing channel and time.

---

## 10. Explicit non-equivalence statement

> The current output is **not** verified as equivalent to any specific official demonstration
> text. It is a project-authored draft generator. No legal review has been performed, no
> official template has been adapted, and no claim of legal certification is made. Any future
> template change must follow `docs/legal-template-governance/governance.md`.
