# File: utils/family_calc.py
# Purpose: Child support fee estimator for divorce cases
# Encoding: UTF-8

def estimate_child_support(parent_income, percentage=0.25):
    """
    Calculate recommended support amount.
    Standard: 20% to 30% of monthly income.
    """
    return parent_income * percentage
