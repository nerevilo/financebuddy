"""
Test Cascade Enrichment System

Quick test to verify:
1. Semantic/Rule matching works
2. Claude Haiku enrichment works
3. Search service works
4. Cascade flow works correctly
"""
import asyncio
from app.services.search_service import SearchService
from app.services.semantic_matcher import get_semantic_matcher
from app.services.llm_enrichment import LLMEnrichmentService
from app.services.llm_enrichment_advanced import AdvancedLLMEnrichment
from app.core.config import get_settings


# Mock transaction class for testing
class MockTransaction:
    def __init__(self, description, amount):
        self.id = "test-123"
        self.description = description
        self.amount = amount
        self.enriched_merchant = None


async def test_semantic_matching():
    """Test semantic/rule matching (FREE)"""
    print("\n" + "="*50)
    print("TEST 1: Semantic/Rule Matching (FREE)")
    print("="*50)

    matcher = get_semantic_matcher()

    test_cases = [
        # Standard cases
        "Debit Card Purchase - HARDEE'S 594",
        "DOMINO S 4290",
        "WALMART SUPERCENTER",
        # KEY FIXES - these should now work correctly
        "COSTCO GAS 1234",          # Should be gas_stations, NOT groceries
        "COSTCO WHOLESALE",          # Should be groceries
        "CLAUDE.AI SUBSCRIPTION",    # Should be software_subscriptions
        "ANTHROPIC",                 # Should be software_subscriptions
        "NETFLIX.COM",               # Should be streaming
        "SOME UNKNOWN MERCHANT 123"
    ]

    for desc in test_cases:
        result = matcher.match(desc)
        if result:
            print(f"✅ {desc}")
            print(f"   → Merchant: {result.get('merchant', 'N/A')}")
            print(f"   → Category: {result['category']}")
            print(f"   → Source: {result['source']}")
            print(f"   → Confidence: {result['confidence']:.2f}")
            print(f"   → Cost: $0.00")
        else:
            print(f"❌ {desc} - No match")


async def test_claude_haiku():
    """Test Claude Haiku basic enrichment"""
    print("\n" + "="*50)
    print("TEST 2: Claude Haiku Basic ($0.00025)")
    print("="*50)

    settings = get_settings()
    if not settings.anthropic_api_key:
        print("❌ No Anthropic API key found. Skipping test.")
        return

    llm = LLMEnrichmentService()
    transaction = MockTransaction("GULF ISLANDS NATIONAL SEASHORE", -15.00)

    result = await llm.enrich_with_claude_haiku(transaction)

    if result:
        print(f"✅ Claude Haiku enrichment successful!")
        print(f"   Merchant: {result['merchant']}")
        print(f"   Category: {result['category']}")
        print(f"   Confidence: {result['confidence']}")
        print(f"   Cost: ${result['cost']}")
    else:
        print("❌ Claude Haiku enrichment failed")


async def test_search_service():
    """Test search service (DuckDuckGo fallback)"""
    print("\n" + "="*50)
    print("TEST 3: Search Service (DuckDuckGo)")
    print("="*50)

    search = SearchService()

    # Test search
    results = await search.search("Hardees store 594 location", max_results=2)

    if results:
        print(f"✅ Search successful! Found {len(results)} results")
        for i, result in enumerate(results):
            print(f"\nResult {i+1}:")
            print(f"  Title: {result['title']}")
            print(f"  Snippet: {result['snippet'][:100]}...")
            print(f"  Source: {result['source']}")
    else:
        print("⚠️  No search results (this is expected with DuckDuckGo rate limits)")
        print("   Search would work with Tavily API key")


async def test_claude_with_search():
    """Test Claude Haiku with search tools"""
    print("\n" + "="*50)
    print("TEST 4: Claude Haiku + Search ($0.00525)")
    print("="*50)

    settings = get_settings()
    if not settings.anthropic_api_key:
        print("❌ No Anthropic API key found. Skipping test.")
        return

    llm_advanced = AdvancedLLMEnrichment()
    transaction = MockTransaction("HARDEE'S 594", -8.50)

    print("Testing with 'HARDEE'S 594' (has store number)...")
    result = await llm_advanced.enrich_with_search(transaction)

    if result:
        print(f"✅ Claude + Search successful!")
        print(f"   Merchant: {result['merchant']}")
        print(f"   Category: {result['category']}")
        print(f"   Address: {result.get('address', 'N/A')}")
        print(f"   City: {result.get('city', 'N/A')}")
        print(f"   State: {result.get('state', 'N/A')}")
        print(f"   Searched: {result.get('searched', False)}")
        if result.get('search_query'):
            print(f"   Search query: {result['search_query']}")
        print(f"   Confidence: {result['confidence']}")
        print(f"   Cost: ${result['cost']}")
    else:
        print("❌ Claude + Search failed")


async def test_cascade_full():
    """Test full cascade flow"""
    print("\n" + "="*50)
    print("TEST 5: Full Cascade Flow")
    print("="*50)

    from app.services.cascade_enrichment import CascadeEnrichment

    cascade = CascadeEnrichment()

    test_transactions = [
        ("WALMART SUPERCENTER", -45.67),      # Should match semantic rule → groceries
        ("COSTCO GAS 1234", -52.00),          # Should match semantic rule → gas_stations (KEY FIX!)
        ("COSTCO WHOLESALE", -156.00),        # Should match semantic rule → groceries
        ("CLAUDE.AI SUBSCRIPTION", -20.00),   # Should match semantic rule → software_subscriptions (KEY FIX!)
        ("ANTHROPIC", -20.00),                # Should match semantic rule → software_subscriptions
        ("NETFLIX.COM", -15.99),              # Should match semantic rule → streaming
        ("UNKNOWN COFFEE SHOP", -4.50),       # Should use LLM basic
        ("HARDEE'S 594", -8.50),              # Should match semantic rule → fast_food
    ]

    for desc, amount in test_transactions:
        print(f"\nTesting: {desc}")
        transaction = MockTransaction(desc, amount)

        result = await cascade.enrich_transaction(transaction)

        print(f"  Method used: {result['method_used']}")
        print(f"  Merchant: {result.get('merchant', 'N/A')}")
        print(f"  Category: {result.get('category', 'N/A')}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Cost: ${result['cost']}")

    # Print final stats
    print("\n" + "-"*50)
    print("FINAL STATS:")
    stats = cascade.get_stats()
    print(f"Total transactions: {stats['total_transactions']}")
    print(f"Total cost: ${stats['total_cost']}")
    print(f"Cost per transaction: ${stats['cost_per_transaction']}")
    print(f"Methods used: {stats['methods_used']}")
    print(f"Ntropy would cost: ${stats['ntropy_cost_would_be']}")
    print(f"Savings: ${stats['savings_amount']} ({stats['savings_percent']}%)")


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 CASCADE ENRICHMENT SYSTEM TEST")
    print("="*70)

    # Test each component
    await test_semantic_matching()
    await test_claude_haiku()
    await test_search_service()
    await test_claude_with_search()
    await test_cascade_full()

    print("\n" + "="*70)
    print("✅ All tests complete!")
    print("="*70)
    print("\nNext steps:")
    print("1. Add Tavily API key to .env for better search results")
    print("2. Test with real transactions via API")
    print("3. Run batch enrichment: POST /categorization/cascade/enrich/all")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
