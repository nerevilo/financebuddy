from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


# ==================== User Schemas ====================

class UserCreate(BaseModel):
    email: str
    name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
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
