from sqlalchemy import Column, String, Float, Date, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from ..core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class AccountType(enum.Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT = "credit"
    OTHER = "other"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    institutions = relationship("Institution", back_populates="user", cascade="all, delete-orphan")


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    teller_enrollment_id = Column(String, unique=True, nullable=False)
    teller_access_token = Column(String, nullable=False)  # Encrypted in production
    name = Column(String, nullable=False)
    status = Column(String, default="active")  # active, disconnected, error
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="institutions")
    accounts = relationship("Account", back_populates="institution", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String, primary_key=True, default=generate_uuid)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False)
    teller_account_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # depository, credit
    subtype = Column(String, nullable=True)  # checking, savings, credit_card
    current_balance = Column(Float, default=0.0)
    available_balance = Column(Float, nullable=True)
    currency = Column(String, default="USD")
    last_four = Column(String, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    institution = relationship("Institution", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)
    icon = Column(String, nullable=True)
    color = Column(String, nullable=True)
    is_system = Column(Boolean, default=True)

    # Relationships
    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=generate_uuid)
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    teller_transaction_id = Column(String, unique=True, nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)  # Negative for expenses, positive for income
    description = Column(String, nullable=False)
    merchant_name = Column(String, nullable=True)
    category_id = Column(String, ForeignKey("categories.id"), nullable=True)
    teller_category = Column(String, nullable=True)  # Original category from Teller
    type = Column(String, nullable=True)  # card_payment, ach, transfer, etc.
    status = Column(String, default="posted")  # posted, pending
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")


class TransferRule(Base):
    """
    User-configurable rules for transfer detection.

    Allows users to add custom keywords or patterns without code changes.
    Will be used alongside default rules and ML-based detection.
    """
    __tablename__ = "transfer_rules"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # None = global rule
    rule_type = Column(String, nullable=False)  # "internal_transfer", "payment", "exclude"
    pattern = Column(String, nullable=False)  # Keyword or regex pattern
    is_regex = Column(Boolean, default=False)
    priority = Column(Float, default=0.0)  # Higher priority rules checked first
    description = Column(Text, nullable=True)  # Why this rule exists
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="transfer_rules")
