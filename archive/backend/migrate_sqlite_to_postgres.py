"""
Migrate data from SQLite to PostgreSQL (Supabase)
"""
import sqlite3
from sqlalchemy import create_engine, text
from app.core.config import get_settings


def migrate_data():
    """Migrate all data from SQLite to PostgreSQL"""

    print("\n" + "="*80)
    print("🔄 MIGRATING DATA: SQLite → PostgreSQL (Supabase)")
    print("="*80)

    # Get database URLs
    settings = get_settings()
    postgres_url = settings.database_url

    print(f"\n📦 Source: SQLite (fintrack.db)")
    print(f"📦 Destination: PostgreSQL (Supabase)")
    print(f"   {postgres_url[:50]}...\n")

    # Connect to both databases
    sqlite_conn = sqlite3.connect('fintrack.db')
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    postgres_engine = create_engine(postgres_url)

    print("✅ Connected to both databases\n")
    print("-"*80)

    # Count records in SQLite
    sqlite_cursor.execute("SELECT COUNT(*) FROM institutions")
    inst_count = sqlite_cursor.fetchone()[0]

    sqlite_cursor.execute("SELECT COUNT(*) FROM accounts")
    acc_count = sqlite_cursor.fetchone()[0]

    sqlite_cursor.execute("SELECT COUNT(*) FROM transactions")
    txn_count = sqlite_cursor.fetchone()[0]

    sqlite_cursor.execute("SELECT COUNT(*) FROM transactions WHERE enriched_merchant IS NOT NULL")
    enriched_count = sqlite_cursor.fetchone()[0]

    print(f"📊 SQLite Data:")
    print(f"   Institutions: {inst_count}")
    print(f"   Accounts: {acc_count}")
    print(f"   Transactions: {txn_count}")
    print(f"   Enriched: {enriched_count}")
    print()

    # Check PostgreSQL
    with postgres_engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM transactions"))
        pg_txn_count = result.scalar()

        if pg_txn_count > 0:
            print(f"⚠️  WARNING: PostgreSQL already has {pg_txn_count} transactions!")
            response = input("   Clear existing data and migrate? (yes/no): ")
            if response.lower() != 'yes':
                print("\n❌ Migration cancelled")
                return

            # Clear existing data
            print("\n🗑️  Clearing PostgreSQL data...")
            conn.execute(text("DELETE FROM transactions"))
            conn.execute(text("DELETE FROM accounts"))
            conn.execute(text("DELETE FROM institutions"))
            conn.commit()
            print("   ✅ Cleared")

    print("\n🚀 Starting migration...\n")

    # Migrate Users first (institutions reference users)
    print("0️⃣  Migrating users...")
    sqlite_cursor.execute("SELECT * FROM users")
    users = sqlite_cursor.fetchall()

    if users:
        with postgres_engine.connect() as conn:
            for user in users:
                conn.execute(text("""
                    INSERT INTO users (id, email, name, created_at)
                    VALUES (:id, :email, :name, :created_at)
                    ON CONFLICT (id) DO NOTHING
                """), {
                    'id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'created_at': user['created_at']
                })
            conn.commit()
        print(f"   ✅ Migrated {len(users)} users")
    else:
        print(f"   ⚠️  No users found")

    # Migrate Institutions
    print("1️⃣  Migrating institutions...")
    sqlite_cursor.execute("SELECT * FROM institutions")
    institutions = sqlite_cursor.fetchall()

    with postgres_engine.connect() as conn:
        for inst in institutions:
            conn.execute(text("""
                INSERT INTO institutions (
                    id, user_id, teller_enrollment_id, teller_access_token,
                    name, status, last_synced_at, created_at
                )
                VALUES (
                    :id, :user_id, :teller_enrollment_id, :teller_access_token,
                    :name, :status, :last_synced_at, :created_at
                )
                ON CONFLICT (id) DO NOTHING
            """), {
                'id': inst['id'],
                'user_id': inst['user_id'],
                'teller_enrollment_id': inst['teller_enrollment_id'],
                'teller_access_token': inst['teller_access_token'],
                'name': inst['name'],
                'status': inst['status'],
                'last_synced_at': inst['last_synced_at'],
                'created_at': inst['created_at']
            })
        conn.commit()

    print(f"   ✅ Migrated {len(institutions)} institutions")

    # Migrate Accounts
    print("\n2️⃣  Migrating accounts...")
    sqlite_cursor.execute("SELECT * FROM accounts")
    accounts = sqlite_cursor.fetchall()

    with postgres_engine.connect() as conn:
        for acc in accounts:
            conn.execute(text("""
                INSERT INTO accounts (
                    id, institution_id, teller_account_id, name, type, subtype,
                    current_balance, available_balance, currency, last_four,
                    last_synced_at, created_at
                )
                VALUES (
                    :id, :institution_id, :teller_account_id, :name, :type, :subtype,
                    :current_balance, :available_balance, :currency, :last_four,
                    :last_synced_at, :created_at
                )
                ON CONFLICT (id) DO NOTHING
            """), {
                'id': acc['id'],
                'institution_id': acc['institution_id'],
                'teller_account_id': acc['teller_account_id'],
                'name': acc['name'],
                'type': acc['type'],
                'subtype': acc['subtype'],
                'current_balance': acc['current_balance'],
                'available_balance': acc['available_balance'],
                'currency': acc['currency'],
                'last_four': acc['last_four'],
                'last_synced_at': acc['last_synced_at'],
                'created_at': acc['created_at']
            })
        conn.commit()

    print(f"   ✅ Migrated {len(accounts)} accounts")

    # Migrate Transactions (with enrichment data!)
    print("\n3️⃣  Migrating transactions (including enrichment data)...")
    sqlite_cursor.execute("SELECT * FROM transactions")
    transactions = sqlite_cursor.fetchall()

    migrated = 0
    with postgres_engine.connect() as conn:
        for i, txn in enumerate(transactions, 1):
            conn.execute(text("""
                INSERT INTO transactions (
                    id, account_id, teller_transaction_id, date, amount, description,
                    merchant_name, category_id, teller_category, type, status,
                    enriched_merchant, enriched_category, is_transfer,
                    categorization_source, categorization_confidence,
                    enriched_at, created_at
                )
                VALUES (
                    :id, :account_id, :teller_transaction_id, :date, :amount, :description,
                    :merchant_name, :category_id, :teller_category, :type, :status,
                    :enriched_merchant, :enriched_category, :is_transfer,
                    :categorization_source, :categorization_confidence,
                    :enriched_at, :created_at
                )
                ON CONFLICT (id) DO NOTHING
            """), {
                'id': txn['id'],
                'account_id': txn['account_id'],
                'teller_transaction_id': txn['teller_transaction_id'],
                'date': txn['date'],
                'amount': txn['amount'],
                'description': txn['description'],
                'merchant_name': txn['merchant_name'],
                'category_id': txn['category_id'],
                'teller_category': txn['teller_category'],
                'type': txn['type'],
                'status': txn['status'],
                'enriched_merchant': txn['enriched_merchant'],
                'enriched_category': txn['enriched_category'],
                'is_transfer': txn['is_transfer'],
                'categorization_source': txn['categorization_source'],
                'categorization_confidence': txn['categorization_confidence'],
                'enriched_at': txn['enriched_at'],
                'created_at': txn['created_at']
            })

            if i % 100 == 0:
                conn.commit()
                print(f"   ... {i}/{len(transactions)}")
                migrated = i

        conn.commit()

    print(f"   ✅ Migrated {len(transactions)} transactions")

    # Verify migration
    print("\n" + "-"*80)
    print("🔍 VERIFYING MIGRATION...")
    print("-"*80)

    with postgres_engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM institutions"))
        pg_inst_count = result.scalar()

        result = conn.execute(text("SELECT COUNT(*) FROM accounts"))
        pg_acc_count = result.scalar()

        result = conn.execute(text("SELECT COUNT(*) FROM transactions"))
        pg_txn_count = result.scalar()

        result = conn.execute(text(
            "SELECT COUNT(*) FROM transactions WHERE enriched_merchant IS NOT NULL"
        ))
        pg_enriched_count = result.scalar()

    print(f"\n📊 PostgreSQL Data (after migration):")
    print(f"   Institutions: {pg_inst_count}/{inst_count}")
    print(f"   Accounts: {pg_acc_count}/{acc_count}")
    print(f"   Transactions: {pg_txn_count}/{txn_count}")
    print(f"   Enriched: {pg_enriched_count}/{enriched_count}")

    # Check if all data migrated
    if (pg_inst_count == inst_count and
        pg_acc_count == acc_count and
        pg_txn_count == txn_count and
        pg_enriched_count == enriched_count):
        print("\n✅ MIGRATION SUCCESSFUL! All data migrated correctly.")
        print("\n🎉 You can now delete fintrack.db (SQLite) if you want.")
        print("   All data is now in PostgreSQL (Supabase)!")
    else:
        print("\n⚠️  WARNING: Some data may not have migrated correctly!")
        print("   Please check the counts above.")

    # Close connections
    sqlite_conn.close()

    print("\n" + "="*80)
    print("✅ MIGRATION COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    migrate_data()
