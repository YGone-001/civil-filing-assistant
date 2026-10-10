# Official Source Verification

**Source ID:** `spc-2025-notice-pdf`
**Analyzed revision:** `639179933c51f111ea43060157e897fa0a1e4d30`
**Verification date:** 2026-10-10

---

## 1. Retrieval

| Item | Value |
|---|---|
| Official download URL | `https://www.court.gov.cn/upload/file/2025/06/22/17/43/202506221742_01.pdf` |
| Linking official publication | `https://www.court.gov.cn/zixun/xiangqing/468671.html` (最高人民法院 / 司法部 / 中华全国律师协会, published 2025-06-23) |
| Retrieval method | HTTP GET, `curl -L`, development-time only |
| HTTP outcome | GET → 200 with the full body; a HEAD probe on the same URL returned 403 (access quirk, recorded for transparency) |
| Local path | temporary directory **outside** the repository (not committed) |
| File size | 6 832 359 bytes |
| PDF version | 1.7 |
| Page count | 975 |

## 2. Hash verification

| Item | Value |
|---|---|
| Independently computed SHA-256 | `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88` |
| Frozen registry value | `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88` |
| **SOURCE_HASH_MATCH** | **PASS** |

The registry value was **not copied** — the file was retrieved again and hashed from the retrieved bytes. The registry file itself was not modified.

## 3. Text-extraction quality

Text extraction is **partial**. The document embeds CID fonts; most pages extract cleanly, while a minority (for example physical pages 1–5 and 14–20) return no text at all. All five complaint forms used in this analysis extracted as text, so their elements are recorded with `extraction_confidence: TEXT_VERIFIED`.

**No page was visually inspected**, so no element is recorded as `TEXT_AND_VISUAL_VERIFIED`, and no `VISUAL_VERIFIED` claim is made.

## 4. Located category forms

| Case type | Official title | Blank complaint form (physical pages) | Printed pages | Answer form | Complaint example |
|---|---|---|---|---|---|
| `divorce` | 离婚纠纷 | p57–p60 | 41–44 | p61–p63 | p64–p67 |
| `contract` | 买卖合同纠纷 | p71–p76 | 55–60 | p77–p81 | p82–p87 |
| `loan` | 民间借贷纠纷 | p134–p139 | 118–123 | p140–p143 | p144–p147 |
| `property` | 物业服务合同纠纷 | p233–p236 | 217–220 | p237–p240 | p241–p244 |
| `labor` | 劳动争议纠纷 | p248–p251 | 232–235 | p252–p254 | p255–p258 |

All five prior page hints were **independently confirmed**.

**Deliberate exclusion:** a distinct `房屋买卖合同纠纷` category begins at physical p93. It was **not** merged into the `contract` analysis; the generic `买卖合同纠纷` form was used instead, and the variant question is recorded as an open item.

## 5. Two decisive negative findings

1. **No service-address document.** The string `送达地址` occurs on **0** of 975 pages. This is a statement about *this source* only. It does **not** mean no official service-address form exists anywhere.
2. **No standalone evidence-list document.** `证据清单` occurs on 211 pages, but always as a **section inside** the demonstration texts (the blank forms carry a "证据清单（可另附页）" item). No standalone official evidence-list document was found.

## 6. Version status

The notice announces nationwide use from 2025-07-14 and states the texts will be optimised dynamically. No separately identifiable later authoritative revision was retrieved.

```text
version decision: UNRESOLVED_AND_RECORDED
```

Not established: whether the uploaded file has been replaced in place without a URL change, and whether provincial reproductions differ from the central file.

## 7. Rights and redistribution

The 6.8 MB official PDF is **not** committed. Only short element labels, physical page pointers, semantic summaries and source references are stored. No official DOCX, page image or bulk extracted text is committed. Rights review status: `NOT_REVIEWED`.

## 8. What this verification does NOT establish

- It does not establish that any application output conforms to these forms.
- It does not establish local-court or jurisdictional applicability.
- It does not establish that the inspected 2025 file is the current authoritative version.
- It does not constitute legal review.
