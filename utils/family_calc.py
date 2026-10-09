# File: utils/family_calc.py
# Purpose: Child support fee estimator helper for divorce cases
# Encoding: UTF-8


def estimate_child_support(parent_income, percentage=0.25):
    """Return a rough, non-authoritative child-support estimate.

    This is a simple arithmetic helper only. It does NOT assert any statutory or
    judicial "standard" ratio: the appropriate amount depends on the child's
    actual needs, the parents' incomes and local practice, and is ultimately
    decided by the court. Any figure returned here must be reviewed by a person
    before it is relied upon.
    """
    return parent_income * percentage
