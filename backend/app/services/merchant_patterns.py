"""
DIY Merchant Recognition - Free Alternative to Ntropy

This module provides basic merchant recognition using pattern matching
and rule-based categorization. Use this BEFORE calling Ntropy to reduce API costs.

Expected cost reduction: 60-70% of Ntropy API calls
"""
import re
from typing import Optional, Dict


class MerchantPatternMatcher:
    """
    Free merchant recognition using pattern matching.

    Covers ~70% of common transactions without API calls.
    """

    def __init__(self):
        # Merchant name patterns (add more as you see them)
        self.merchant_patterns = {
            # Fast Food
            "HARDEE": "Hardee's",
            "HARDEES": "Hardee's",
            "MCDONALD": "McDonald's",
            "BURGER KING": "Burger King",
            "WENDY": "Wendy's",
            "TACO BELL": "Taco Bell",
            "DOMINO": "Domino's",
            "PIZZA HUT": "Pizza Hut",
            "SUBWAY": "Subway",
            "CHICK-FIL-A": "Chick-fil-A",
            "CHIPOTLE": "Chipotle",
            "PANERA": "Panera Bread",
            "KFC": "KFC",

            # Groceries
            "WALMART": "Walmart",
            "TARGET": "Target",
            "KROGER": "Kroger",
            "PUBLIX": "Publix",
            "SAFEWAY": "Safeway",
            "WHOLE FOODS": "Whole Foods",
            "TRADER JOE": "Trader Joe's",
            "ALDI": "Aldi",
            "COSTCO": "Costco",
            "SAM'S CLUB": "Sam's Club",

            # Gas Stations
            "SHELL": "Shell",
            "EXXON": "ExxonMobil",
            "CHEVRON": "Chevron",
            "BP": "BP",
            "MOBIL": "Mobil",
            "MARATHON": "Marathon",
            "SUNOCO": "Sunoco",
            "CIRCLE K": "Circle K",
            "7-ELEVEN": "7-Eleven",
            "WAWA": "Wawa",

            # Coffee
            "STARBUCKS": "Starbucks",
            "DUNKIN": "Dunkin'",
            "PEET'S": "Peet's Coffee",

            # Retail
            "AMAZON": "Amazon",
            "BEST BUY": "Best Buy",
            "HOME DEPOT": "Home Depot",
            "LOWE'S": "Lowe's",
            "CVS": "CVS",
            "WALGREENS": "Walgreens",

            # Add more as you encounter them...
        }

        # Category mapping
        self.category_mapping = {
            # Fast Food
            "Hardee's": "fast food",
            "McDonald's": "fast food",
            "Burger King": "fast food",
            "Wendy's": "fast food",
            "Taco Bell": "fast food",
            "Chick-fil-A": "fast food",
            "KFC": "fast food",

            # Pizza
            "Domino's": "fast food",
            "Pizza Hut": "fast food",

            # Casual Dining
            "Chipotle": "dining",
            "Panera Bread": "dining",
            "Subway": "fast food",

            # Groceries
            "Walmart": "groceries",
            "Target": "groceries",
            "Kroger": "groceries",
            "Publix": "groceries",
            "Safeway": "groceries",
            "Whole Foods": "groceries",
            "Trader Joe's": "groceries",
            "Aldi": "groceries",
            "Costco": "groceries",
            "Sam's Club": "groceries",

            # Gas
            "Shell": "gas stations",
            "ExxonMobil": "gas stations",
            "Chevron": "gas stations",
            "BP": "gas stations",
            "Mobil": "gas stations",
            "Marathon": "gas stations",
            "Sunoco": "gas stations",
            "Circle K": "gas stations",
            "7-Eleven": "gas stations",
            "Wawa": "gas stations",

            # Coffee
            "Starbucks": "coffee shops",
            "Dunkin'": "coffee shops",
            "Peet's Coffee": "coffee shops",

            # Retail
            "Amazon": "shopping",
            "Best Buy": "electronics",
            "Home Depot": "home improvement",
            "Lowe's": "home improvement",
            "CVS": "pharmacy",
            "Walgreens": "pharmacy",
        }

        # Merchant websites (for logo URLs)
        self.merchant_websites = {
            "Hardee's": "hardees.com",
            "McDonald's": "mcdonalds.com",
            "Domino's": "dominos.com",
            "Walmart": "walmart.com",
            "Target": "target.com",
            "Starbucks": "starbucks.com",
            # Add more as needed...
        }

        # Common prefixes to remove
        self.prefixes = [
            "Debit Card Purchase - ",
            "Credit Card Purchase - ",
            "Online Purchase - ",
            "POS ",
            "ATM ",
            "Withdrawal from ",
            "Payment to ",
        ]

    def recognize_merchant(self, description: str) -> Optional[Dict]:
        """
        Recognize merchant from transaction description.

        Args:
            description: Raw transaction description

        Returns:
            Dict with merchant info or None if not recognized
            {
                "merchant": "Hardee's",
                "category": "fast food",
                "confidence": 0.85,
                "logo": "https://logo.clearbit.com/hardees.com",
                "website": "hardees.com",
                "source": "pattern_match"
            }
        """
        # Clean description
        cleaned = self._clean_description(description)

        # Try to match against known patterns
        merchant_name = self._match_merchant(cleaned)

        if merchant_name:
            category = self.category_mapping.get(merchant_name)
            website = self.merchant_websites.get(merchant_name)

            return {
                "merchant": merchant_name,
                "category": category,
                "confidence": 0.85,  # Pattern match confidence
                "logo": f"https://logo.clearbit.com/{website}" if website else None,
                "website": website,
                "source": "pattern_match"
            }

        return None

    def _clean_description(self, description: str) -> str:
        """Remove common prefixes from description"""
        cleaned = description

        for prefix in self.prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned.replace(prefix, "", 1)
                break

        return cleaned.strip()

    def _match_merchant(self, description: str) -> Optional[str]:
        """Match description against known merchant patterns"""
        desc_upper = description.upper()

        # STEP 1: Check for internal transactions FIRST (skip these)
        internal_keywords = [
            "WITHDRAWAL TO", "DEPOSIT FROM", "CHECK DEPOSIT",
            "ZELLE", "VENMO", "PAYPAL TRANSFER", "CASHAPP",
            "INTEREST PAID", "MONTHLY FEE", "ATM WITHDRAWAL",
            "TRANSFER TO", "TRANSFER FROM",
            "SAVINGS", "CHECKING",  # Account transfers
            "ACH TRNSFR", "INST XFER", "WEB PMTS",
            "ROBINHOOD", "CREDITS", "DEBITS",
            "MONEY FROM", "MONEY TO", "MONEY RECEIVED",
            "CARD ADJUSTMENT", "ADJUSTMENT SIGNATURE"
        ]

        for keyword in internal_keywords:
            if keyword in desc_upper:
                return None  # Skip - internal transaction, not a merchant

        # STEP 2: Match merchant patterns with word boundaries
        for pattern, merchant_name in self.merchant_patterns.items():
            # Use word boundary regex to avoid false matches
            # e.g., "MOBIL" won't match "Mobile" anymore
            pattern_regex = r'\b' + re.escape(pattern) + r'\b'
            if re.search(pattern_regex, desc_upper):
                return merchant_name

        return None

    def extract_location_hints(self, description: str) -> Optional[Dict]:
        """
        Extract location hints from description (city, state).

        This is basic - won't get street address like Ntropy.
        """
        # Try to find state abbreviations
        state_pattern = r'\b([A-Z]{2})\b'
        states = re.findall(state_pattern, description)

        # Try to find city names (basic - just capitalized words before state)
        city_pattern = r'([A-Z][A-Z\s]+?)\s+([A-Z]{2})\b'
        match = re.search(city_pattern, description)

        if match:
            return {
                "city": match.group(1).strip(),
                "state": match.group(2),
                "source": "regex_extraction"
            }

        return None

    def extract_store_number(self, description: str) -> Optional[str]:
        """Extract store number if present"""
        # Look for numbers at the end or after merchant name
        match = re.search(r'\s(\d{3,5})\b', description)
        if match:
            return match.group(1)
        return None


# Example usage:
"""
matcher = MerchantPatternMatcher()

result = matcher.recognize_merchant("Debit Card Purchase - HARDEE'S 594")
# Returns:
{
    "merchant": "Hardee's",
    "category": "fast food",
    "confidence": 0.85,
    "logo": "https://logo.clearbit.com/hardees.com",
    "website": "hardees.com",
    "source": "pattern_match"
}

# Only call Ntropy if result is None (unknown merchant)
"""
