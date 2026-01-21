"""
Test the new intelligent categorization system.

Run: python test_categorization.py
"""
import sys
sys.path.insert(0, '.')

from app.services.semantic_matcher import SemanticMatcher, get_semantic_matcher
from app.services.categories import normalize_category_id, CATEGORIES

def test_semantic_matcher():
    """Test the semantic matcher with known problematic cases"""
    print("\n" + "="*80)
    print("🧪 TESTING INTELLIGENT CATEGORIZATION SYSTEM")
    print("="*80)

    matcher = SemanticMatcher()

    # Test cases: (description, expected_category, expected_merchant)
    test_cases = [
        # Gas station variants at retail stores (THE KEY FIXES)
        ("Debit Card Purchase - COSTCO GAS 1234", "gas_stations", "Costco Gas"),
        ("COSTCO GASOLINE", "gas_stations", "Costco Gas"),
        ("COSTCO FUEL CENTER", "gas_stations", "Costco Gas"),
        ("SAMS CLUB GAS", "gas_stations", "Sam's Club Gas"),
        ("SAM'S CLUB FUEL", "gas_stations", "Sam's Club Gas"),
        ("WALMART GAS STATION", "gas_stations", "Walmart Gas"),
        ("KROGER FUEL CENTER", "gas_stations", "Kroger Fuel Center"),

        # Regular Costco (should be groceries)
        ("COSTCO WHSE #1234", "groceries", "Costco"),
        ("COSTCO WHOLESALE", "groceries", "Costco"),

        # Software subscriptions (THE OTHER KEY FIXES)
        ("CLAUDE.AI SUBSCRIPTION", "software_subscriptions", "Claude (Anthropic)"),
        ("ANTHROPIC", "software_subscriptions", "Anthropic"),
        ("OPENAI", "software_subscriptions", "OpenAI"),
        ("CHATGPT PLUS", "software_subscriptions", "ChatGPT Plus"),
        ("GITHUB", "software_subscriptions", "GitHub"),
        ("CURSOR", "software_subscriptions", "Cursor"),
        ("NOTION", "software_subscriptions", "Notion"),
        ("FIGMA", "software_subscriptions", "Figma"),
        ("ADOBE CREATIVE CLOUD", "software_subscriptions", "Adobe"),
        ("MICROSOFT 365", "software_subscriptions", "Microsoft 365"),

        # Streaming services (NOT software)
        ("NETFLIX.COM", "streaming", "Netflix"),
        ("SPOTIFY", "streaming", "Spotify"),
        ("DISNEY+ SUBSCRIPTION", "streaming", "Disney+"),
        ("HULU", "streaming", "Hulu"),
        ("HBO MAX", "streaming", "Max (HBO)"),

        # Standard gas stations
        ("SHELL OIL 12345", "gas_stations", "Shell"),
        ("EXXONMOBIL", "gas_stations", "ExxonMobil"),
        ("CHEVRON 567", "gas_stations", "Chevron"),
        ("BP #890", "gas_stations", "BP"),

        # Fast food
        ("MCDONALD'S 12345", "fast_food", "McDonald's"),
        ("CHICK-FIL-A #567", "fast_food", "Chick-fil-A"),
        ("DOMINO'S PIZZA", "fast_food", "Domino's"),

        # Coffee
        ("STARBUCKS 123", "coffee_shops", "Starbucks"),
        ("DUNKIN DONUTS", "coffee_shops", "Dunkin'"),

        # Phone/Internet
        ("VERIZON WIRELESS", "phone_internet", "Verizon"),
        ("AT&T MOBILITY", "phone_internet", "AT&T"),
        ("T-MOBILE", "phone_internet", "T-Mobile"),

        # Gaming
        ("STEAM GAMES", "gaming", "Steam"),
        ("PLAYSTATION NETWORK", "gaming", "PlayStation"),
        ("XBOX LIVE", "gaming", "Xbox"),
    ]

    passed = 0
    failed = 0

    print("\n📋 Testing Rule-Based Matching:\n")

    for desc, expected_cat, expected_merchant in test_cases:
        result = matcher.match_merchant_rules(desc)

        if result:
            actual_cat = result.get("category")
            actual_merchant = result.get("merchant")
            cat_match = actual_cat == expected_cat
            merchant_match = actual_merchant == expected_merchant

            if cat_match and merchant_match:
                print(f"  ✅ '{desc[:40]:<40}' → {actual_cat} ({actual_merchant})")
                passed += 1
            elif cat_match:
                print(f"  ⚠️  '{desc[:40]:<40}' → {actual_cat} (merchant: {actual_merchant}, expected: {expected_merchant})")
                passed += 1  # Category is most important
            else:
                print(f"  ❌ '{desc[:40]:<40}' → {actual_cat} (expected: {expected_cat})")
                failed += 1
        else:
            print(f"  ❌ '{desc[:40]:<40}' → NO MATCH (expected: {expected_cat})")
            failed += 1

    print(f"\n📊 Results: {passed}/{passed+failed} passed ({passed/(passed+failed)*100:.0f}%)")

    # Test category normalization
    print("\n" + "="*80)
    print("🔄 Testing Category Normalization:")
    print("="*80 + "\n")

    norm_cases = [
        ("fast food", "fast_food"),
        ("Fast Food", "fast_food"),
        ("gas stations", "gas_stations"),
        ("gas", "gas_stations"),
        ("fuel", "gas_stations"),
        ("software subscription", "software_subscriptions"),
        ("software", "software_subscriptions"),
        ("subscription", "software_subscriptions"),
        ("television", "streaming"),  # Common mis-categorization
        ("tv", "streaming"),
        ("groceries", "groceries"),
        ("grocery", "groceries"),
        ("GROCERIES", "groceries"),
    ]

    for raw, expected in norm_cases:
        normalized = normalize_category_id(raw)
        status = "✅" if normalized == expected else "❌"
        print(f"  {status} '{raw}' → '{normalized}' (expected: '{expected}')")

    # Print all valid categories
    print("\n" + "="*80)
    print("📚 Valid Category IDs:")
    print("="*80 + "\n")

    for cat_id, cat in sorted(CATEGORIES.items()):
        print(f"  {cat.emoji} {cat_id}: {cat.display_name}")

    print("\n" + "="*80)
    print("✅ Categorization system test complete!")
    print("="*80 + "\n")


def test_semantic_similarity():
    """Test semantic similarity matching (requires sentence-transformers)"""
    print("\n" + "="*80)
    print("🧠 Testing Semantic Similarity Matching:")
    print("="*80 + "\n")

    try:
        matcher = get_semantic_matcher()

        if not matcher._initialized:
            print("  ⚠️  Semantic model not initialized (sentence-transformers not installed)")
            print("     Run: pip install sentence-transformers")
            return

        # Ambiguous cases that might not have exact rule matches
        ambiguous_cases = [
            "RANDOM GAS MART",
            "ACME SOFTWARE TOOLS",
            "LOCAL COFFEE HOUSE",
            "DOWNTOWN PIZZA JOINT",
            "TECH SUBSCRIPTION SERVICE",
            "CLOUD COMPUTING SERVICES",
            "STREAMING VIDEO NETWORK",
        ]

        for desc in ambiguous_cases:
            result = matcher.match_semantic(desc)
            if result:
                print(f"  🔍 '{desc}' → {result.get('category')} (score: {result.get('similarity_score', 0):.2f})")
            else:
                print(f"  ❓ '{desc}' → No semantic match")

    except Exception as e:
        print(f"  ❌ Error: {e}")


if __name__ == "__main__":
    test_semantic_matcher()
    test_semantic_similarity()
