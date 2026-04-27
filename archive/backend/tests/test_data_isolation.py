"""Tests that user A cannot access user B's data through any endpoint."""
from datetime import date
from tests.conftest import auth_headers
from app.models import Institution, Account, Transaction
from app.models.models import generate_uuid


def _seed_institution(db, user_id: str, name: str = "Test Bank") -> Institution:
    inst = Institution(
        id=generate_uuid(),
        user_id=user_id,
        teller_enrollment_id=generate_uuid(),
        teller_access_token="enc_fake_token",
        name=name,
        status="active",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def _seed_account(db, institution_id: str, name: str = "Checking") -> Account:
    acct = Account(
        id=generate_uuid(),
        institution_id=institution_id,
        teller_account_id=generate_uuid(),
        name=name,
        type="depository",
        subtype="checking",
        current_balance=1000.0,
    )
    db.add(acct)
    db.commit()
    db.refresh(acct)
    return acct


def _seed_transaction(db, account_id: str, amount: float = -50.0, desc: str = "Coffee") -> Transaction:
    txn = Transaction(
        id=generate_uuid(),
        account_id=account_id,
        teller_transaction_id=generate_uuid(),
        date=date.today(),
        amount=amount,
        description=desc,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


class TestInstitutionIsolation:
    def test_user_a_cannot_see_user_b_institutions(self, client, db_session, user_a, user_b):
        _seed_institution(db_session, user_a.id, "Alice Bank")
        _seed_institution(db_session, user_b.id, "Bob Bank")

        resp = client.get("/institutions/", headers=auth_headers(user_a))
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()]
        assert "Alice Bank" in names
        assert "Bob Bank" not in names

    def test_user_b_cannot_see_user_a_institutions(self, client, db_session, user_a, user_b):
        _seed_institution(db_session, user_a.id, "Alice Bank")
        _seed_institution(db_session, user_b.id, "Bob Bank")

        resp = client.get("/institutions/", headers=auth_headers(user_b))
        names = [i["name"] for i in resp.json()]
        assert "Bob Bank" in names
        assert "Alice Bank" not in names


class TestTransactionIsolation:
    def test_user_a_cannot_see_user_b_transactions(self, client, db_session, user_a, user_b):
        inst_a = _seed_institution(db_session, user_a.id)
        acct_a = _seed_account(db_session, inst_a.id, "Alice Checking")
        _seed_transaction(db_session, acct_a.id, -100.0, "Alice Groceries")

        inst_b = _seed_institution(db_session, user_b.id)
        acct_b = _seed_account(db_session, inst_b.id, "Bob Checking")
        _seed_transaction(db_session, acct_b.id, -200.0, "Bob Dining")

        # User A should see only their transactions
        resp = client.get("/transactions/", headers=auth_headers(user_a))
        assert resp.status_code == 200
        descriptions = [t["description"] for t in resp.json()]
        assert "Alice Groceries" in descriptions
        assert "Bob Dining" not in descriptions

    def test_user_b_cannot_see_user_a_transactions(self, client, db_session, user_a, user_b):
        inst_a = _seed_institution(db_session, user_a.id)
        acct_a = _seed_account(db_session, inst_a.id)
        _seed_transaction(db_session, acct_a.id, -100.0, "Alice Private")

        inst_b = _seed_institution(db_session, user_b.id)
        acct_b = _seed_account(db_session, inst_b.id)
        _seed_transaction(db_session, acct_b.id, -50.0, "Bob Public")

        resp = client.get("/transactions/", headers=auth_headers(user_b))
        assert resp.status_code == 200
        descriptions = [t["description"] for t in resp.json()]
        assert "Bob Public" in descriptions
        assert "Alice Private" not in descriptions


class TestAccountIsolation:
    def test_user_a_cannot_see_user_b_accounts(self, client, db_session, user_a, user_b):
        inst_a = _seed_institution(db_session, user_a.id)
        _seed_account(db_session, inst_a.id, "Alice Savings")

        inst_b = _seed_institution(db_session, user_b.id)
        _seed_account(db_session, inst_b.id, "Bob Credit")

        resp = client.get("/accounts/", headers=auth_headers(user_a))
        assert resp.status_code == 200
        names = [a["name"] for a in resp.json()]
        assert "Alice Savings" in names
        assert "Bob Credit" not in names


class TestUnauthenticatedAccess:
    def test_institutions_requires_auth(self, client):
        resp = client.get("/institutions/")
        assert resp.status_code == 401

    def test_transactions_requires_auth(self, client):
        resp = client.get("/transactions/")
        assert resp.status_code == 401

    def test_accounts_requires_auth(self, client):
        resp = client.get("/accounts/")
        assert resp.status_code == 401

    def test_dashboard_requires_auth(self, client):
        resp = client.get("/api/dashboard/stats")
        assert resp.status_code == 401
