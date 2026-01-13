"""
Verify Enrichment Quality by Comparing Against Ntropy
"""
import asyncio
import sqlite3
import random
from app.services.cascade_enrichment import CascadeEnrichment
from app.services.ntropy_client import NtropyClient


class MockTransaction:
    """Mock transaction object"""
    def __init__(self, id, description, amount, date, enriched_merchant=None, enriched_category=None):
        self.id = id
        self.description = description
        self.amount = amount
        self.date = date
        self.enriched_merchant = enriched_merchant
        self.enriched_category = enriched_category


async def verify_quality(sample_size=30):
    """
    Verify enrichment quality by comparing our results with Ntropy

    Process:
    1. Get a random sample of enriched transactions
    2. Re-enrich them with Ntropy (forced)
    3. Compare results side-by-side
    4. Calculate accuracy metrics
    """

    print("\n" + "="*100)
    print("🔍 VERIFYING ENRICHMENT QUALITY")
    print("="*100)
    print(f"\nSample size: {sample_size} transactions")
    print(f"Cost: ~${sample_size * 0.02:.2f} (Ntropy API calls)")
    print("\nThis will compare our enrichment against Ntropy's premium service...\n")

    # Connect to SQLite
    conn = sqlite3.connect('fintrack.db')
    cursor = conn.cursor()

    # Get only successfully enriched transactions (not skipped internal transfers)
    cursor.execute("""
        SELECT id, description, amount, date, enriched_merchant, enriched_category
        FROM transactions
        WHERE enriched_merchant IS NOT NULL
        ORDER BY RANDOM()
        LIMIT ?
    """, (sample_size,))

    rows = cursor.fetchall()
    conn.close()

    if len(rows) < sample_size:
        print(f"⚠️  Only found {len(rows)} enriched transactions")
        sample_size = len(rows)

    print(f"✅ Selected {sample_size} random enriched transactions\n")
    print("-"*100)

    # Initialize services
    cascade = CascadeEnrichment()
    ntropy = NtropyClient()

    # Check if Ntropy is configured
    if not ntropy.api_key:
        print("\n❌ Ntropy API key not configured!")
        print("Please add NTROPY_API_KEY to .env file to run this comparison.")
        return

    results = []
    exact_matches = 0
    similar_matches = 0
    disagreements = 0
    our_better = 0
    ntropy_better = 0

    for i, row in enumerate(rows, 1):
        txn_id, description, amount, date, our_merchant, our_category = row
        transaction = MockTransaction(txn_id, description, amount, date)

        print(f"\n{i}. Transaction: {description}")
        print(f"   Amount: ${abs(amount):.2f}")
        print(f"   📦 Our Result: {our_merchant} ({our_category})")

        # Get Ntropy enrichment
        try:
            ntropy_result = await cascade.enrich_transaction(transaction, force_method='ntropy')

            if ntropy_result and ntropy_result.get('merchant'):
                ntropy_merchant = ntropy_result['merchant']
                ntropy_category = ntropy_result['category']

                print(f"   🏆 Ntropy:     {ntropy_merchant} ({ntropy_category})")

                # Compare results
                merchant_match = our_merchant.lower().strip() == ntropy_merchant.lower().strip()
                category_match = our_category.lower().strip() == ntropy_category.lower().strip()

                # Fuzzy match for merchant names (e.g., "Domino's" vs "Domino's Pizza")
                fuzzy_merchant_match = (
                    our_merchant.lower() in ntropy_merchant.lower() or
                    ntropy_merchant.lower() in our_merchant.lower()
                )

                if merchant_match and category_match:
                    print(f"   ✅ EXACT MATCH")
                    exact_matches += 1
                elif fuzzy_merchant_match and category_match:
                    print(f"   ✅ SIMILAR MATCH (merchant name slightly different)")
                    similar_matches += 1
                elif category_match:
                    print(f"   ⚠️  CATEGORY MATCH (different merchant name)")
                    # Manual judgment needed
                    print(f"      Which is better? 1=Ours, 2=Ntropy, 3=Similar")
                    disagreements += 1
                else:
                    print(f"   ❌ DISAGREEMENT")
                    print(f"      Which is correct? 1=Ours, 2=Ntropy, 3=Both acceptable")
                    disagreements += 1

                results.append({
                    'description': description,
                    'our_merchant': our_merchant,
                    'our_category': our_category,
                    'ntropy_merchant': ntropy_merchant,
                    'ntropy_category': ntropy_category,
                    'match': merchant_match and category_match
                })
            else:
                print(f"   ❌ Ntropy failed to enrich")

        except Exception as e:
            print(f"   ❌ Error calling Ntropy: {e}")

        # Small delay to avoid rate limits
        await asyncio.sleep(0.5)

    # Summary
    print("\n" + "="*100)
    print("📊 QUALITY VERIFICATION SUMMARY")
    print("="*100)

    total = len(results)
    if total > 0:
        exact_rate = (exact_matches / total) * 100
        similar_rate = (similar_matches / total) * 100
        combined_rate = ((exact_matches + similar_matches) / total) * 100

        print(f"\n✅ Exact Matches: {exact_matches}/{total} ({exact_rate:.1f}%)")
        print(f"✅ Similar Matches: {similar_matches}/{total} ({similar_rate:.1f}%)")
        print(f"📊 Combined Accuracy: {exact_matches + similar_matches}/{total} ({combined_rate:.1f}%)")
        print(f"⚠️  Disagreements: {disagreements}/{total} ({disagreements/total*100:.1f}%)")

        # Cost comparison
        our_cost = 0.05  # What we actually paid
        ntropy_cost = total * 0.02  # What this verification cost
        full_ntropy_cost = 791 * 0.02  # What full Ntropy would cost

        print(f"\n💰 Cost Analysis:")
        print(f"   Our full enrichment cost: $0.05")
        print(f"   This verification cost: ${ntropy_cost:.2f}")
        print(f"   Full Ntropy would cost: ${full_ntropy_cost:.2f}")

        if combined_rate >= 90:
            print(f"\n🎉 EXCELLENT! Our enrichment is {combined_rate:.1f}% accurate vs Ntropy")
            print(f"   You saved ${full_ntropy_cost - 0.05:.2f} ({(1 - 0.05/full_ntropy_cost)*100:.1f}%) with similar quality!")
        elif combined_rate >= 75:
            print(f"\n✅ GOOD! Our enrichment is {combined_rate:.1f}% accurate vs Ntropy")
            print(f"   Some differences may be acceptable (e.g., 'Domino's' vs 'Domino's Pizza')")
        else:
            print(f"\n⚠️  WARNING! Only {combined_rate:.1f}% accuracy")
            print(f"   May need to improve pattern matching or use Ntropy more often")

        # Show some examples of disagreements
        if disagreements > 0:
            print(f"\n📋 Example Disagreements (manual review needed):")
            disagreement_examples = [r for r in results if not r['match']][:5]
            for ex in disagreement_examples:
                print(f"\n   '{ex['description']}'")
                print(f"   Ours:   {ex['our_merchant']} ({ex['our_category']})")
                print(f"   Ntropy: {ex['ntropy_merchant']} ({ex['ntropy_category']})")

    print("\n" + "="*100)
    print("✅ Verification complete!")
    print("="*100 + "\n")


if __name__ == "__main__":
    asyncio.run(verify_quality(sample_size=30))
