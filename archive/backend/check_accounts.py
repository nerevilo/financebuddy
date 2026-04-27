"""
Check bank accounts and institutions in database
"""
from app.core.database import SessionLocal
from app.models.models import Account, Institution, Transaction

db = SessionLocal()

# Check institutions
institutions = db.query(Institution).all()
print(f'Institutions connected: {len(institutions)}')
for inst in institutions:
    print(f'  - {inst.name} (ID: {inst.id})')
print()

# Check accounts
accounts = db.query(Account).all()
print(f'Bank accounts: {len(accounts)}')
for acc in accounts:
    print(f'  - {acc.name} ({acc.type}) - Institution: {acc.institution_id}')
    print(f'    Balance: ${acc.balance:.2f}')
    print(f'    Teller ID: {acc.teller_account_id}')

    # Check transactions for this account
    txn_count = db.query(Transaction).filter(Transaction.account_id == acc.id).count()
    print(f'    Transactions: {txn_count}')
    print()

# Total transactions
total_txns = db.query(Transaction).count()
print(f'\nTotal transactions across all accounts: {total_txns}')

if len(accounts) > 0 and total_txns == 0:
    print('\n⚠️  You have accounts connected but NO transactions!')
    print('This means you need to sync/fetch transactions from Teller.')
    print('\nNext step: Fetch transactions from Teller API')

db.close()
