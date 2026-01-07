"""
Test script for transfer detection functionality

Tests the multi-tiered production-grade transfer detector.
"""
from app.services.categorization import TransferDetector


class MockTransaction:
    """Mock transaction for testing"""
    def __init__(self, description, type=None, teller_category=None, amount=0.0, merchant_name=None, account_id=None):
        self.description = description
        self.type = type
        self.teller_category = teller_category
        self.amount = amount
        self.merchant_name = merchant_name
        self.account_id = account_id
        self.date = None  # Not needed for basic tests


def test_transfer_detection():
    # Initialize without DB for tier 1/3/4 testing
    detector = TransferDetector(db=None)

    # Test cases: (transaction, expected_result, description, expected_tier)
    test_cases = [
        # === INTERNAL TRANSFERS (Should be filtered) ===
        (
            MockTransaction("WITHDRAWAL TO 360 PERFORMANCE", type="transfer", amount=-7000.00),
            True,
            "Internal: Withdrawal to savings (type=transfer + keywords)",
            4
        ),
        (
            MockTransaction("Some transaction", teller_category="transfer", amount=-200.00),
            True,
            "Internal: Teller category says 'transfer'",
            1
        ),
        (
            MockTransaction("TRANSFER TO CHECKING", type="transfer", amount=-200.00),
            True,
            "Internal: Keywords + type=transfer",
            4
        ),
        (
            MockTransaction("TRANSFER TO CHECKING", type=None, amount=-200.00),
            True,
            "Internal: Clear keywords, no type info",
            4
        ),

        # === CREDIT CARD PAYMENTS (Should be filtered - avoid double counting) ===
        (
            MockTransaction("CHASE CREDIT CARD PAYMENT", type="ach", amount=-500.00),
            True,
            "Payment: Credit card payment (avoid double counting)",
            3
        ),
        (
            MockTransaction("AMEX PAYMENT AUTOPAY", type="ach", amount=-1200.00),
            True,
            "Payment: Amex autopay (avoid double counting)",
            3
        ),
        (
            MockTransaction("CAPITAL ONE CC PAYMENT", type="ach", amount=-350.00),
            True,
            "Payment: Capital One credit card",
            3
        ),
        (
            MockTransaction("DISCOVER CARD PAYMENT", type="ach", amount=-800.00),
            True,
            "Payment: Discover card",
            3
        ),

        # === LOAN/MORTGAGE PAYMENTS (Should be filtered) ===
        (
            MockTransaction("MORTGAGE PAYMENT", type="ach", amount=-2000.00),
            True,
            "Payment: Mortgage payment",
            3
        ),
        (
            MockTransaction("AUTO LOAN PAYMENT", type="ach", amount=-400.00),
            True,
            "Payment: Auto loan",
            3
        ),

        # === EXTERNAL PAYMENTS (Should NOT be filtered - these are REAL) ===
        (
            MockTransaction("RENT PAYMENT ACH", type="ach", amount=-1500.00),
            False,
            "External: Rent payment (ACH to landlord)",
            None
        ),
        (
            MockTransaction("PAYCHECK DEPOSIT", type="ach", amount=3000.00),
            False,
            "External: Paycheck direct deposit (REAL INCOME)",
            None
        ),
        (
            MockTransaction("ACH DEBIT 12345", type="ach", merchant_name=None, amount=-500.00),
            False,
            "External: Generic ACH payment (NOT flagged without keywords)",
            None
        ),
        (
            MockTransaction("WIRE TO JOHN DOE", type="wire", amount=-5000.00),
            False,
            "External: Wire transfer to person (REAL PAYMENT)",
            None
        ),

        # === FALSE POSITIVE PREVENTION ===
        (
            MockTransaction("TRANSFER TAPE CO.", type="card_payment", teller_category="shopping", amount=-25.00),
            False,
            "Merchant: 'TRANSFER' in name but is a store",
            None
        ),

        # === REAL PURCHASES ===
        (
            MockTransaction("HARDEE S", type="card_payment", teller_category="dining", merchant_name="Hardee's", amount=-12.50),
            False,
            "Purchase: Restaurant",
            None
        ),
        (
            MockTransaction("WALMART", type="card_payment", teller_category="shopping", merchant_name="Walmart", amount=-45.67),
            False,
            "Purchase: Retail store",
            None
        ),
        (
            MockTransaction("ATM WITHDRAWAL", type="atm", amount=-100.00),
            False,
            "Cash: ATM withdrawal",
            None
        ),
    ]

    print("Testing Production-Grade Transfer Detection")
    print("="*70)
    print("Filters: Internal transfers + Credit card/loan payments")
    print("Keeps: Rent, paycheck, bills, purchases")
    print("="*70 + "\n")

    passed = 0
    failed = 0

    for transaction, expected, desc, expected_tier in test_cases:
        result = detector.is_transfer(transaction)
        confidence = detector.get_confidence_score(transaction)

        status = "✓ PASS" if result == expected else "✗ FAIL"

        if result == expected:
            passed += 1
        else:
            failed += 1

        tier_info = f"Tier {confidence['tier']}" if confidence['tier'] else "Not flagged"
        conf_pct = f"{int(confidence['confidence'] * 100)}%" if confidence['confidence'] > 0 else "N/A"

        print(f"{status}: {desc}")
        print(f"  Transaction: {transaction.description}")
        print(f"  Type: {transaction.type} | Category: {transaction.teller_category}")
        print(f"  Detection: {tier_info} (confidence: {conf_pct})")
        print(f"  Expected: {expected}, Got: {result}")

        if confidence['signals']:
            print(f"  Signals: {confidence['signals']}")

        print()

    print("="*70)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("="*70)

    return failed == 0


if __name__ == "__main__":
    success = test_transfer_detection()
    exit(0 if success else 1)
