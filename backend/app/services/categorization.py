"""
Transaction Categorization Services

Handles transaction categorization, transfer detection, and merchant recognition.
"""
from typing import Optional, List
from datetime import timedelta
from sqlalchemy.orm import Session
import json
import os
import re
from ..models.models import Transaction, Account, TransferRule


class TransferDetector:
    """
    Production-grade transfer detection using multi-tiered approach:

    Tier 1: Structured API data (most reliable)
    Tier 2: Account matching (gold standard)
    Tier 3: Heuristic patterns (fallback - configurable)

    Rules are loaded from:
    1. JSON config file (default rules)
    2. Database (user-specific rules)
    3. Can be overridden without code changes
    """

    def __init__(self, db: Optional[Session] = None, user_id: Optional[str] = None):
        """
        Initialize detector with optional database session for account matching.

        Args:
            db: SQLAlchemy database session (enables account matching + custom rules)
            user_id: Optional user ID to load user-specific rules
        """
        self.db = db
        self.user_id = user_id

        # Load default rules from JSON config
        self._load_default_rules()

        # Load user-specific rules from database if available
        if db and user_id:
            self._load_user_rules()

    def _load_default_rules(self):
        """Load default rules from JSON configuration file."""
        config_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "config",
            "transfer_rules.json"
        )

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            self.internal_keywords = config.get("internal_transfer_keywords", [])
            self.cc_payment_keywords = config.get("credit_card_payment_keywords", [])
            self.cc_companies = config.get("credit_card_companies", [])
            self.loan_keywords = config.get("loan_payment_keywords", [])

        except FileNotFoundError:
            # Fallback to hardcoded defaults
            self.internal_keywords = [
                "WITHDRAWAL TO", "TRANSFER TO", "TRANSFER FROM",
                "INTERNAL TRANSFER", "BETWEEN ACCOUNTS",
                "ONLINE XFER", "MOBILE XFER"
            ]
            self.cc_payment_keywords = [
                "CREDIT CARD PAYMENT", "CC PAYMENT", "CARD PAYMENT",
                "PAY CREDIT CARD", "AUTOPAY"
            ]
            self.cc_companies = [
                "CHASE", "AMEX", "AMERICAN EXPRESS", "DISCOVER",
                "CAPITAL ONE", "CITI", "CITIBANK", "BANK OF AMERICA",
                "WELLS FARGO", "BARCLAYS", "SYNCHRONY", "USAA"
            ]
            self.loan_keywords = [
                "LOAN PAYMENT", "MORTGAGE PAYMENT", "AUTO PAYMENT",
                "STUDENT LOAN", "SAVINGS TRANSFER", "INVESTMENT TRANSFER"
            ]

        # User-specific rules (loaded from database)
        self.user_rules = []

    def _load_user_rules(self):
        """Load user-specific custom rules from database."""
        if not self.db or not self.user_id:
            return

        # Get user-specific and global rules
        rules = self.db.query(TransferRule).filter(
            TransferRule.is_active == True,
            (TransferRule.user_id == self.user_id) | (TransferRule.user_id == None)
        ).order_by(TransferRule.priority.desc()).all()

        self.user_rules = rules

    def is_transfer(self, transaction: Transaction) -> bool:
        """
        Multi-tiered transfer detection - ONLY FLAGS INTERNAL TRANSFERS.

        CRITICAL: External ACH payments (rent, paycheck, bills) are NOT transfers!
        Only internal movements between your own accounts should be filtered.

        Detection tiers (in order of reliability):
        1. Teller category = "transfer" (Teller's enrichment)
        2. Account matching (both sides visible = definitive internal transfer)
        3. Description pattern matching (last resort, very conservative)

        Args:
            transaction: Transaction object to analyze

        Returns:
            bool: True if INTERNAL transfer, False if external payment/income
        """
        if not transaction:
            return False

        # === TIER 1: Trust Teller's Category Enrichment ===
        # Teller's category field is their ML enrichment - trust it
        if transaction.teller_category and transaction.teller_category.lower() == "transfer":
            return True

        # === TIER 2: Account Matching (GOLD STANDARD) ===
        # If we can see both sides of the transaction = internal transfer
        if self.db and self._find_matching_transfer(transaction):
            return True

        # === TIER 3: Credit Card & External Account Payments ===
        # Detect payments to credit cards or external accounts (not real spending)
        desc_upper = transaction.description.upper()

        if self._is_payment_to_external_account(transaction):
            return True

        # === TIER 4: Custom User Rules (Highest Priority) ===
        # Check user-defined rules before using default patterns
        user_rule_result = self._check_user_rules(transaction)
        if user_rule_result is not None:
            return user_rule_result

        # === TIER 5: Description Patterns (VERY CONSERVATIVE) ===
        # Only flag if description clearly indicates internal movement
        # AND it's not a merchant purchase

        # Use configurable keywords from JSON config
        if any(kw in desc_upper for kw in self.internal_keywords):
            # Extra safety: make sure it's not a merchant
            if self._has_merchant_indicators(transaction):
                return False  # It's a purchase, not a transfer

            # Check if type suggests internal movement
            # Only flag if type is explicitly "transfer" (not ach/wire)
            if transaction.type == "transfer":
                return True

            # If no type info, be conservative - only flag if very clear keywords
            if transaction.type is None:
                # Very specific patterns that are almost certainly internal
                if any(kw in desc_upper for kw in ["WITHDRAWAL TO", "TRANSFER TO", "TRANSFER FROM"]):
                    return True

        return False

    def _check_user_rules(self, transaction: Transaction) -> Optional[bool]:
        """
        Check user-defined custom rules.

        User rules have highest priority and can override default behavior.

        Returns:
            Optional[bool]: True (is transfer), False (not transfer), None (no match)
        """
        if not self.user_rules:
            return None

        desc_upper = transaction.description.upper()

        for rule in self.user_rules:
            matched = False

            if rule.is_regex:
                # Use regex matching
                try:
                    pattern = re.compile(rule.pattern, re.IGNORECASE)
                    matched = pattern.search(transaction.description) is not None
                except re.error:
                    continue  # Invalid regex, skip
            else:
                # Simple keyword matching
                matched = rule.pattern.upper() in desc_upper

            if matched:
                # Rule matched - return based on rule type
                if rule.rule_type == "internal_transfer":
                    return True
                elif rule.rule_type == "payment":
                    return True
                elif rule.rule_type == "exclude":
                    return False  # Explicitly not a transfer

        return None  # No user rules matched

    def _is_payment_to_external_account(self, transaction: Transaction) -> bool:
        """
        Detect payments to credit cards, loans, or external financial accounts.

        These are transfers that move money to pay off debt or move between
        your own accounts at different institutions (avoiding double-counting).

        Uses configurable keywords from JSON config.

        Returns:
            bool: True if this is a payment to an external account
        """
        desc_upper = transaction.description.upper()

        # Check for explicit payment keywords (from config)
        if any(kw in desc_upper for kw in self.cc_payment_keywords):
            return True

        # Check for credit card company + payment type
        # e.g., "CHASE CREDIT CARD" or "AMEX PAYMENT"
        has_cc_company = any(company in desc_upper for company in self.cc_companies)
        has_payment_indicator = any(word in desc_upper for word in ["PAYMENT", "PAY", "AUTOPAY"])

        if has_cc_company and has_payment_indicator:
            return True

        # Check for loan payments (from config)
        if any(kw in desc_upper for kw in self.loan_keywords):
            return True

        return False

    def _find_matching_transfer(self, transaction: Transaction) -> bool:
        """
        Check if this transaction has a matching opposite transaction
        in another account (indicating an internal transfer).

        This is the GOLD STANDARD for transfer detection.

        Args:
            transaction: Transaction to find match for

        Returns:
            bool: True if matching transfer found
        """
        if not self.db:
            return False

        # Get all accounts in the same institution
        account = self.db.query(Account).filter(
            Account.id == transaction.account_id
        ).first()

        if not account:
            return False

        # Look for opposite transaction within 2 days
        date_start = transaction.date - timedelta(days=2)
        date_end = transaction.date + timedelta(days=2)

        # Opposite amount (if we sent $500, look for +$500 elsewhere)
        opposite_amount = -transaction.amount

        # Search for matching transaction in other accounts
        matching_tx = self.db.query(Transaction).join(Account).filter(
            Account.institution_id == account.institution_id,
            Account.id != transaction.account_id,  # Different account
            Transaction.amount == opposite_amount,  # Opposite amount
            Transaction.date >= date_start,
            Transaction.date <= date_end
        ).first()

        return matching_tx is not None

    def _has_merchant_indicators(self, transaction: Transaction) -> bool:
        """
        Check if transaction shows signs of being a real merchant purchase.

        Helps avoid false positives like "TRANSFER TAPE CO." (a store).

        Returns:
            bool: True if this looks like a merchant purchase
        """
        # Has a merchant name from Teller's enrichment
        if transaction.merchant_name:
            return True

        # Card payments are purchases, not transfers
        if transaction.type == "card_payment":
            return True

        # Shopping/dining categories indicate merchant
        merchant_categories = [
            "dining", "groceries", "shopping", "entertainment",
            "gas", "transportation", "travel", "health"
        ]
        if transaction.teller_category and transaction.teller_category.lower() in merchant_categories:
            return True

        return False

    def get_confidence_score(self, transaction: Transaction) -> dict:
        """
        Get detailed confidence breakdown for why transaction was/wasn't
        flagged as an internal transfer. Useful for debugging and ML training data.

        Args:
            transaction: Transaction to analyze

        Returns:
            dict: Confidence scores and reasoning
        """
        signals = {
            "is_transfer": self.is_transfer(transaction),
            "tier": None,
            "confidence": 0.0,
            "signals": {}
        }

        # Check each tier
        if transaction.teller_category == "transfer":
            signals["tier"] = 1
            signals["confidence"] = 0.90
            signals["signals"]["teller_category"] = "transfer"
        elif self._find_matching_transfer(transaction):
            signals["tier"] = 2
            signals["confidence"] = 0.95
            signals["signals"]["account_match"] = True
        elif self._is_payment_to_external_account(transaction):
            signals["tier"] = 3
            signals["confidence"] = 0.85
            signals["signals"]["payment_type"] = "external_account"
        else:
            # Check keyword matching (configurable keywords)
            desc_upper = transaction.description.upper()
            matched_keywords = [kw for kw in self.internal_keywords if kw in desc_upper]
            if matched_keywords:
                has_merchant = self._has_merchant_indicators(transaction)
                is_transfer_type = transaction.type == "transfer"

                if not has_merchant and (is_transfer_type or transaction.type is None):
                    signals["tier"] = 4
                    signals["confidence"] = 0.70
                    signals["signals"]["keywords"] = matched_keywords
                    signals["signals"]["type"] = transaction.type

        return signals

    def categorize_transfer_type(self, transaction: Transaction) -> Optional[str]:
        """
        Categorize the type of transfer for analytics.

        Args:
            transaction: Transaction object to analyze

        Returns:
            Optional[str]: Transfer type or None
        """
        if not self.is_transfer(transaction):
            return None

        # Use API type if available
        if transaction.type in ["ach", "wire"]:
            return transaction.type

        if transaction.type == "transfer":
            # Check if internal vs external
            if self._find_matching_transfer(transaction):
                return "internal"
            return "transfer"

        return "transfer"
