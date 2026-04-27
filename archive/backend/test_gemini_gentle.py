"""
Gentle Gemini Test - Just ONE Request
"""
import asyncio
from app.services.gemini_enrichment import GeminiEnrichment


class MockTransaction:
    def __init__(self, description, amount):
        self.id = "test-123"
        self.description = description
        self.amount = amount


async def test_one_transaction():
    """Test just ONE transaction with Gemini"""
    print("\n🧪 Testing Gemini with 1 simple transaction...\n")

    gemini = GeminiEnrichment()

    # Simple transaction without store numbers
    transaction = MockTransaction("STARBUCKS COFFEE", -5.75)

    print(f"Testing: {transaction.description}")
    print(f"Amount: ${abs(transaction.amount)}")
    print("\nCalling Gemini API (basic enrichment, no search)...\n")

    result = await gemini.enrich_basic(transaction)

    if result:
        print("✅ SUCCESS! Gemini is working!\n")
        print(f"Merchant: {result['merchant']}")
        print(f"Category: {result['category']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Cost: ${result['cost']} (FREE tier!)")
        print(f"Source: {result['source']}")
    else:
        print("❌ Gemini didn't return a result")
        print("This could mean:")
        print("  - API quota still at limit")
        print("  - API key needs activation")
        print("  - Free tier not enabled")

    print("\n✅ Test complete (only 1 request made)")


if __name__ == "__main__":
    asyncio.run(test_one_transaction())
