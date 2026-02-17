"""
Fast Parallel Transaction Enrichment

Processes transactions in parallel batches for much faster enrichment.
"""
import asyncio
from datetime import datetime
from app.core.database import SessionLocal
from app.models.models import Transaction
from app.services.cascade_enrichment import CascadeEnrichment


BATCH_SIZE = 5  # Parallel requests per batch (conservative to avoid rate limits)
DELAY_BETWEEN_BATCHES = 0.5  # seconds


async def enrich_batch(cascade: CascadeEnrichment, transactions: list, batch_num: int, total_batches: int) -> dict:
    """Enrich a batch of transactions in parallel"""
    results = {"enriched": 0, "skipped": 0, "failed": 0}

    # Create tasks for parallel execution
    tasks = [cascade.enrich_transaction(txn) for txn in transactions]

    # Execute all in parallel
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    return batch_results, transactions


async def main():
    print(f"\n{'='*60}")
    print(f"🚀 PARALLEL TRANSACTION ENRICHMENT")
    print(f"{'='*60}")
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")

    db = SessionLocal()

    # Get unenriched transactions
    unenriched = db.query(Transaction).filter(
        Transaction.enriched_merchant.is_(None),
        Transaction.enriched_category.is_(None)
    ).all()

    total = len(unenriched)
    if total == 0:
        print("\n✅ All transactions already enriched!")
        db.close()
        return

    print(f"\n📊 Found {total} unenriched transactions")
    print(f"📦 Processing in batches of {BATCH_SIZE}")
    print(f"⏱️  Estimated time: {total * 0.5 / 60:.1f} minutes\n")

    cascade = CascadeEnrichment()

    enriched_count = 0
    skipped_count = 0
    failed_count = 0

    # Process in batches
    num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, total, BATCH_SIZE):
        batch = unenriched[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        print(f"\n[{batch_num}/{num_batches}] Processing {len(batch)} transactions...")

        try:
            # Run batch in parallel
            tasks = [cascade.enrich_transaction(txn) for txn in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for txn, result in zip(batch, results):
                if isinstance(result, Exception):
                    print(f"  ❌ Error: {txn.description[:40]}... - {str(result)[:50]}")
                    failed_count += 1
                    continue

                if result.get('merchant'):
                    txn.enriched_merchant = result['merchant']
                    txn.enriched_category = result['category']
                    txn.categorization_source = result.get('source', 'cascade')
                    txn.categorization_confidence = result.get('confidence', 0.8)
                    enriched_count += 1
                    print(f"  ✅ {result['merchant'][:25]:25} | {result['category'][:15]:15} | {result['method_used']}")
                elif result.get('category') in ['internal_transfer', 'p2p_transfer']:
                    txn.enriched_category = result['category']
                    txn.categorization_source = 'skipped'
                    skipped_count += 1
                    print(f"  ⏭️  {txn.description[:40]:40} | {result['category']}")
                else:
                    failed_count += 1
                    print(f"  ❌ Failed: {txn.description[:50]}")

            # Commit after each batch
            db.commit()

            # Progress update
            processed = min(i + BATCH_SIZE, total)
            pct = processed / total * 100
            print(f"  📍 Progress: {processed}/{total} ({pct:.0f}%)")

            # Small delay to avoid rate limits
            if i + BATCH_SIZE < total:
                await asyncio.sleep(DELAY_BETWEEN_BATCHES)

        except Exception as e:
            print(f"  ❌ Batch error: {e}")
            db.rollback()

    db.close()

    # Final summary
    print(f"\n{'='*60}")
    print(f"✅ ENRICHMENT COMPLETE")
    print(f"{'='*60}")
    print(f"Finished: {datetime.now().strftime('%H:%M:%S')}")
    print(f"\n📊 Results:")
    print(f"   ✅ Enriched: {enriched_count}")
    print(f"   ⏭️  Skipped (internal): {skipped_count}")
    print(f"   ❌ Failed: {failed_count}")

    stats = cascade.get_stats()
    print(f"\n💰 Cost: ${stats['total_cost']:.2f}")
    print(f"💸 Saved vs Ntropy: ${stats['savings_amount']:.2f} ({stats['savings_percent']:.0f}%)")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
