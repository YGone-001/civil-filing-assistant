# 民间借贷纠纷 — `loan` — Official Element Gap Analysis

> **Not approved.** This report is analysis only. No legal review has occurred, no official template has been adopted, and no implementation is authorised.

## 1. Category and source identity

- Case type: `loan` — 民间借贷纠纷
- Official candidate: 民事起诉状（民间借贷纠纷）
- Source: `spc-2025-notice-pdf` — `https://www.court.gov.cn/upload/file/2025/06/22/17/43/202506221742_01.pdf`
- Verified SHA-256: `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88` (`SOURCE_HASH_MATCH = PASS`)
- Analyzed revision: `639179933c51f111ea43060157e897fa0a1e4d30`
- Official elements recorded: **40**; crosswalk records: **45**; case-scoped complaint gaps: **27**

Gap records are scoped to this case's own official form. A shared application limitation (for example, the shared party page) is recorded separately for each case type rather than borrowed from another case's gap record.

## 2. Verified PDF page range

- Blank 民事起诉状 form: **physical pages p134–p139** (printed pages 118–123), 1-based physical PDF pages.
- Answer form, example pages and the following category were excluded from the blank-form inventory.

## 3. Official form structure

- 当事人信息（原告/被告自然人/被告单位/第三人）
- 委托诉讼代理人
- 诉讼请求（本金、利息、加速到期、担保、实现债权费用、诉讼费、其他、标的总额）
- 约定管辖和诉前保全
- 事实与理由（合同签订、主体、金额、期限、利率、提供时间、还款方式、还款情况、逾期、担保、登记、保证）
- 证据清单
- 对纠纷解决方式的意愿
- 落款

## 4. Current application structure

叙事式：当事人栏 → 诉讼请求（本金/利息/诉讼费）→ 事实与理由（借款发生、交付、借条三态、利率、催款）→ 此致/落款。

## 5. Element-level mapping summary

| Coverage status | Count |
|---|---|
| `DIRECT_MATCH` | 5 |
| `PARTIAL_MATCH` | 10 |
| `CONDITIONAL_MISMATCH` | 1 |
| `NO_CURRENT_APPLICATION_FIELD` | 23 |
| `APPLICATION_ONLY_ELEMENT` | 5 |
| `NOT_APPLICABLE` | 1 |

## 6. Direct matches

| Official element | Application field(s) | Mechanism | Note |
|---|---|---|---|
| `loan.party.plaintiff.name` | `shared.party.plaintiff.name` | `USER_INPUT_FIELD` | 均为原告姓名。 |
| `loan.party.plaintiff.phone` | `shared.party.plaintiff.phone` | `USER_INPUT_FIELD` | 均为联系电话。 |
| `loan.party.plaintiff.domicile` | `shared.party.plaintiff.address` | `USER_INPUT_FIELD` | 官方为住所地，应用为住址。 |
| `loan.closing.signature` | — | `STATIC_RENDERING` | 均为具状人签署栏。 |
| `loan.closing.date` | — | `STATIC_RENDERING` | 均为落款日期。 |

## 7. Partial matches

| Official element | Application field(s) | Gap(s) | Note |
|---|---|---|---|
| `loan.party.plaintiff.id_document` | `shared.party.plaintiff.id_number` | `GAP-ID-TYPE` | 官方区分证件类型与号码，应用仅有号码。 |
| `loan.party.defendant.natural` | `shared.party.plaintiff.name`, `shared.party.plaintiff.id_number`, `shared.party.plaintiff.address`, `shared.party.plaintiff.phone` | `GAP-PARTY-IDENTITY-DETAILS` | 被告自然人与原告使用同一套字段。 |
| `loan.party.defendant.organization` | `shared.party.company_fields`, `shared.party.plaintiff.name`, `shared.party.plaintiff.address` | `GAP-ORG-REGISTRATION` | 应用支持企业名称/信用代码/法定代表人/住所地。 |
| `loan.evidence.list` | `shared.evidence.rows` | `GAP-EVIDENCE-STANDALONE` | 官方为起诉状内嵌章节，应用为独立文档。 |
| `loan.claim.principal` | `loan.principal` | `GAP-LOAN-ASOF-DATE` | 均为本金主张；官方要求截至日期。 |
| `loan.claim.interest` | `loan.interest_rate`, `loan.interest_start_date` | `GAP-LOAN-ASOF-DATE`, `GAP-LOAN-INTEREST-BASIS` | 应用测算利息并提示人工核对；官方要求尚欠利息与计算方式。 |
| `loan.fact.contracting_parties` | `shared.party.plaintiff.name` | `GAP-LOAN-ROLE-LABELLING` | 官方区分出借人与借款人；应用以原告/被告角色表述。 |
| `loan.fact.principal_amount` | `loan.principal`, `loan.payment_method` | `GAP-LOAN-PRINCIPAL-AMOUNT` | 应用有本金与交付方式；官方区分约定数额与实际提供数额。 |
| `loan.fact.interest_rate` | `loan.interest_rate` | `GAP-LOAN-INTEREST-BASIS` | 应用仅有年利率；官方要求计息周期与条款号。 |
| `loan.fact.disbursement_time` | `loan.loan_date` | `GAP-LOAN-PRINCIPAL-AMOUNT` | 应用借款日期近似对应借款提供时间；提供金额未单独采集。 |

## 7b. Semantic and conditional mismatches

- `loan.procedure.court_fee` → `CONDITIONAL_MISMATCH`: 应用无条件主张诉讼费。

## 8. Missing application inputs

- **GAP-LOAN-REPAYMENT-STATUS** (HIGH): 缺少已还款信息；应用直接主张全额本金与测算利息。
- **GAP-JURISDICTION-CLAUSE** (MEDIUM): 缺少管辖约定字段。
- **GAP-LOAN-ACCELERATION** (MEDIUM): 缺少加速到期/解除合同请求。
- **GAP-LOAN-OVERDUE** (MEDIUM): 缺少逾期状态。
- **GAP-LOAN-SECURITY** (MEDIUM): 担保事实与担保权利主张均未采集。
- **GAP-LOAN-TERM** (MEDIUM): 缺少借款期限。
- **GAP-PARTY-IDENTITY-DETAILS** (MEDIUM): 当事人身份细节字段在应用中没有对应输入。
- **GAP-REPRESENTATIVE** (MEDIUM): 缺少代理人信息。
- **GAP-THIRD-PARTY** (MEDIUM): 缺少第三人建模。
- **GAP-LOAN-CONTRACT-FORMATION** (LOW): 借款合同签订要素未采集。
- **GAP-LOAN-REPAYMENT-METHOD** (LOW): 缺少还款方式。
- **GAP-OTHER-CLAIMS** (LOW): 缺少其他请求入口。
- **GAP-PARTY-RESIDENCE** (LOW): 缺少经常居住地字段。
- **GAP-PRESERVATION** (LOW): 缺少保全信息。

## 9. Missing application outputs / partial coverage

- **GAP-LOAN-INTEREST-BASIS** (HIGH, CALCULATION_RISK): 利率口径（年/季/月）与合同条款出处未采集。
- **GAP-EVIDENCE-STANDALONE** (MEDIUM, EVIDENCE_PRESENTATION): 官方为起诉状内嵌章节，应用为独立文档；两者是否等价未经核实。
- **GAP-LEGAL-BASIS** (MEDIUM, MISSING_OUTPUT): 缺少法律依据输出。
- **GAP-LOAN-ASOF-DATE** (MEDIUM, PARTIAL_FIELD_COVERAGE): 金额基准日与“至实际清偿之日”选项不完整。
- **GAP-COURT-FEE-CONDITIONAL** (LOW, CONDITIONALITY_DIFFERENCE): 条件性不同：应用总是主张，官方允许不主张。
- **GAP-ENFORCEMENT-COST** (LOW, MISSING_OUTPUT): 该请求未实现。
- **GAP-ID-TYPE** (LOW, PARTIAL_FIELD_COVERAGE): 缺少证件类型。
- **GAP-LOAN-PRINCIPAL-AMOUNT** (LOW, PARTIAL_FIELD_COVERAGE): 约定/实际数额与提供金额未分别采集。
- **GAP-LOAN-ROLE-LABELLING** (LOW, SEMANTIC_DIFFERENCE): 角色标签语义不同。
- **GAP-MEDIATION-PREFERENCE** (LOW, PROCEDURAL_APPLICABILITY): 缺少调解意愿字段。
- **GAP-ORG-REGISTRATION** (LOW, PARTIAL_FIELD_COVERAGE): 企业登记细节不完整。
- **GAP-SOURCE-VERSION** (LOW, SOURCE_VERIFICATION_GAP): 版本状态未决。
- **GAP-TOTAL-AMOUNT** (LOW, MISSING_OUTPUT): 缺少标的总额输出。

## 10. Application-only content (reverse coverage)

| Official element | Application field(s) | Note |
|---|---|---|
| `None` | `shared.court_name` | 应用输出“此致 <法院>”，官方空白表格正文未设法院名称栏（由受理法院确定）。 |
| `None` | `loan.loan_reason` | 应用输出借款理由；官方民间借贷表格未设借款理由栏。 |
| `None` | `loan.has_iou` | 应用输出借条出具情况；官方民间借贷表格未设借条栏。 |
| `None` | `loan.demand_date` | 应用在填写催款时间与方式后输出催款事实；官方民间借贷表格未设催款栏。 |
| `None` | `loan.demand_method` | 同上，催款方式。 |

## 11. Conditionality and factual-integrity risks

借条为三态（UNKNOWN/TRUE/FALSE），未确认时不输出任何借条表述；催款仅在时间与方式同时填写时输出；利率适用性提示人工核对。

No official example assertion is proposed as unconditional static text. The tri-state contract (`UNKNOWN` / `CONFIRMED_TRUE` / `CONFIRMED_FALSE`) is preserved.

## 12. Procedure-specific questions

无程序性采集；不涉及仲裁前置。

## 13. Evidence-section findings

- The official 民间借贷纠纷 complaint form contains a `证据清单（可另附页）` **section**.
- No standalone official evidence-list document was found in the 975-page source.
- The application emits an independent four-column evidence table; standalone equivalence is **unverified**.
- Route ownership: the standalone evidence-list route carries this case's own evidence-list gap (`GAP-LOAN-ROUTE-EVIDENCE-STANDALONE` or the loan original); it does not inherit another case's gap record.

## 14. Formatting observations

- The official form is element/checkbox based; the application output is narrative. The application's SimSun/SimHei/FangSong_GB2312 sizes, 2.54/3.17 cm margins and 28 pt line spacing are **project conventions**; no inspected source mandates them. No typography or layout change is proposed.

## 15. Prioritized review items

- **GAP-LOAN-INTEREST-BASIS** — HIGH / CALCULATION_RISK — 不得改变现有计算；须人工核对后决定是否扩展输入。
- **GAP-LOAN-REPAYMENT-STATUS** — HIGH / MISSING_INPUT — 需人工核对；不得自动假定零还款。
- **GAP-EVIDENCE-STANDALONE** — MEDIUM / EVIDENCE_PRESENTATION — 保持独立文档现状；等价性须经法律/内容审查后再评估。
- **GAP-JURISDICTION-CLAUSE** — MEDIUM / MISSING_INPUT — 评估是否新增；属程序事项，需人工核对。
- **GAP-LEGAL-BASIS** — MEDIUM / MISSING_OUTPUT — 不得自动插入法律条文；须人工填写并复核。
- **GAP-LOAN-ACCELERATION** — MEDIUM / MISSING_INPUT — 评估是否新增；属请求范围扩展，须单独授权。
- **GAP-LOAN-ASOF-DATE** — MEDIUM / PARTIAL_FIELD_COVERAGE — 评估是否新增基准日与选项；属计算口径变更，须单独授权。
- **GAP-LOAN-OVERDUE** — MEDIUM / MISSING_INPUT — 评估是否新增；须避免编造逾期。
- **GAP-LOAN-SECURITY** — MEDIUM / MISSING_INPUT — 评估是否新增；属结构性扩展，须单独授权。
- **GAP-LOAN-TERM** — MEDIUM / MISSING_INPUT — 评估是否新增；须避免编造还款期限。
- **GAP-PARTY-IDENTITY-DETAILS** — MEDIUM / MISSING_INPUT — 在获得授权后再评估是否新增采集项；本阶段仅记录。
- **GAP-REPRESENTATIVE** — MEDIUM / MISSING_INPUT — 评估是否新增；属当事人自主决定事项。
- **GAP-THIRD-PARTY** — MEDIUM / MISSING_INPUT — 评估是否支持第三人；属结构性变更，须单独授权。
- **GAP-COURT-FEE-CONDITIONAL** — LOW / CONDITIONALITY_DIFFERENCE — 记录差异；不改变现有行为。
- **GAP-ENFORCEMENT-COST** — LOW / MISSING_OUTPUT — 评估是否新增。
- **GAP-ID-TYPE** — LOW / PARTIAL_FIELD_COVERAGE — 评估是否新增证件类型；本阶段不实现。
- **GAP-LOAN-CONTRACT-FORMATION** — LOW / MISSING_INPUT — 评估是否新增；须避免编造合同签订事实。
- **GAP-LOAN-PRINCIPAL-AMOUNT** — LOW / PARTIAL_FIELD_COVERAGE — 评估是否补充口径；不得改变现有本金计算。
- **GAP-LOAN-REPAYMENT-METHOD** — LOW / MISSING_INPUT — 评估是否新增。
- **GAP-LOAN-ROLE-LABELLING** — LOW / SEMANTIC_DIFFERENCE — 评估是否补充角色表述；不得改变当事人事实。
- **GAP-MEDIATION-PREFERENCE** — LOW / PROCEDURAL_APPLICABILITY — 评估是否新增；属程序事项。
- **GAP-ORG-REGISTRATION** — LOW / PARTIAL_FIELD_COVERAGE — 评估是否新增；需与工商登记信息核对。
- **GAP-OTHER-CLAIMS** — LOW / MISSING_INPUT — 评估是否新增。
- **GAP-PARTY-RESIDENCE** — LOW / MISSING_INPUT — 评估是否新增；属送达相关事项，需人工核对。
- **GAP-PRESERVATION** — LOW / MISSING_INPUT — 评估是否新增。
- **GAP-SOURCE-VERSION** — LOW / SOURCE_VERIFICATION_GAP — 须定期复核官方发布。
- **GAP-TOTAL-AMOUNT** — LOW / MISSING_OUTPUT — 评估是否新增计算与输出；属计算变更，须单独授权。

## 16. Explicit non-approval statement

> The `loan` analysis is **not approved**. It records differences between the application and one inspected official source. Applicability, required adaptation and any legal conclusion remain subject to legal/content review. `approval_status = NOT_REQUESTED`; `review_status = NOT_REQUESTED`.
