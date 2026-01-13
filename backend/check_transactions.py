"""
Check what transactions we have in the database
"""
from app.core.database import SessionLocal
from app.models.models import Transaction

db = SessionLocal()

# Count total transactions
count = db.query(Transaction).count()
print(f'Total transactions in database: {count}')

if count > 0:
    print('\nFirst 10 transactions:')
    print('-' * 80)
    txns = db.query(Transaction).limit(10).all()
    for i, txn in enumerate(txns, 1):
        enriched = "✅ Yes" if txn.enriched_merchant else "❌ No"
        print(f'{i}. ID: {txn.id}')
        print(f'   Description: {txn.description}')
        print(f'   Amount: ${abs(txn.amount):.2f}')
        print(f'   Enriched: {enriched}')
        if txn.enriched_merchant:
            print(f'   Merchant: {txn.enriched_merchant}')
            print(f'   Category: {txn.enriched_category}')
        print()
else:
    print('\n❌ No transactions found.')
    print('You need to connect your bank account first via Teller API.')
    print('\nTo add transactions:')
    print('1. Use the frontend to connect your bank')
    print('2. OR use the Teller API directly')
    print('3. Then run this enrichment!')

db.close()
