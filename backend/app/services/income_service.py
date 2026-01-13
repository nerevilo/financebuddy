"""
Income Detection and Management Service

Auto-detects recurring deposits and manages income sources.
"""
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Dict, List, Optional
from collections import defaultdict
import re

from ..models import Transaction, Account, IncomeSource
from ..models.models import generate_uuid


class IncomeService:
    """Service for income detection and management."""

    # Patterns for income detection
    INCOME_PATTERNS = [
        r"payroll",
        r"direct\s*dep(osit)?",
        r"salary",
        r"employer",
        r"ach\s*credit",
        r"paycheck",
        r"wages",
    ]

    # Patterns to exclude (not income)
    EXCLUDE_PATTERNS = [
        r"refund",
        r"return",
        r"cashback",
        r"interest",
        r"rebate",
        r"transfer\s*from",
        r"zelle",
        r"venmo",
    ]

    def __init__(self, db: Session):
        self.db = db

    def detect_income_sources(self, user_id: str) -> List[Dict]:
        """
        Analyze transactions to detect recurring income deposits.

        Returns list of detected income sources with confidence scores.
        """
        # Get positive deposits from last 90 days
        ninety_days_ago = datetime.now() - timedelta(days=90)

        deposits = self.db.query(Transaction).join(Account).filter(
            and_(
                Transaction.amount > 0,  # Positive = deposit
                Transaction.date >= ninety_days_ago,
                Account.type == 'depository'  # Bank accounts only
            )
        ).order_by(Transaction.date.desc()).all()

        # Group by similar descriptions and amounts
        deposit_groups = self._group_similar_deposits(deposits)

        detected_sources = []
        for pattern, group in deposit_groups.items():
            if len(group) >= 2:  # At least 2 occurrences
                # Check if matches income patterns
                if self._is_likely_income(pattern):
                    frequency = self._detect_frequency(group)
                    avg_amount = sum(d.amount for d in group) / len(group)

                    detected_sources.append({
                        'name': self._clean_income_name(pattern),
                        'amount': round(avg_amount, 2),
                        'frequency': frequency,
                        'occurrences': len(group),
                        'pattern': pattern,
                        'last_date': max(d.date for d in group),
                        'confidence': self._calculate_confidence(group, frequency),
                        'last_transaction_id': group[0].id
                    })

        return sorted(detected_sources, key=lambda x: x['amount'], reverse=True)

    def _group_similar_deposits(self, deposits: List[Transaction]) -> Dict:
        """Group deposits by similar description and amount (within 5%)."""
        groups = defaultdict(list)

        for deposit in deposits:
            # Normalize description
            desc = deposit.description.upper()
            desc = re.sub(r'\d{4,}', 'XXXX', desc)  # Mask long numbers
            desc = re.sub(r'\s+', ' ', desc).strip()

            # Find existing group with similar amount
            matched = False
            for key, group in groups.items():
                if group:
                    avg_amount = sum(d.amount for d in group) / len(group)
                    if avg_amount > 0 and abs(deposit.amount - avg_amount) / avg_amount < 0.05:  # Within 5%
                        if self._similar_description(desc, key):
                            groups[key].append(deposit)
                            matched = True
                            break

            if not matched:
                groups[desc].append(deposit)

        return groups

    def _similar_description(self, desc1: str, desc2: str) -> bool:
        """Check if two descriptions are similar enough."""
        words1 = set(desc1.split())
        words2 = set(desc2.split())
        overlap = len(words1 & words2)
        total = len(words1 | words2)
        return overlap / total > 0.5 if total > 0 else False

    def _is_likely_income(self, pattern: str) -> bool:
        """Check if pattern looks like income."""
        pattern_lower = pattern.lower()

        # Check exclusions first
        for exclude in self.EXCLUDE_PATTERNS:
            if re.search(exclude, pattern_lower):
                return False

        # Check income patterns
        for income in self.INCOME_PATTERNS:
            if re.search(income, pattern_lower):
                return True

        # Also accept large recurring deposits even without keyword match
        return False

    def _detect_frequency(self, deposits: List[Transaction]) -> str:
        """Detect payment frequency from deposit dates."""
        if len(deposits) < 2:
            return "irregular"

        dates = sorted([d.date for d in deposits])
        gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        avg_gap = sum(gaps) / len(gaps)

        if 5 <= avg_gap <= 9:
            return "weekly"
        elif 12 <= avg_gap <= 16:
            return "biweekly"
        elif 26 <= avg_gap <= 34:
            return "monthly"
        else:
            return "irregular"

    def _calculate_confidence(self, deposits: List[Transaction], frequency: str) -> float:
        """Calculate confidence score for income detection."""
        base_confidence = 0.5

        # More occurrences = higher confidence
        occurrence_bonus = min(len(deposits) * 0.1, 0.3)

        # Regular frequency = higher confidence
        frequency_bonus = 0.2 if frequency != "irregular" else 0.0

        return min(base_confidence + occurrence_bonus + frequency_bonus, 0.95)

    def _clean_income_name(self, pattern: str) -> str:
        """Clean up pattern into readable income source name."""
        name = pattern
        name = re.sub(r'ACH\s*(CREDIT|DEPOSIT)?', '', name, flags=re.IGNORECASE)
        name = re.sub(r'DIRECT\s*DEP(OSIT)?', '', name, flags=re.IGNORECASE)
        name = re.sub(r'XXXX', '', name)
        name = re.sub(r'\s+', ' ', name).strip()

        return name.title() if name else "Unknown Employer"

    def save_detected_income(self, user_id: str, detected: Dict) -> IncomeSource:
        """Save a detected income source to the database."""
        source = IncomeSource(
            id=generate_uuid(),
            user_id=user_id,
            name=detected['name'],
            amount=detected['amount'],
            frequency=detected['frequency'],
            auto_detected=True,
            detection_pattern=detected['pattern'],
            last_transaction_id=detected.get('last_transaction_id'),
            last_received_date=detected.get('last_date'),
            next_expected_date=self._calculate_next_expected(
                detected.get('last_date'), detected['frequency']
            )
        )

        self.db.add(source)
        self.db.commit()
        return source

    def _calculate_next_expected(self, last_date: date, frequency: str) -> Optional[date]:
        """Calculate next expected income date."""
        if not last_date:
            return None

        days_map = {
            'weekly': 7,
            'biweekly': 14,
            'monthly': 30,
            'yearly': 365,
        }

        days = days_map.get(frequency)
        if days:
            return last_date + timedelta(days=days)
        return None

    def calculate_monthly_income(self, user_id: str) -> float:
        """Calculate total monthly income from all active sources."""
        sources = self.db.query(IncomeSource).filter(
            and_(
                IncomeSource.user_id == user_id,
                IncomeSource.is_active == True
            )
        ).all()

        total = 0.0
        for source in sources:
            if source.frequency == 'weekly':
                total += source.amount * 4.33
            elif source.frequency == 'biweekly':
                total += source.amount * 2.17
            elif source.frequency == 'monthly':
                total += source.amount
            elif source.frequency == 'yearly':
                total += source.amount / 12
            else:  # irregular - use as-is assuming monthly
                total += source.amount

        return round(total, 2)

    # CRUD Operations

    def create_income_source(self, user_id: str, data: Dict) -> IncomeSource:
        """Create a manual income source."""
        source = IncomeSource(
            id=generate_uuid(),
            user_id=user_id,
            name=data['name'],
            amount=data['amount'],
            frequency=data['frequency'],
            auto_detected=False,
            next_expected_date=data.get('next_expected_date')
        )
        self.db.add(source)
        self.db.commit()
        return source

    def get_income_sources(self, user_id: str) -> List[IncomeSource]:
        """Get all income sources for a user."""
        return self.db.query(IncomeSource).filter(
            IncomeSource.user_id == user_id
        ).order_by(IncomeSource.amount.desc()).all()

    def update_income_source(self, source_id: str, data: Dict) -> Optional[IncomeSource]:
        """Update an income source."""
        source = self.db.query(IncomeSource).filter(
            IncomeSource.id == source_id
        ).first()

        if not source:
            return None

        for key, value in data.items():
            if value is not None and hasattr(source, key):
                setattr(source, key, value)

        source.updated_at = datetime.utcnow()
        self.db.commit()
        return source

    def delete_income_source(self, source_id: str) -> bool:
        """Delete an income source."""
        source = self.db.query(IncomeSource).filter(
            IncomeSource.id == source_id
        ).first()

        if source:
            self.db.delete(source)
            self.db.commit()
            return True
        return False
