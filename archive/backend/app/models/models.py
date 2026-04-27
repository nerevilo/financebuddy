from sqlalchemy import Column, String, Float, Date, DateTime, Boolean, ForeignKey, Text, Integer, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
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


class GoalStatus(enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class GoalPriority(enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncomeFrequency(enum.Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    IRREGULAR = "irregular"


class InsightType(enum.Enum):
    ALERT = "alert"
    OPPORTUNITY = "opportunity"
    OPTIMIZATION = "optimization"


class InsightFeedback(enum.Enum):
    HELPFUL = "helpful"
    ACTED_ON = "acted_on"
    DISMISSED = "dismissed"
    NONE = "none"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)  # Nullable for migration, then required
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Enrichment budget tracking
    enrichment_budget = Column(Float, default=1.0)  # Max $1.00 per user
    enrichment_spent = Column(Float, default=0.0)   # Amount spent so far
    enrichment_last_reset = Column(DateTime, nullable=True)  # For monthly resets if needed

    # Relationships
    institutions = relationship("Institution", back_populates="user", cascade="all, delete-orphan")


class Institution(Base):
    __tablename__ = "institutions"
    __table_args__ = (
        Index('ix_institutions_user_status', 'user_id', 'status'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    teller_enrollment_id = Column(String, unique=True, nullable=False)
    teller_access_token = Column(String, nullable=False)  # Encrypted in production
    name = Column(String, nullable=False)
    status = Column(String, default="active")  # active, disconnected, error
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="institutions")
    accounts = relationship("Account", back_populates="institution", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String, primary_key=True, default=generate_uuid)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    teller_account_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # depository, credit
    subtype = Column(String, nullable=True)  # checking, savings, credit_card
    current_balance = Column(Float, default=0.0)
    available_balance = Column(Float, nullable=True)
    currency = Column(String, default="USD")
    last_four = Column(String, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

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
    __table_args__ = (
        Index('ix_transactions_account_id_date', 'account_id', 'date'),
        Index('ix_transactions_teller_category', 'teller_category'),
        Index('ix_transactions_enriched_category', 'enriched_category'),
        Index('ix_transactions_is_transfer', 'is_transfer'),
        Index('ix_transactions_merchant_name', 'merchant_name'),
        # Partial index for unreviewed anomalies (fast lookup for anomaly widget)
        Index('ix_transactions_unreviewed_anomalies', 'is_anomaly', 'user_reviewed',
              postgresql_where='is_anomaly = true AND user_reviewed = false'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False, index=True)
    teller_transaction_id = Column(String, unique=True, nullable=False)
    date = Column(Date, nullable=False, index=True)
    amount = Column(Float, nullable=False)  # Negative for expenses, positive for income
    description = Column(String, nullable=False)
    merchant_name = Column(String, nullable=True)
    category_id = Column(String, ForeignKey("categories.id"), nullable=True, index=True)
    teller_category = Column(String, nullable=True)  # Original category from Teller
    type = Column(String, nullable=True)  # card_payment, ach, transfer, etc.
    status = Column(String, default="posted")  # posted, pending
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # ML Enrichment Fields (Ntropy API results)
    enriched_merchant = Column(String, nullable=True)  # Clean merchant name from Ntropy
    enriched_category = Column(String, nullable=True)  # Category from ML/Ntropy
    is_transfer = Column(Boolean, default=False)  # Transfer flag from detection
    categorization_source = Column(String, nullable=True, index=True)  # 'rule', 'bert', 'ntropy'
    categorization_confidence = Column(Float, nullable=True)  # Confidence score 0.0-1.0
    enriched_at = Column(DateTime, nullable=True)  # When enrichment was performed

    # Enrichment Retry Queue Fields (serverless-friendly background processing)
    enrichment_attempts = Column(Integer, default=0)  # Number of enrichment attempts
    enrichment_error = Column(Text, nullable=True)  # Last error message if failed
    enrichment_queued_at = Column(DateTime, nullable=True)  # When queued for enrichment

    # Anomaly Detection Fields (statistical analysis)
    is_anomaly = Column(Boolean, default=False, index=True)  # System-detected unusual transaction
    anomaly_score = Column(Float, nullable=True)  # Confidence score 0.0-1.0
    anomaly_reason = Column(String, nullable=True)  # z_score, iqr_outlier, category_spike, new_large_merchant

    # User Classification Fields
    is_one_time = Column(Boolean, default=False)  # User-marked one-time expense
    one_time_reason = Column(String, nullable=True)  # User's note for why it's one-time
    exclude_from_budget = Column(Boolean, default=False)  # Exclude from budget calculations
    user_reviewed = Column(Boolean, default=False)  # User has reviewed this anomaly

    # Relationships
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    tags = relationship("TransactionTag", secondary="transaction_tag_associations", back_populates="transactions")


class TransactionTag(Base):
    """
    Tags for organizing and classifying transactions.

    Supports both predefined system tags (rent, subscription, etc.)
    and custom user-created tags.
    """
    __tablename__ = "transaction_tags"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    color = Column(String, nullable=True)  # Hex color for display (e.g., "#3B82F6")
    tag_type = Column(String, default="custom")  # "predefined" or "custom"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Unique constraint: user can't have duplicate tag names
    __table_args__ = (
        Index('ix_transaction_tags_user_name', 'user_id', 'name', unique=True),
    )

    # Relationships
    user = relationship("User", backref="transaction_tags")
    transactions = relationship("Transaction", secondary="transaction_tag_associations", back_populates="tags")


class TransactionTagAssociation(Base):
    """Many-to-many join table for transactions and tags."""
    __tablename__ = "transaction_tag_associations"

    id = Column(String, primary_key=True, default=generate_uuid)
    transaction_id = Column(String, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = Column(String, ForeignKey("transaction_tags.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('ix_transaction_tag_assoc_unique', 'transaction_id', 'tag_id', unique=True),
    )


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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="transfer_rules")


class MerchantCategoryRule(Base):
    """
    User-defined rules for automatic category assignment by merchant name.
    Created when user changes a transaction's category and opts to apply to all similar.
    """
    __tablename__ = "merchant_category_rules"
    __table_args__ = (
        Index('ix_merchant_category_rules_user_merchant', 'user_id', 'merchant_name', unique=True),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    merchant_name = Column(String, nullable=False)  # Exact match on merchant_name field
    category = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    times_applied = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="merchant_category_rules")


class UserProfile(Base):
    """Extended user profile with financial context for LLM personalization."""
    __tablename__ = "user_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)

    # Income context
    monthly_income_estimate = Column(Float, nullable=True)
    income_last_calculated = Column(DateTime, nullable=True)

    # Household context
    household_size = Column(Integer, default=1)
    location_city = Column(String, nullable=True)
    location_state = Column(String, nullable=True)

    # User-provided context for LLM
    context_notes = Column(Text, nullable=True)  # e.g., "Student", "Saving for wedding"

    # Preferences
    insight_frequency = Column(String, default="daily")  # daily, weekly
    preferred_categories = Column(Text, nullable=True)  # JSON array of focus categories

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="profile")


class IncomeSource(Base):
    """Detected or manually entered income sources."""
    __tablename__ = "income_sources"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String, nullable=False)  # e.g., "Employer Paycheck", "Freelance Client"
    amount = Column(Float, nullable=False)
    frequency = Column(String, nullable=False)  # weekly, biweekly, monthly, yearly, irregular

    # Detection metadata
    auto_detected = Column(Boolean, default=False)
    detection_pattern = Column(String, nullable=True)  # Matched transaction description pattern
    last_transaction_id = Column(String, ForeignKey("transactions.id"), nullable=True)

    # Scheduling
    next_expected_date = Column(Date, nullable=True)
    last_received_date = Column(Date, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="income_sources")


class Goal(Base):
    """Financial goals with progress tracking."""
    __tablename__ = "goals"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String, nullable=False)  # e.g., "Emergency Fund", "Vacation to Hawaii"
    description = Column(Text, nullable=True)

    # Financial targets
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    monthly_allocation = Column(Float, nullable=True)  # Suggested monthly savings

    # Timeline
    deadline = Column(Date, nullable=True)

    # Priority & Status
    priority = Column(String, default="medium")  # high, medium, low
    status = Column(String, default="active")  # active, completed, paused, cancelled

    # Suggestion metadata
    auto_suggested = Column(Boolean, default=False)
    suggestion_reason = Column(Text, nullable=True)  # Why this goal was suggested
    related_category = Column(String, nullable=True)  # Category that triggered suggestion

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="goals")


class Insight(Base):
    """LLM-generated daily insights with user feedback."""
    __tablename__ = "insights"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Insight content
    type = Column(String, nullable=False)  # alert, opportunity, optimization
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    action = Column(Text, nullable=True)  # Suggested action to take

    # Context
    category = Column(String, nullable=True)  # Related spending category
    amount_referenced = Column(Float, nullable=True)  # Dollar amount mentioned
    comparison_period = Column(String, nullable=True)  # e.g., "vs last month"

    # Priority for display
    priority_score = Column(Float, default=0.5)  # 0.0-1.0, for ranking
    emoji = Column(String, nullable=True)  # Visual indicator

    # User feedback
    feedback = Column(String, default="none")  # helpful, acted_on, dismissed, none
    feedback_at = Column(DateTime, nullable=True)

    # Generation metadata
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    llm_source = Column(String, nullable=True)  # gemini_flash, claude_haiku
    generation_cost = Column(Float, default=0.0)  # Track costs
    prompt_version = Column(String, nullable=True)  # For A/B testing prompts

    # Validity
    expires_at = Column(DateTime, nullable=True)  # When insight becomes stale
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="insights")


class Conversation(Base):
    """Chat conversation sessions for the AI assistant."""
    __tablename__ = "conversations"
    __table_args__ = (
        Index('ix_conversations_user_updated', 'user_id', 'updated_at'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=True)  # Auto-generated from first message
    status = Column(String, default="active")  # active, archived
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_message_at = Column(DateTime, nullable=True)
    message_count = Column(Integer, default=0)

    # Metadata for analytics
    tool_calls_count = Column(Integer, default=0)
    llm_provider = Column(String, nullable=True)  # claude, gemini
    total_tokens = Column(Integer, default=0)

    # Relationships
    user = relationship("User", backref="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )


class Message(Base):
    """Individual chat messages within a conversation."""
    __tablename__ = "messages"
    __table_args__ = (
        Index('ix_messages_conversation_created', 'conversation_id', 'created_at'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)  # user, assistant, tool, system
    content = Column(Text, nullable=False)

    # Tool call metadata (for assistant messages that invoke tools)
    tool_calls = Column(Text, nullable=True)  # JSON array of tool calls
    tool_call_id = Column(String, nullable=True)  # For tool response messages
    tool_name = Column(String, nullable=True)  # Which tool was called

    # Token tracking
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
