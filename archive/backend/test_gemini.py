"""
Test Gemini Enrichment with Real Tavily Search

Quick test to verify Gemini + Tavily integration works perfectly
"""
import asyncio
from app.services.gemini_enrichment import GeminiEnrichment


# Mock transaction class
class MockTransaction:
    def __init__(self, description, amount):
        self.id = "test-123"
        self.description = description
        self.amount = amount
        self.enriched_merchant = None


async def test_gemini_basic():
    """Test Gemini basic enrichment (FREE!)"""
    print("\n" + "="*60)
    print("TEST 1: Gemini Flash Basic (FREE!)")
    print("="*60)

    gemini = GeminiEnrichment()

    test_cases = [
        ("GULF ISLANDS NATIONAL SEASHORE", -15.00),
        ("SPOTIFY PREMIUM", -9.99),
        ("CHIPOTLE 1234", -12.50),
    ]

    for desc, amount in test_cases:
        print(f"\nTesting: {desc}")
        transaction = MockTransaction(desc, amount)

        result = await gemini.enrich_basic(transaction)

        if result:
            print(f"  ✅ Merchant: {result['merchant']}")
            print(f"  ✅ Category: {result['category']}")
            print(f"  ✅ Confidence: {result['confidence']}")
            print(f"  ✅ Cost: ${result['cost']} (FREE tier!)")
        else:
            print(f"  ❌ Failed")


async def test_gemini_with_search():
    """Test Gemini with Tavily search (store location detection)"""
    print("\n" + "="*60)
    print("TEST 2: Gemini Flash + Tavily Search")
    print("="*60)

    gemini = GeminiEnrichment()

    # Transactions with store numbers
    test_cases = [
        ("HARDEE'S 594", -8.50),
        ("DOMINO S 4290", -18.99),
        ("STARBUCKS 12345", -5.75),
    ]

    for desc, amount in test_cases:
        print(f"\nTesting: {desc}")
        transaction = MockTransaction(desc, amount)

        result = await gemini.enrich_with_search(transaction)

        if result:
            print(f"  ✅ Merchant: {result['merchant']}")
            print(f"  ✅ Category: {result['category']}")
            if result.get('address'):
                print(f"  🏠 Address: {result['address']}")
            if result.get('city'):
                print(f"  📍 City: {result['city']}, {result.get('state', '')}")
            print(f"  🔍 Searched: {result.get('searched', False)}")
            if result.get('search_query'):
                print(f"  🔎 Query: {result['search_query']}")
            print(f"  ✅ Confidence: {result['confidence']}")
            print(f"  💰 Cost: ${result['cost']}")
        else:
            print(f"  ❌ Failed")


async def test_cascade_gemini():
    """Test full cascade with Gemini"""
    print("\n" + "="*60)
    print("TEST 3: Full Cascade (Pattern → Gemini → Search → Ntropy)")
    print("="*60)

    from app.services.cascade_enrichment import CascadeEnrichment

    cascade = CascadeEnrichment()

    test_transactions = [
        ("WALMART SUPERCENTER", -45.67),  # Should match pattern
        ("TRADER JOES", -32.15),          # Should use Gemini basic
        ("HARDEE'S 594", -8.50),          # Should use Gemini + search
    ]

    for desc, amount in test_transactions:
        print(f"\nTesting: {desc}")
        transaction = MockTransaction(desc, amount)

        result = await cascade.enrich_transaction(transaction)

        print(f"  Method: {result['method_used']}")
        print(f"  Merchant: {result.get('merchant', 'N/A')}")
        print(f"  Category: {result.get('category', 'N/A')}")
        if result.get('address'):
            print(f"  Address: {result['address']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Cost: ${result['cost']}")

    # Print stats
    print("\n" + "-"*60)
    print("STATS:")
    stats = cascade.get_stats()
    print(f"  Total cost: ${stats['total_cost']}")
    print(f"  Methods: {stats['methods_used']}")
    print(f"  Ntropy would cost: ${stats['ntropy_cost_would_be']}")
    print(f"  Savings: ${stats['savings_amount']} ({stats['savings_percent']}%)")


async def main():
    """Run all Gemini tests"""
    print("\n" + "="*60)
    print("🤖 GEMINI + TAVILY ENRICHMENT TEST")
    print("="*60)
    print("\nGemini Flash: FREE for 1,500 requests/day!")
    print("Tavily Search: FREE for 1,000 searches/month!")
    print("="*60)

    await test_gemini_basic()
    await test_gemini_with_search()
    await test_cascade_gemini()

    print("\n" + "="*60)
    print("✅ All tests complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Test with your real 791 transactions")
    print("2. Watch patterns auto-learn from enrichments")
    print("3. Cost goes down with each batch!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
