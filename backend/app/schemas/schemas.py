from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


# ==================== Auth Schemas ====================

class UserRegister(BaseModel):
    """Request body for user registration."""
    email: str
    password: str
    name: Optional[str] = None


class UserLogin(BaseModel):
    """Request body for user login."""
    email: str
    password: str


class TokenRefresh(BaseModel):
    """Request body for token refresh."""
    refresh_token: str


class TokenResponse(BaseModel):
    """Response containing access and refresh tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


# ==================== User Schemas ====================

class UserCreate(BaseModel):
    email: str
    name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Institution Schemas ====================

class TellerConnectPayload(BaseModel):
    """Payload received from Teller Connect onSuccess callback."""
    accessToken: str
    enrollment: dict
    user: dict


class InstitutionCreate(BaseModel):
    teller_enrollment_id: str
    teller_access_token: str
    name: str


class InstitutionResponse(BaseModel):
    id: str
    name: str
    status: str
    last_synced_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Account Schemas ====================

class AccountResponse(BaseModel):
    id: str
    teller_account_id: str
    name: str
    type: str
    subtype: Optional[str]
    current_balance: float
    available_balance: Optional[float]
    currency: str
    last_four: Optional[str]
    institution_name: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== Transaction Schemas ====================

class TransactionResponse(BaseModel):
    id: str
    account_id: str
    date: date
    amount: float
    description: str
    merchant_name: Optional[str]
    category: Optional[str]
    type: Optional[str]
    status: str

    class Config:
        from_attributes = True


# ==================== Analytics Schemas ====================

class SpendingByCategory(BaseModel):
    category: str
    total: float
    count: int
    percentage: float


class SpendingByMerchant(BaseModel):
    merchant: str
    total: float
    count: int
    percentage: float


class SpendingTrend(BaseModel):
    period: str  # e.g., "2024-01" for month
    total: float
    income: float
    expenses: float


class PeriodComparison(BaseModel):
    current_period: str
    previous_period: str
    current_total: float
    previous_total: float
    change_amount: float
    change_percentage: float


# ==================== Category Schemas ====================

class CategoryResponse(BaseModel):
    name: str
    transaction_count: Optional[int] = None

    class Config:
        from_attributes = True


class TransactionCategoryUpdate(BaseModel):
    category: str


# ==================== Paginated Transaction Schemas ====================

class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


# ==================== User Profile Schemas ====================

class UserProfileCreate(BaseModel):
    household_size: Optional[int] = 1
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    context_notes: Optional[str] = None
    insight_frequency: Optional[str] = "daily"


class UserProfileUpdate(BaseModel):
    household_size: Optional[int] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    context_notes: Optional[str] = None
    insight_frequency: Optional[str] = None
    preferred_categories: Optional[List[str]] = None


class UserProfileResponse(BaseModel):
    id: str
    user_id: str
    monthly_income_estimate: Optional[float]
    income_last_calculated: Optional[datetime]
    household_size: int
    location_city: Optional[str]
    location_state: Optional[str]
    context_notes: Optional[str]
    insight_frequency: str
    preferred_categories: Optional[List[str]] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ==================== Income Source Schemas ====================

class IncomeSourceCreate(BaseModel):
    name: str
    amount: float
    frequency: str  # weekly, biweekly, monthly, yearly, irregular
    next_expected_date: Optional[date] = None


class IncomeSourceUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    frequency: Optional[str] = None
    next_expected_date: Optional[date] = None
    is_active: Optional[bool] = None


class IncomeSourceResponse(BaseModel):
    id: str
    user_id: str
    name: str
    amount: float
    frequency: str
    auto_detected: bool
    detection_pattern: Optional[str]
    next_expected_date: Optional[date]
    last_received_date: Optional[date]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class IncomeSummary(BaseModel):
    total_monthly_income: float
    income_sources: List[IncomeSourceResponse]
    auto_detected_count: int
    manual_count: int


class DetectedIncome(BaseModel):
    name: str
    amount: float
    frequency: str
    occurrences: int
    pattern: str
    last_date: date
    confidence: float
    last_transaction_id: Optional[str]


# ==================== Goal Schemas ====================

class GoalCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_amount: float
    current_amount: Optional[float] = 0.0
    monthly_allocation: Optional[float] = None
    deadline: Optional[date] = None
    priority: Optional[str] = "medium"


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_amount: Optional[float] = None
    current_amount: Optional[float] = None
    monthly_allocation: Optional[float] = None
    deadline: Optional[date] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class GoalResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    target_amount: float
    current_amount: float
    monthly_allocation: Optional[float]
    deadline: Optional[date]
    priority: str
    status: str
    auto_suggested: bool
    suggestion_reason: Optional[str]
    related_category: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    # Computed fields
    progress_percentage: Optional[float] = None
    months_to_goal: Optional[int] = None
    on_track: Optional[bool] = None

    class Config:
        from_attributes = True


class GoalSuggestion(BaseModel):
    name: str
    target_amount: float
    monthly_allocation: float
    reason: str
    related_category: Optional[str]
    priority: str


# ==================== Insight Schemas ====================

class InsightFeedbackUpdate(BaseModel):
    feedback: str  # helpful, acted_on, dismissed


class InsightResponse(BaseModel):
    id: str
    type: str  # alert, opportunity, optimization
    title: str
    description: str
    action: Optional[str]
    category: Optional[str]
    amount_referenced: Optional[float]
    comparison_period: Optional[str]
    priority_score: float
    emoji: Optional[str]
    feedback: str
    feedback_at: Optional[datetime]
    generated_at: datetime
    is_read: bool
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class DailyInsightsResponse(BaseModel):
    date: date
    insights: List[InsightResponse]
    generation_source: str
    total_cost: float


class InsightHistory(BaseModel):
    insights: List[InsightResponse]
    total: int
    helpful_count: int
    acted_on_count: int
    dismissed_count: int


# ==================== Anomaly Detection Schemas ====================

class AnomalyResponse(BaseModel):
    """A detected unusual transaction."""
    id: str
    amount: float
    merchant: Optional[str]
    category: Optional[str]
    date: Optional[date]
    anomaly_score: float
    anomaly_reason: str
    description: str
    is_one_time: bool = False
    user_reviewed: bool = False


class UnusualTransactionsResponse(BaseModel):
    """Response containing unusual transactions for review."""
    transactions: List[AnomalyResponse]
    total_unreviewed: int
    last_scan: str


class MarkOneTimeRequest(BaseModel):
    """Request to mark a transaction as one-time expense."""
    reason: Optional[str] = None
    exclude_from_budget: bool = True


class OneTimeExpenseResponse(BaseModel):
    """A transaction marked as one-time expense."""
    id: str
    amount: float
    merchant: Optional[str]
    category: Optional[str]
    date: Optional[date]
    one_time_reason: Optional[str]
    exclude_from_budget: bool


class OneTimeExpensesListResponse(BaseModel):
    """Response containing all one-time expenses."""
    expenses: List[OneTimeExpenseResponse]
    total: int
    total_amount: float


class AnomalySummary(BaseModel):
    """Summary of anomaly detection status for dashboard."""
    unreviewed_count: int
    one_time_count: int
    one_time_total: float
    top_unreviewed: List[AnomalyResponse]
