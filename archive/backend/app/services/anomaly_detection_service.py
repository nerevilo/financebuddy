"""
Anomaly Detection Service

Two-stage detection:
1. Statistical detection (fast, free) - Z-score, IQR, category spikes
2. LLM verification (Gemini Flash) - confirms if truly unusual

Detection Methods:
1. Z-Score: Transactions >4 standard deviations from mean
2. IQR: Transactions outside 3*IQR from quartiles
3. Category Spike: >5x typical category spending
4. New Large Merchant: First-time merchant with amount >$1000
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Dict, List, Optional
from collections import defaultdict
import statistics
import json
import hashlib
import time

from ..models.models import Transaction, Account, Institution
from ..core.config import get_settings
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# In-memory cache for anomaly statistics (per-user, with TTL)
# Structure: {user_id: {"stats": {...}, "expires_at": timestamp, "tx_hash": hash}}
_stats_cache: Dict[str, Dict] = {}
STATS_CACHE_TTL = 86400  # 24 hours - statistics don't change frequently

# Optional Gemini import
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


class AnomalyDetectionService:
    """
    Detect anomalous transactions using statistical methods.
    No LLM calls - pure Python statistics for cost efficiency.
    """

    # Configurable thresholds - tuned to catch truly unusual expenses
    Z_SCORE_THRESHOLD = 4.0           # Standard deviations from mean (was 2.5)
    IQR_MULTIPLIER = 3.0              # IQR fence multiplier (was 1.5)
    CATEGORY_SPIKE_MULTIPLIER = 5.0   # Times normal category spend (was 3.0)
    NEW_MERCHANT_THRESHOLD = 1000.0   # Minimum for new merchant flag (was 500)
    MINIMUM_TRANSACTIONS = 10         # Need enough data for stats
    MINIMUM_ANOMALY_AMOUNT = 500.0    # Don't flag anything under $500

    # Categories to exclude from anomaly detection (expected large recurring expenses)
    EXCLUDED_CATEGORIES = {'rent', 'groceries', 'mortgage', 'utilities'}

    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self._stats_cache: Dict = {}
        self._gemini_model = None

        # Initialize Gemini if available
        if GEMINI_AVAILABLE:
            settings = get_settings()
            if settings.gemini_api_key:
                genai.configure(api_key=settings.gemini_api_key)
                self._gemini_model = genai.GenerativeModel('gemini-2.0-flash')

    def detect_anomalies_for_user(self, lookback_days: int = 90) -> List[Dict]:
        """
        Scan user's transactions and detect anomalies.

        Returns list of detected anomalies sorted by score (highest first).
        """
        transactions = self._get_user_expenses(lookback_days)

        if len(transactions) < self.MINIMUM_TRANSACTIONS:
            return []

        # Calculate baseline statistics (with caching)
        self._calculate_statistics_cached(transactions)

        detected = []
        for txn in transactions:
            result = self._check_transaction(txn)
            if result:
                detected.append(result)

        return sorted(detected, key=lambda x: x['anomaly_score'], reverse=True)

    def check_single_transaction(self, transaction: Transaction) -> Optional[Dict]:
        """Check if a single transaction is anomalous."""
        transactions = self._get_user_expenses(90)

        if len(transactions) < self.MINIMUM_TRANSACTIONS:
            return None

        self._calculate_statistics_cached(transactions)
        return self._check_transaction(transaction)

    def _get_user_expenses(self, days: int) -> List[Transaction]:
        """Get user's expense transactions for analysis."""
        cutoff = datetime.now() - timedelta(days=days)

        # Categories that are transfers/payments, not real spending
        non_spending_teller_categories = ['investment', 'transfer']
        non_spending_enriched_categories = [
            'inter account transfer', 'transfer to stock broker',
            'credit card payment', 'payment'
        ]

        return self.db.query(Transaction).join(Account).join(Institution).filter(
            and_(
                Institution.user_id == self.user_id,
                Institution.status == "active",
                Transaction.date >= cutoff.date(),
                Transaction.amount < 0,  # Expenses only
                or_(Transaction.is_transfer.is_(None), Transaction.is_transfer == False),
                # Exclude investment/transfer categories (like Robinhood)
                or_(Transaction.teller_category.is_(None), ~Transaction.teller_category.in_(non_spending_teller_categories)),
                or_(Transaction.enriched_category.is_(None), ~Transaction.enriched_category.in_(non_spending_enriched_categories)),
            )
        ).order_by(Transaction.date.desc()).all()

    def _compute_transactions_hash(self, transactions: List[Transaction]) -> str:
        """Compute a hash of transactions for cache invalidation."""
        # Use count + sum of amounts + latest date as a fast fingerprint
        if not transactions:
            return "empty"
        total = sum(abs(t.amount) for t in transactions)
        latest = max(t.date for t in transactions)
        return hashlib.md5(f"{len(transactions)}:{total:.2f}:{latest}".encode()).hexdigest()

    def _calculate_statistics_cached(self, transactions: List[Transaction]) -> None:
        """
        Calculate statistics with caching to avoid recalculation.

        Cache is invalidated when:
        - TTL expires (24 hours)
        - Transaction fingerprint changes (new transactions added)
        """
        global _stats_cache

        tx_hash = self._compute_transactions_hash(transactions)
        cache_key = self.user_id
        now = time.time()

        # Check if we have valid cached stats
        if cache_key in _stats_cache:
            cached = _stats_cache[cache_key]
            if cached["expires_at"] > now and cached["tx_hash"] == tx_hash:
                # Cache hit - restore cached statistics
                self._stats_cache = cached["stats"].copy()
                return

        # Cache miss - calculate fresh statistics
        self._calculate_statistics(transactions)

        # Store in cache
        _stats_cache[cache_key] = {
            "stats": self._stats_cache.copy(),
            "expires_at": now + STATS_CACHE_TTL,
            "tx_hash": tx_hash
        }

    def _calculate_statistics(self, transactions: List[Transaction]) -> None:
        """Calculate statistical baselines for anomaly detection."""
        amounts = [abs(t.amount) for t in transactions]

        if len(amounts) < 2:
            return

        # Overall statistics
        self._stats_cache['mean'] = statistics.mean(amounts)
        self._stats_cache['stdev'] = statistics.stdev(amounts) if len(amounts) > 1 else 0
        self._stats_cache['median'] = statistics.median(amounts)

        # IQR calculation
        sorted_amounts = sorted(amounts)
        n = len(sorted_amounts)
        q1_idx = n // 4
        q3_idx = (3 * n) // 4
        self._stats_cache['q1'] = sorted_amounts[q1_idx]
        self._stats_cache['q3'] = sorted_amounts[q3_idx]
        self._stats_cache['iqr'] = self._stats_cache['q3'] - self._stats_cache['q1']

        # Per-category statistics
        category_amounts = defaultdict(list)
        for t in transactions:
            cat = t.enriched_category or t.teller_category or 'uncategorized'
            category_amounts[cat].append(abs(t.amount))

        self._stats_cache['category_means'] = {
            cat: statistics.mean(amts) for cat, amts in category_amounts.items()
        }

        # Known merchants (for detecting first-time large purchases)
        self._stats_cache['known_merchants'] = {
            t.enriched_merchant or t.merchant_name
            for t in transactions
            if t.enriched_merchant or t.merchant_name
        }

    def _check_transaction(self, txn: Transaction) -> Optional[Dict]:
        """
        Check if a transaction is anomalous using multiple methods.
        Returns dict with anomaly details or None if normal.
        """
        amount = abs(txn.amount)
        category = txn.enriched_category or txn.teller_category
        merchant = txn.enriched_merchant or txn.merchant_name

        # Skip small transactions - not worth flagging
        if amount < self.MINIMUM_ANOMALY_AMOUNT:
            return None

        # Skip expected recurring expense categories (rent, groceries, etc.)
        if category and category.lower() in self.EXCLUDED_CATEGORIES:
            return None

        reasons = []
        scores = []

        # Method 1: Z-Score (very high threshold - truly unusual)
        z_score = self._calculate_z_score(amount)
        if z_score and z_score > self.Z_SCORE_THRESHOLD:
            reasons.append('z_score')
            scores.append(min(z_score / 6.0, 1.0))

        # Method 2: IQR Outlier (high threshold)
        iqr_score = self._check_iqr_outlier(amount)
        if iqr_score:
            reasons.append('iqr_outlier')
            scores.append(iqr_score)

        # Method 3: Category Spike (only for non-excluded categories)
        if category:
            spike_score = self._check_category_spike(amount, category)
            if spike_score:
                reasons.append('category_spike')
                scores.append(spike_score)

        # Method 4: New Large Merchant (>$1000 at new place)
        if merchant and amount >= self.NEW_MERCHANT_THRESHOLD:
            known_merchants = self._stats_cache.get('known_merchants', set())
            if merchant not in known_merchants:
                reasons.append('new_large_merchant')
                scores.append(min(amount / 3000, 1.0))

        if not reasons:
            return None

        # Calculate composite score (average of all triggered methods)
        composite_score = sum(scores) / len(scores)
        primary_reason = reasons[0]

        return {
            'transaction_id': txn.id,
            'transaction': txn,
            'amount': amount,
            'merchant': merchant,
            'category': category,
            'date': txn.date,
            'anomaly_score': round(composite_score, 3),
            'anomaly_reason': primary_reason,
            'all_reasons': reasons,
            'description': self._generate_description(txn, primary_reason, amount)
        }

    def _calculate_z_score(self, amount: float) -> Optional[float]:
        """Calculate Z-score for an amount."""
        mean = self._stats_cache.get('mean')
        stdev = self._stats_cache.get('stdev')

        if mean is None or stdev is None or stdev == 0:
            return None

        return abs(amount - mean) / stdev

    def _check_iqr_outlier(self, amount: float) -> Optional[float]:
        """Check if amount is outside IQR fences. Returns score 0-1."""
        q3 = self._stats_cache.get('q3')
        iqr = self._stats_cache.get('iqr')

        if q3 is None or iqr is None or iqr == 0:
            return None

        upper_fence = q3 + (self.IQR_MULTIPLIER * iqr)

        if amount > upper_fence:
            excess = (amount - upper_fence) / iqr
            return min(excess / 3.0, 1.0)

        return None

    def _check_category_spike(self, amount: float, category: str) -> Optional[float]:
        """Check if amount is a spike for this category. Returns score 0-1."""
        category_means = self._stats_cache.get('category_means', {})
        cat_mean = category_means.get(category)

        if cat_mean is None or cat_mean == 0:
            return None

        ratio = amount / cat_mean

        if ratio > self.CATEGORY_SPIKE_MULTIPLIER:
            return min((ratio - self.CATEGORY_SPIKE_MULTIPLIER) / 5.0, 1.0)

        return None

    def _generate_description(self, txn: Transaction, reason: str, amount: float) -> str:
        """Generate human-readable description of anomaly."""
        merchant = txn.enriched_merchant or txn.merchant_name or 'Unknown'
        category = txn.enriched_category or txn.teller_category or 'spending'

        descriptions = {
            'z_score': f"${amount:,.2f} at {merchant} is unusually high compared to your typical spending",
            'iqr_outlier': f"${amount:,.2f} at {merchant} is statistically unusual for your spending pattern",
            'category_spike': f"${amount:,.2f} at {merchant} is much higher than your usual {category} spending",
            'new_large_merchant': f"${amount:,.2f} at {merchant} - first purchase at this merchant with a large amount"
        }

        return descriptions.get(reason, f"${amount:,.2f} at {merchant} appears unusual")

    # ========== LLM Verification ==========

    async def verify_with_llm(self, anomalies: List[Dict]) -> List[Dict]:
        """
        Use Gemini to verify statistically-detected anomalies.

        The LLM reviews each candidate and determines:
        1. Is this truly a one-time/unusual expense?
        2. What type is it? (one-time, recurring-but-large, false-positive)
        3. Should it be excluded from budget?

        Returns filtered list with LLM assessments.
        """
        if not self._gemini_model or not anomalies:
            return anomalies

        # Build context about user's spending
        mean = self._stats_cache.get('mean', 0)
        median = self._stats_cache.get('median', 0)

        # Format anomalies for LLM
        transactions_text = "\n".join([
            f"- ${a['amount']:,.2f} at {a['merchant'] or 'Unknown'} ({a['category'] or 'uncategorized'}) on {a['date']}"
            for a in anomalies
        ])

        prompt = f"""You are a personal finance assistant. Review these transactions that were statistically flagged as unusual.

User's typical spending: average ${mean:,.2f}, median ${median:,.2f}

Flagged transactions:
{transactions_text}

For EACH transaction, determine:
1. Is this a TRUE one-time expense? (moving costs, immigration fees, medical procedures, large deposits, annual fees)
2. Or is it a FALSE POSITIVE? (regular rent, normal grocery trips, recurring subscriptions)

IMPORTANT RULES:
- Monthly rent payments are NOT unusual - they're expected recurring expenses
- Regular grocery trips (even $200 at Costco) are NOT unusual
- Government fees (USCIS, DMV, passport) ARE unusual one-time expenses
- Large deposits/down payments ARE unusual one-time expenses
- Annual subscriptions CAN be one-time if >$500

Respond with JSON array:
[
  {{
    "merchant": "merchant name",
    "amount": dollar amount,
    "is_one_time": true/false,
    "reason": "brief explanation",
    "expense_type": "one-time" | "recurring" | "false-positive"
  }}
]

Only include transactions you've analyzed. Be conservative - only flag TRUE one-time expenses."""

        try:
            response = self._gemini_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 500,
                }
            )

            # Parse response
            result = self._extract_json(response.text)

            if result and isinstance(result, list):
                # Match LLM results back to anomalies
                verified = []
                for anomaly in anomalies:
                    llm_match = next(
                        (r for r in result if abs(r.get('amount', 0) - anomaly['amount']) < 1),
                        None
                    )

                    if llm_match and llm_match.get('is_one_time'):
                        anomaly['llm_verified'] = True
                        anomaly['llm_reason'] = llm_match.get('reason', '')
                        anomaly['expense_type'] = llm_match.get('expense_type', 'one-time')
                        anomaly['description'] = llm_match.get('reason', anomaly['description'])
                        verified.append(anomaly)

                return verified

        except Exception as e:
            logger.error("LLM verification error", extra={"error": str(e)})

        return anomalies

    def _extract_json(self, text: str) -> Optional[any]:
        """Extract JSON from LLM response."""
        try:
            return json.loads(text)
        except:
            pass

        # Try extracting from code block
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except:
                    pass

        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except:
                    pass

        # Try extracting array
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except:
                pass

        return None

    # ========== User Feedback Methods ==========

    def mark_as_one_time(
        self,
        transaction_id: str,
        reason: Optional[str] = None,
        exclude_from_budget: bool = True
    ) -> Optional[Transaction]:
        """Mark a transaction as one-time expense."""
        txn = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()

        if not txn:
            return None

        txn.is_one_time = True
        txn.one_time_reason = reason
        txn.exclude_from_budget = exclude_from_budget
        txn.user_reviewed = True

        self.db.commit()
        return txn

    def mark_as_normal(self, transaction_id: str) -> Optional[Transaction]:
        """User indicates this is a normal transaction (not anomalous)."""
        txn = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()

        if not txn:
            return None

        txn.is_anomaly = False
        txn.is_one_time = False
        txn.exclude_from_budget = False
        txn.user_reviewed = True

        self.db.commit()
        return txn

    def get_unreviewed_anomalies(self, limit: int = 10) -> List[Transaction]:
        """Get anomalies that user hasn't reviewed yet."""
        return self.db.query(Transaction).join(Account).join(Institution).filter(
            and_(
                Institution.user_id == self.user_id,
                Transaction.is_anomaly == True,
                Transaction.user_reviewed == False
            )
        ).order_by(Transaction.anomaly_score.desc()).limit(limit).all()

    def get_one_time_expenses(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        """Get all one-time expenses in a date range."""
        query = self.db.query(Transaction).join(Account).join(Institution).filter(
            and_(
                Institution.user_id == self.user_id,
                Transaction.is_one_time == True
            )
        )

        if start_date:
            query = query.filter(Transaction.date >= start_date.date())
        if end_date:
            query = query.filter(Transaction.date <= end_date.date())

        return query.order_by(Transaction.date.desc()).all()

    # ========== Batch Processing ==========

    def run_detection_and_save(self) -> int:
        """
        Run anomaly detection and save results to database.
        Called during transaction sync or as background job.
        Returns count of new anomalies detected.
        """
        anomalies = self.detect_anomalies_for_user()
        count = 0

        for anomaly in anomalies:
            txn = anomaly['transaction']

            # Only update if not already flagged and not reviewed
            if not txn.is_anomaly and not txn.user_reviewed:
                txn.is_anomaly = True
                txn.anomaly_score = anomaly['anomaly_score']
                txn.anomaly_reason = anomaly['anomaly_reason']
                count += 1

        self.db.commit()
        return count

    def get_anomaly_summary(self) -> Dict:
        """Get summary stats for dashboard widget."""
        unreviewed = self.get_unreviewed_anomalies(100)
        one_time = self.get_one_time_expenses()

        return {
            'unreviewed_count': len(unreviewed),
            'one_time_count': len(one_time),
            'one_time_total': sum(abs(t.amount) for t in one_time),
            'top_unreviewed': unreviewed[:3]
        }
