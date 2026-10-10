# Factual Integrity Contract for Future Adaptation

**Non-negotiable. No application change is made or authorized in this task.**

> The application must never create factual allegations from absent or unconfirmed user input.

Any future authorized adaptation must preserve every rule below. These rules already hold in the
frozen application; the purpose of this contract is to make them an explicit acceptance criterion for
any future change.

---

## 1. Tri-state fact contract

```text
UNKNOWN           -> assert neither outcome
CONFIRMED_TRUE    -> may describe the positive fact
CONFIRMED_FALSE   -> may describe the negative fact
```

Tri-state controls exist today for delivery, receipt and IOU status. A future element-based layout
must not collapse them into a checkbox default.

| Fact | UNKNOWN behaviour | Notes |
|---|---|---|
| Loan disbursement | assert neither | the loan date/payment method do not prove delivery of a specific sum |
| Partial repayment | assert neither | **never** infer "no repayment" from the absence of a repayment field |
| Contract formation | assert neither | `ContractCaseModel.render_facts()` must keep not inventing a demand |
| Delivery | omit the sentence | contradiction with receipt blocks export |
| Receipt | omit the sentence | contradiction with delivery blocks export |
| Payment demand | omit the sentence | requires both date and method (loan) / a demand record (property) |
| Employment relationship | assert neither | labour relationship facts come from user input only |
| Arbitration posture | assert neither | procedural prerequisites must not be asserted |
| Marriage breakdown | omit the reason | no marital-fault allegation without user confirmation |
| Children / custody / support | omit | support requires an identified child |
| Optional remedies | omit | an empty amount removes the clause rather than inventing one |

---

## 2. Content provenance classes

Every future document fragment must be attributable to exactly one class:

```text
USER_CONFIRMED_FACT
USER_CLAIM_OR_ALLEGATION
CALCULATED_VALUE
LEGAL_REFERENCE
TEMPLATE_STATIC_TEXT
REVIEW_REQUIRED_PLACEHOLDER
UNVERIFIED_SOURCE_CONTENT
```

`UNVERIFIED_SOURCE_CONTENT` must **never** be emitted into a user document.

---

## 3. No invented case facts

- An official form's *completed example* must never become a default value.
- A blank field must never become an affirmative assertion.
- A model-calculated figure must never be presented as a user-confirmed contractual fact.
- A template's static text must not be inserted where it would assert an unconfirmed event.
- A manual-review placeholder must remain visibly editable and must not be silently resolved.

---

## 4. Monetary values

- Every calculated figure keeps a manual-verification entry point.
- A user-entered total is never silently overwritten by a computed value.
- An unparseable or reversed period yields an explicit placeholder, never a fabricated number.
- The four HIGH-severity gaps (`GAP-LOAN-INTEREST-BASIS`, `GAP-LOAN-REPAYMENT-STATUS`,
  `GAP-LABOR-ARBITRATION`, `GAP-DIVORCE-COMBINED-SCOPE`) are review blockers, not calculation
  instructions.

---

## 5. Offline and privacy boundary

Any future authorized implementation must preserve:

```text
No runtime source download
No telemetry
No cloud processing
No mandatory network connection
No user-case data in governance metadata
No reviewer identity or secret in planning metadata
```

Planning metadata contains no user case data: the files in this directory describe *the application
and the sources*, never a real dispute.

---

## 6. Acceptance criteria for a future change

A future implementation is acceptable only if:

1. every new field is optional unless a completed review establishes that it is required;
2. every new tri-state fact defaults to UNKNOWN and asserts nothing;
3. no official example text or value appears in any generated document;
4. all existing factual-confirmation tests still pass unchanged;
5. new tests cover the UNKNOWN, CONFIRMED_TRUE and CONFIRMED_FALSE paths of every new fact;
6. the offline guarantee is verifiably intact.
