"""
Enrich All 791 Transactions from SQLite with Cascade Enrichment
"""
import asyncio
import sqlite3
from app.services.cascade_enrichment import CascadeEnrichment


class MockTransaction:
    """Mock transaction object for testing"""
    def __init__(self, id, description, amount, date):
        self.id = id
        self.description = description
        self.amount = amount
        self.date = date
        self.enriched_merchant = None


async def enrich_all_transactions():
    """Enrich all 791 transactions"""

    print("\n" + "="*80)
    print("🚀 ENRICHING ALL 791 TRANSACTIONS")
    print("="*80)

    # Connect to SQLite
    conn = sqlite3.connect('fintrack.db')
    cursor = conn.cursor()

    # Get all unenriched transactions
    cursor.execute("""
        SELECT id, description, amount, date
        FROM transactions
        WHERE enriched_merchant IS NULL
        ORDER BY date DESC
    """)

    rows = cursor.fetchall()
    total_count = len(rows)

    if not rows:
        print("❌ No unenriched transactions found in database!")
        conn.close()
        return

    print(f"\n✅ Found {total_count} transactions to enrich")
    print(f"📊 Estimated time: 5-10 minutes")
    print(f"💰 Estimated cost: $0.20-0.30\n")
    print("Starting enrichment...\n")
    print("-"*80)

    # Initialize cascade enrichment
    cascade = CascadeEnrichment()

    results = []
    enriched_count = 0
    skipped_count = 0
    failed_count = 0

    for i, row in enumerate(rows, 1):
        txn_id, description, amount, date = row
        transaction = MockTransaction(txn_id, description, amount, date)

        # Print progress every 50 transactions
        if i % 50 == 0 or i == 1:
            print(f"\n📍 Progress: {i}/{total_count} ({i/total_count*100:.1f}%)")

        # Enrich
        try:
            result = await cascade.enrich_transaction(transaction)
            results.append(result)

            # Save to database
            if result.get('merchant'):
                # Real merchant - save enrichment
                cursor.execute("""
                    UPDATE transactions
                    SET enriched_merchant = ?,
                        enriched_category = ?,
                        categorization_source = ?,
                        categorization_confidence = ?,
                        enriched_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    result['merchant'],
                    result['category'],
                    result.get('method_used', 'unknown'),
                    result.get('confidence', 0.0),
                    txn_id
                ))
                conn.commit()
                enriched_count += 1
                if i <= 10 or i % 100 == 0:  # Show first 10 and every 100th
                    print(f"   ✅ #{i}: {result['merchant']} ({result['category']}) - {result['method_used']}")
            elif result.get('category') in ['internal_transfer', 'p2p_transfer']:
                # Internal transaction - mark as skipped
                cursor.execute("""
                    UPDATE transactions
                    SET enriched_category = ?,
                        categorization_source = 'skipped',
                        categorization_confidence = 1.0,
                        enriched_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (result['category'], txn_id))
                conn.commit()
                skipped_count += 1
                if i <= 10 or i % 100 == 0:
                    print(f"   ⏭️  #{i}: Skipped - {result['category']}")
            else:
                failed_count += 1
                if i <= 10:
                    print(f"   ❌ #{i}: Failed to enrich")

        except Exception as e:
            print(f"   ❌ Error on transaction {i}: {e}")
            failed_count += 1

    conn.close()

    # Final Summary
    print("\n" + "="*80)
    print("🎉 ENRICHMENT COMPLETE!")
    print("="*80)

    stats = cascade.get_stats()

    print(f"\n📊 Results Summary:")
    print(f"   Total processed: {total_count}")
    print(f"   ✅ Successfully enriched: {enriched_count}")
    print(f"   ⏭️  Skipped (internal/P2P): {skipped_count}")
    print(f"   ❌ Failed: {failed_count}")

    print(f"\n💰 Cost Analysis:")
    print(f"   Total cost: ${stats['total_cost']:.2f}")
    print(f"   Average per transaction: ${stats['cost_per_transaction']:.6f}")

    print(f"\n📈 Methods Used:")
    for method, count in stats['methods_used'].items():
        if count > 0:
            percentage = (count / total_count) * 100
            print(f"   - {method}: {count} ({percentage:.1f}%)")

    print(f"\n💸 Cost Breakdown:")
    for method, cost in stats['cost_by_method'].items():
        if cost > 0:
            print(f"   - {method}: ${cost:.4f}")

    print(f"\n🎯 Savings vs Ntropy-Only:")
    print(f"   Ntropy would cost: ${stats['ntropy_cost_would_be']:.2f}")
    print(f"   You paid: ${stats['total_cost']:.2f}")
    print(f"   💰 Saved: ${stats['savings_amount']:.2f} ({stats['savings_percent']:.1f}%)")

    print("\n" + "="*80)
    print("✨ Next Steps:")
    print("   1. Review the enriched data in your database")
    print("   2. Build a dashboard to visualize spending patterns")
    print("   3. Prepare for friends/family beta testing")
    print("="*80 + "\n")

    # Save detailed results to file
    with open('enrichment_results.txt', 'w') as f:
        f.write("Enrichment Results\n")
        f.write("="*80 + "\n\n")
        f.write(f"Total processed: {total_count}\n")
        f.write(f"Enriched: {enriched_count}\n")
        f.write(f"Skipped: {skipped_count}\n")
        f.write(f"Failed: {failed_count}\n")
        f.write(f"\nTotal cost: ${stats['total_cost']:.2f}\n")
        f.write(f"Savings: ${stats['savings_amount']:.2f} ({stats['savings_percent']:.1f}%)\n")

    print("📝 Detailed results saved to: enrichment_results.txt\n")


if __name__ == "__main__":
    asyncio.run(enrich_all_transactions())
