# Transaction Categorization Implementation Plan

## Executive Summary

This plan addresses two critical issues in FinTrack:
1. **Transfers counted as spending**: "Withdrawal to 360 Performance" should not be categorized as an expense
2. **Poor merchant recognition**: "HARDEE S" should be auto-categorized as dining/food

**Strategy**: Implement a phased hybrid approach that starts with an API (Ntropy), builds proprietary ML capability, then optimizes costs by combining both.

**Timeline**: 3 months to full production-ready hybrid system
**Final Cost**: ~$30/month for 100k transactions (vs. $3,000/month API-only)

---

## Phase 1: Foundation & Quick Wins (Week 1-2)

### Goals
- Eliminate transfers from spending calculations
- Integrate Ntropy API for initial merchant categorization
- Build training data foundation

### Tasks

#### 1.1 Transfer Detection (Day 1-2)
**File**: `backend/app/services/categorization.py`

```python
class TransferDetector:
    """Identifies internal transfers that shouldn't count as spending"""

    TRANSFER_KEYWORDS = [
        "WITHDRAWAL TO",
        "TRANSFER TO",
        "TRANSFER FROM",
        "ACH TRANSFER",
        "INTERNAL TRANSFER",
        "BETWEEN ACCOUNTS",
        "ACCOUNT TRANSFER"
    ]

    TRANSFER_TYPES = ["transfer", "ach"]

    def is_transfer(self, transaction):
        """
        Multi-signal transfer detection

        Returns:
            bool: True if transaction is a transfer, not real spending
        """
        # Signal 1: Teller transaction type
        if transaction.type in self.TRANSFER_TYPES:
            # Check if it's actually to another account
            desc_upper = transaction.description.upper()
            if any(kw in desc_upper for kw in self.TRANSFER_KEYWORDS):
                return True

        # Signal 2: Description keywords
        if any(kw in transaction.description.upper() for kw in self.TRANSFER_KEYWORDS):
            return True

        # Signal 3: Teller category
        if transaction.teller_category and "transfer" in transaction.teller_category.lower():
            return True

        return False
```

**Update Analytics Router** (`backend/app/routers/analytics.py`):

```python
# Import the detector
from app.services.categorization import TransferDetector

transfer_detector = TransferDetector()

# In get_spending_by_category endpoint (line ~75)
transactions = db.query(Transaction).join(Account).join(Institution).filter(
    and_(
        Institution.status == "active",
        Transaction.date >= start,
        Transaction.date <= end,
        Transaction.amount < 0  # Expenses are negative
    )
).all()

# NEW: Filter out transfers
spending_transactions = [
    tx for tx in transactions
    if not transfer_detector.is_transfer(tx)
]

# Continue with category aggregation using spending_transactions
```

**Expected Impact**:
- "Withdrawal to 360 Performance" ($7,000) removed from spending
- Spending drops from $8,817.94 to $1,817.94 (correct amount)
- Savings rate calculation becomes accurate

#### 1.2 Ntropy API Integration (Day 3-5)

**Install Dependencies**:
```bash
pip install httpx anthropic
```

**Environment Variables** (`.env`):
```bash
NTROPY_API_KEY=your_api_key_here
USE_NTROPY=true
```

**Ntropy Service** (`backend/app/services/ntropy_client.py`):

```python
import httpx
from typing import Dict, List, Optional
from app.core.config import settings

class NtropyClient:
    """Client for Ntropy transaction enrichment API"""

    BASE_URL = "https://api.ntropy.com/v3"

    def __init__(self):
        self.api_key = settings.NTROPY_API_KEY
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    async def enrich_transaction(self, transaction) -> Dict:
        """
        Enrich a single transaction with Ntropy

        Returns:
            {
                "merchant": "Hardee's",
                "category": "dining",
                "location": {...},
                "confidence": 0.95
            }
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/transactions",
                headers=self.headers,
                json={
                    "transactions": [{
                        "description": transaction.description,
                        "amount": float(transaction.amount),
                        "date": transaction.date.isoformat(),
                        "account_holder_type": "consumer"
                    }]
                },
                timeout=30.0
            )

            if response.status_code != 200:
                raise Exception(f"Ntropy API error: {response.text}")

            data = response.json()
            enriched = data["transactions"][0]

            return {
                "merchant": enriched.get("merchant_name"),
                "category": enriched.get("category"),
                "location": enriched.get("location"),
                "confidence": enriched.get("confidence", 0.0)
            }

    async def enrich_batch(self, transactions: List) -> List[Dict]:
        """
        Enrich multiple transactions in one API call (more efficient)
        Max 100 transactions per batch
        """
        batch_size = 100
        results = []

        for i in range(0, len(transactions), batch_size):
            batch = transactions[i:i + batch_size]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/transactions",
                    headers=self.headers,
                    json={
                        "transactions": [
                            {
                                "description": tx.description,
                                "amount": float(tx.amount),
                                "date": tx.date.isoformat(),
                                "account_holder_type": "consumer"
                            }
                            for tx in batch
                        ]
                    },
                    timeout=60.0
                )

                if response.status_code == 200:
                    data = response.json()
                    results.extend(data["transactions"])

        return results
```

#### 1.3 Database Schema Updates (Day 6)

**Add Migration** (`backend/app/models/models.py`):

```python
# Update Transaction model
class Transaction(Base):
    __tablename__ = "transactions"

    # ... existing fields ...

    # NEW FIELDS
    enriched_merchant = Column(String, nullable=True)  # Clean merchant name from Ntropy
    enriched_category = Column(String, nullable=True)  # Category from ML/Ntropy
    is_transfer = Column(Boolean, default=False)       # Transfer flag
    categorization_source = Column(String, nullable=True)  # 'rule', 'bert', 'ntropy'
    categorization_confidence = Column(Float, nullable=True)  # Confidence score
    enriched_at = Column(DateTime, nullable=True)      # When it was enriched
```

**Create Migration**:
```bash
cd backend
alembic revision --autogenerate -m "Add enrichment fields to transactions"
alembic upgrade head
```

#### 1.4 Categorization Endpoint (Day 7)

**New Router** (`backend/app/routers/categorization.py`):

```python
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.categorization import TransferDetector
from app.services.ntropy_client import NtropyClient
from app.models.models import Transaction, Account, Institution
from datetime import datetime

router = APIRouter(prefix="/categorization", tags=["categorization"])

@router.post("/enrich/all")
async def enrich_all_transactions(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Enrich all uncategorized transactions using Ntropy
    Runs in background to avoid timeout
    """
    background_tasks.add_task(enrich_transactions_task, db)
    return {"message": "Enrichment started in background"}

async def enrich_transactions_task(db: Session):
    """Background task to enrich transactions"""
    transfer_detector = TransferDetector()
    ntropy_client = NtropyClient()

    # Get all transactions without enrichment
    transactions = db.query(Transaction).filter(
        Transaction.enriched_merchant == None
    ).all()

    for tx in transactions:
        # Step 1: Check if transfer
        tx.is_transfer = transfer_detector.is_transfer(tx)

        if not tx.is_transfer:
            # Step 2: Enrich with Ntropy
            try:
                enriched = await ntropy_client.enrich_transaction(tx)
                tx.enriched_merchant = enriched["merchant"]
                tx.enriched_category = enriched["category"]
                tx.categorization_source = "ntropy"
                tx.categorization_confidence = enriched["confidence"]
                tx.enriched_at = datetime.utcnow()
            except Exception as e:
                print(f"Failed to enrich transaction {tx.id}: {e}")
                continue

        db.commit()

@router.get("/stats")
def get_categorization_stats(db: Session = Depends(get_db)):
    """Get statistics on categorization coverage"""
    total = db.query(Transaction).count()
    enriched = db.query(Transaction).filter(Transaction.enriched_merchant != None).count()
    transfers = db.query(Transaction).filter(Transaction.is_transfer == True).count()

    return {
        "total_transactions": total,
        "enriched": enriched,
        "transfers": transfers,
        "coverage": (enriched / total * 100) if total > 0 else 0
    }
```

**Register Router** (`backend/app/main.py`):
```python
from app.routers import categorization

app.include_router(categorization.router)
```

### Deliverables
- ✅ Transfers excluded from spending calculations
- ✅ Ntropy API integration working
- ✅ Database schema updated with enrichment fields
- ✅ Training data being collected automatically
- ✅ 2,000 free transactions enriched with high accuracy

### Cost: $0 (using free tier)

---

## Phase 2: Build Proprietary ML Model (Week 3-6)

### Goals
- Train custom BERT model on collected data
- Achieve 80%+ accuracy on known merchants
- Reduce dependency on Ntropy API

### Tasks

#### 2.1 Data Collection & Preparation (Week 3)

**Export Training Data**:

```python
# backend/app/scripts/export_training_data.py

import pandas as pd
from app.core.database import SessionLocal
from app.models.models import Transaction

def export_training_data():
    """Export enriched transactions as training dataset"""
    db = SessionLocal()

    # Get all transactions with Ntropy categorizations
    transactions = db.query(Transaction).filter(
        Transaction.enriched_category != None,
        Transaction.is_transfer == False
    ).all()

    data = []
    for tx in transactions:
        data.append({
            'description': tx.description,
            'merchant_raw': tx.merchant_name,
            'merchant_clean': tx.enriched_merchant,
            'category': tx.enriched_category,
            'amount': tx.amount,
            'confidence': tx.categorization_confidence
        })

    df = pd.DataFrame(data)
    df.to_csv('training_data.csv', index=False)
    print(f"Exported {len(df)} transactions for training")

if __name__ == "__main__":
    export_training_data()
```

**Supplement with Public Data**:
```bash
# Download Kaggle dataset
kaggle datasets download -d apoorvwatsky/bank-transaction-data

# Merge with your data
python merge_datasets.py
```

#### 2.2 BERT Model Training (Week 4)

**Install ML Dependencies**:
```bash
pip install transformers torch scikit-learn pandas
```

**Training Script** (`backend/app/ml/train_categorizer.py`):

```python
from transformers import BertTokenizer, BertForSequenceClassification
from transformers import Trainer, TrainingArguments
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

class TransactionCategorizer:
    """BERT-based transaction categorization model"""

    def __init__(self, model_path=None):
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        self.label_encoder = LabelEncoder()

        if model_path:
            self.model = BertForSequenceClassification.from_pretrained(model_path)
        else:
            self.model = None

    def prepare_data(self, csv_path):
        """Load and prepare training data"""
        df = pd.read_csv(csv_path)

        # Combine description and merchant for better context
        df['text'] = df['description'] + " " + df['merchant_raw'].fillna('')

        # Encode categories as numbers
        df['label'] = self.label_encoder.fit_transform(df['category'])

        # Split train/test
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)

        return train_df, test_df

    def tokenize_data(self, df):
        """Tokenize text for BERT"""
        encodings = self.tokenizer(
            df['text'].tolist(),
            truncation=True,
            padding=True,
            max_length=128,
            return_tensors='pt'
        )

        labels = torch.tensor(df['label'].tolist())

        return encodings, labels

    def train(self, train_df, test_df, output_dir='./ml_models/bert_categorizer'):
        """Train the BERT model"""
        num_labels = len(self.label_encoder.classes_)
        self.model = BertForSequenceClassification.from_pretrained(
            'bert-base-uncased',
            num_labels=num_labels
        )

        train_encodings, train_labels = self.tokenize_data(train_df)
        test_encodings, test_labels = self.tokenize_data(test_df)

        # Create PyTorch datasets
        train_dataset = TransactionDataset(train_encodings, train_labels)
        test_dataset = TransactionDataset(test_encodings, test_labels)

        # Training arguments
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=3,
            per_device_train_batch_size=16,
            per_device_eval_batch_size=64,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir='./logs',
            logging_steps=10,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
        )

        # Train
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=test_dataset,
        )

        trainer.train()

        # Save model
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)

        # Save label encoder
        import pickle
        with open(f'{output_dir}/label_encoder.pkl', 'wb') as f:
            pickle.dump(self.label_encoder, f)

        print(f"Model trained and saved to {output_dir}")

    def predict(self, text: str):
        """Predict category for a transaction"""
        if not self.model:
            raise Exception("Model not loaded")

        inputs = self.tokenizer(
            text,
            return_tensors='pt',
            truncation=True,
            padding=True,
            max_length=128
        )

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=1)
            predicted_class = torch.argmax(probabilities, dim=1).item()
            confidence = probabilities[0][predicted_class].item()

        category = self.label_encoder.inverse_transform([predicted_class])[0]

        return {
            'category': category,
            'confidence': confidence
        }

class TransactionDataset(torch.utils.data.Dataset):
    """PyTorch dataset for transactions"""

    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: val[idx] for key, val in self.encodings.items()}
        item['labels'] = self.labels[idx]
        return item

    def __len__(self):
        return len(self.labels)

# Training script
if __name__ == "__main__":
    categorizer = TransactionCategorizer()
    train_df, test_df = categorizer.prepare_data('training_data.csv')
    categorizer.train(train_df, test_df)

    # Test prediction
    result = categorizer.predict("HARDEE S 12345")
    print(f"Prediction: {result}")
```

**Run Training**:
```bash
cd backend
python -m app.ml.train_categorizer
```

**Expected Results**:
- Training time: 30-60 minutes on CPU (5-10 min on GPU)
- Accuracy: 75-85% with 1,000+ labeled transactions
- Model size: ~400MB

#### 2.3 Model Serving Service (Week 5)

**ML Service** (`backend/app/services/ml_categorizer.py`):

```python
from app.ml.train_categorizer import TransactionCategorizer
import pickle
from functools import lru_cache

class MLCategorizationService:
    """Service for using BERT model in production"""

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._load_model()
        return cls._instance

    @classmethod
    def _load_model(cls):
        """Load model once at startup"""
        try:
            model_path = './ml_models/bert_categorizer'
            cls._model = TransactionCategorizer(model_path=model_path)

            # Load label encoder
            with open(f'{model_path}/label_encoder.pkl', 'rb') as f:
                cls._model.label_encoder = pickle.load(f)

            print("ML model loaded successfully")
        except Exception as e:
            print(f"Failed to load ML model: {e}")
            cls._model = None

    @lru_cache(maxsize=10000)
    def categorize(self, merchant_text: str):
        """
        Categorize transaction with caching
        LRU cache stores 10k most recent predictions in memory
        """
        if not self._model:
            return None, 0.0

        result = self._model.predict(merchant_text)
        return result['category'], result['confidence']

    def categorize_batch(self, texts: list):
        """Categorize multiple transactions"""
        results = []
        for text in texts:
            category, confidence = self.categorize(text)
            results.append({'category': category, 'confidence': confidence})
        return results
```

**Update Main App** (`backend/app/main.py`):
```python
from app.services.ml_categorizer import MLCategorizationService

@app.on_event("startup")
async def startup_event():
    """Load ML model on startup"""
    MLCategorizationService()  # Initialize singleton
```

#### 2.4 Model Evaluation Dashboard (Week 6)

**Evaluation Script** (`backend/app/scripts/evaluate_model.py`):

```python
from app.services.ml_categorizer import MLCategorizationService
from app.services.ntropy_client import NtropyClient
from app.core.database import SessionLocal
from app.models.models import Transaction
import asyncio

async def evaluate_model():
    """Compare BERT model vs Ntropy accuracy"""
    db = SessionLocal()
    ml_service = MLCategorizationService()
    ntropy = NtropyClient()

    # Get sample of transactions
    test_transactions = db.query(Transaction).filter(
        Transaction.enriched_category != None,
        Transaction.is_transfer == False
    ).limit(500).all()

    correct_bert = 0
    total = 0

    for tx in test_transactions:
        ground_truth = tx.enriched_category  # Ntropy's answer
        text = f"{tx.description} {tx.merchant_name or ''}"

        bert_category, confidence = ml_service.categorize(text)

        if bert_category == ground_truth:
            correct_bert += 1

        total += 1

        if total % 50 == 0:
            print(f"Processed {total} transactions...")

    accuracy = (correct_bert / total) * 100
    print(f"\nBERT Model Accuracy: {accuracy:.2f}%")
    print(f"Correct: {correct_bert}/{total}")

    return accuracy

if __name__ == "__main__":
    asyncio.run(evaluate_model())
```

### Deliverables
- ✅ BERT model trained on 1,000+ transactions
- ✅ Model achieving 75-85% accuracy
- ✅ ML service running in production
- ✅ Evaluation showing model performance vs. Ntropy

### Cost: $0 (model training is one-time, runs locally)

---

## Phase 3: Hybrid Production System (Week 7-12)

### Goals
- Combine rule-based, BERT, and Ntropy into intelligent cascade
- Minimize API costs while maximizing accuracy
- Build automatic retraining pipeline

### Tasks

#### 3.1 Unified Categorization Service (Week 7-8)

**Hybrid Service** (`backend/app/services/categorization.py`):

```python
from typing import Tuple, Optional
from datetime import datetime
from app.services.ml_categorizer import MLCategorizationService
from app.services.ntropy_client import NtropyClient
from app.models.models import Transaction
from app.core.config import settings
import asyncio

class UnifiedCategorizationService:
    """
    Intelligent multi-layer categorization system

    Layers (in order):
    1. Cache lookup (instant, free)
    2. Transfer detection (instant, free)
    3. Rule-based merchant patterns (instant, free)
    4. BERT ML model (50ms, free)
    5. Ntropy API (200ms, paid - only for edge cases)
    """

    def __init__(self):
        self.ml_service = MLCategorizationService()
        self.ntropy = NtropyClient() if settings.USE_NTROPY else None

        # In-memory cache for merchant categorizations
        self.cache = {}

        # Common merchant patterns for fast matching
        self.merchant_patterns = {
            'dining': [
                'HARDEE', 'MCDONALD', 'BURGER', 'DOMINO', 'PIZZA',
                'RESTAURANT', 'CAFE', 'STARBUCKS', 'SUBWAY', 'WENDY',
                'KFC', 'TACO BELL', 'CHIPOTLE', 'PANERA'
            ],
            'groceries': [
                'PUBLIX', 'WALMART', 'KROGER', 'TARGET', 'SAFEWAY',
                'WHOLE FOODS', 'TRADER JOE', 'ALDI', 'COSTCO', 'SAM\'S CLUB'
            ],
            'gas': [
                'SHELL', 'EXXON', 'BP', 'CHEVRON', 'MOBIL', 'PETRO',
                'MARATHON', 'SUNOCO', 'ARCO', 'SPEEDWAY'
            ],
            'entertainment': [
                'NETFLIX', 'SPOTIFY', 'HULU', 'DISNEY', 'HBO',
                'AMAZON PRIME', 'YOUTUBE', 'THEATER', 'CINEMA'
            ],
            'utilities': [
                'ELECTRIC', 'WATER', 'GAS COMPANY', 'INTERNET',
                'COMCAST', 'VERIZON', 'AT&T', 'T-MOBILE'
            ]
        }

        # Transfer detection keywords
        self.transfer_keywords = [
            'WITHDRAWAL TO', 'TRANSFER TO', 'TRANSFER FROM',
            'ACH TRANSFER', 'INTERNAL TRANSFER', 'BETWEEN ACCOUNTS'
        ]

        # Stats for monitoring
        self.stats = {
            'cache_hits': 0,
            'transfer_detections': 0,
            'rule_matches': 0,
            'bert_predictions': 0,
            'ntropy_calls': 0,
            'failures': 0
        }

    async def categorize(self, transaction: Transaction) -> Tuple[Optional[str], bool, str, float]:
        """
        Categorize a transaction using hybrid approach

        Returns:
            (category, is_transfer, source, confidence)
            - category: The assigned category (or None if transfer)
            - is_transfer: Boolean indicating if this is a transfer
            - source: 'cache', 'rule', 'bert', 'ntropy'
            - confidence: 0.0 to 1.0
        """
        merchant_key = self._get_merchant_key(transaction)

        # Layer 1: Cache lookup
        if merchant_key in self.cache:
            self.stats['cache_hits'] += 1
            cached = self.cache[merchant_key]
            return cached['category'], cached['is_transfer'], 'cache', 1.0

        # Layer 2: Transfer detection
        if self._is_transfer(transaction):
            self.stats['transfer_detections'] += 1
            result = (None, True, 'rule', 1.0)
            self.cache[merchant_key] = {
                'category': None,
                'is_transfer': True
            }
            return result

        # Layer 3: Rule-based pattern matching
        rule_category = self._match_merchant_pattern(transaction)
        if rule_category:
            self.stats['rule_matches'] += 1
            result = (rule_category, False, 'rule', 0.95)
            self.cache[merchant_key] = {
                'category': rule_category,
                'is_transfer': False
            }
            return result

        # Layer 4: BERT ML model
        text = f"{transaction.description} {transaction.merchant_name or ''}"
        bert_category, bert_confidence = self.ml_service.categorize(text)

        if bert_category and bert_confidence >= 0.75:
            # High confidence BERT prediction
            self.stats['bert_predictions'] += 1
            result = (bert_category, False, 'bert', bert_confidence)
            self.cache[merchant_key] = {
                'category': bert_category,
                'is_transfer': False
            }
            return result

        # Layer 5: Ntropy API (only for low-confidence cases)
        if self.ntropy and bert_confidence < 0.5:
            try:
                enriched = await self.ntropy.enrich_transaction(transaction)
                self.stats['ntropy_calls'] += 1

                ntropy_category = enriched['category']
                ntropy_confidence = enriched.get('confidence', 0.9)

                result = (ntropy_category, False, 'ntropy', ntropy_confidence)
                self.cache[merchant_key] = {
                    'category': ntropy_category,
                    'is_transfer': False
                }

                # Store for future BERT retraining
                await self._save_training_example(transaction, ntropy_category, ntropy_confidence)

                return result
            except Exception as e:
                print(f"Ntropy API error: {e}")
                self.stats['failures'] += 1

        # Fallback: Use BERT's best guess even with low confidence
        self.stats['bert_predictions'] += 1
        result = (bert_category or 'uncategorized', False, 'bert', bert_confidence)
        return result

    def _get_merchant_key(self, transaction: Transaction) -> str:
        """Generate cache key for merchant"""
        return (transaction.merchant_name or transaction.description[:30]).upper().strip()

    def _is_transfer(self, transaction: Transaction) -> bool:
        """Multi-signal transfer detection"""
        # Check transaction type
        if transaction.type in ['transfer', 'ach']:
            desc_upper = transaction.description.upper()
            if any(kw in desc_upper for kw in self.transfer_keywords):
                return True

        # Check description
        desc_upper = transaction.description.upper()
        if any(kw in desc_upper for kw in self.transfer_keywords):
            return True

        # Check Teller category
        if transaction.teller_category:
            if 'transfer' in transaction.teller_category.lower():
                return True

        return False

    def _match_merchant_pattern(self, transaction: Transaction) -> Optional[str]:
        """Fast keyword-based categorization"""
        text = f"{transaction.description} {transaction.merchant_name or ''}".upper()

        for category, patterns in self.merchant_patterns.items():
            if any(pattern in text for pattern in patterns):
                return category

        return None

    async def _save_training_example(self, transaction: Transaction, category: str, confidence: float):
        """Save Ntropy result for future model retraining"""
        # This would append to a training dataset CSV or database
        import csv
        import os

        training_file = 'ml_models/retraining_data.csv'
        file_exists = os.path.exists(training_file)

        with open(training_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['description', 'merchant', 'category', 'confidence', 'timestamp'])

            writer.writerow([
                transaction.description,
                transaction.merchant_name,
                category,
                confidence,
                datetime.utcnow().isoformat()
            ])

    def get_stats(self) -> dict:
        """Get categorization statistics"""
        total = sum(self.stats.values())
        if total == 0:
            return self.stats

        return {
            **self.stats,
            'total_categorizations': total,
            'cache_hit_rate': f"{(self.stats['cache_hits'] / total) * 100:.1f}%",
            'ntropy_usage_rate': f"{(self.stats['ntropy_calls'] / total) * 100:.1f}%"
        }
```

#### 3.2 Update Analytics to Use Hybrid System (Week 8)

**Update Analytics Router** (`backend/app/routers/analytics.py`):

```python
from app.services.categorization import UnifiedCategorizationService

categorizer = UnifiedCategorizationService()

@router.get("/spending/by-category")
async def get_spending_by_category(
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db)
):
    """Get spending breakdown by category using hybrid categorization"""

    # ... date handling ...

    # Get all transactions in period
    transactions = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.amount < 0  # Only expenses
        )
    ).all()

    # Categorize each transaction
    category_totals = {}

    for tx in transactions:
        category, is_transfer, source, confidence = await categorizer.categorize(tx)

        # Skip transfers
        if is_transfer:
            continue

        # Aggregate by category
        if category not in category_totals:
            category_totals[category] = {
                'total': 0,
                'count': 0
            }

        category_totals[category]['total'] += abs(tx.amount)
        category_totals[category]['count'] += 1

    # Calculate percentages
    total_spending = sum(cat['total'] for cat in category_totals.values())

    result = []
    for category, data in category_totals.items():
        result.append({
            'category': category,
            'total': round(data['total'], 2),
            'count': data['count'],
            'percentage': round((data['total'] / total_spending * 100), 1) if total_spending > 0 else 0
        })

    # Sort by total descending
    result.sort(key=lambda x: x['total'], reverse=True)

    return result

@router.get("/categorization/stats")
def get_categorization_stats():
    """Get hybrid categorization performance stats"""
    return categorizer.get_stats()
```

#### 3.3 Automatic Model Retraining (Week 9-10)

**Retraining Script** (`backend/app/scripts/retrain_model.py`):

```python
import pandas as pd
from app.ml.train_categorizer import TransactionCategorizer
import os
from datetime import datetime

def retrain_model():
    """
    Retrain BERT model with new examples from Ntropy
    Run this monthly or when you have 500+ new examples
    """

    # Load original training data
    original_data = pd.read_csv('ml_models/training_data.csv')

    # Load new examples from Ntropy categorizations
    new_data = pd.read_csv('ml_models/retraining_data.csv')

    # Filter high-confidence examples only
    new_data = new_data[new_data['confidence'] >= 0.9]

    print(f"Original training data: {len(original_data)} examples")
    print(f"New high-confidence data: {len(new_data)} examples")

    # Merge datasets
    combined = pd.concat([original_data, new_data], ignore_index=True)
    combined = combined.drop_duplicates(subset=['description', 'merchant'])

    print(f"Combined training data: {len(combined)} examples")

    # Save combined dataset
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    combined.to_csv(f'ml_models/training_data_{timestamp}.csv', index=False)

    # Retrain model
    categorizer = TransactionCategorizer()
    train_df, test_df = categorizer.prepare_data(f'ml_models/training_data_{timestamp}.csv')

    output_dir = f'ml_models/bert_categorizer_{timestamp}'
    categorizer.train(train_df, test_df, output_dir=output_dir)

    # Update symlink to latest model
    import shutil
    if os.path.exists('ml_models/bert_categorizer'):
        shutil.rmtree('ml_models/bert_categorizer')
    shutil.copytree(output_dir, 'ml_models/bert_categorizer')

    print("Model retrained successfully!")
    print("Restart the application to load the new model")

if __name__ == "__main__":
    retrain_model()
```

**Cron Job** (run monthly):
```bash
# Add to crontab: retrain model on 1st of each month at 2am
0 2 1 * * cd /path/to/backend && python -m app.scripts.retrain_model
```

#### 3.4 Cost Monitoring Dashboard (Week 11)

**Cost Tracking** (`backend/app/services/cost_tracker.py`):

```python
from datetime import datetime, timedelta
from sqlalchemy import func
from app.models.models import Transaction
from app.core.database import SessionLocal

class CostTracker:
    """Track Ntropy API usage and costs"""

    NTROPY_COST_PER_TRANSACTION = 0.02  # Estimate, adjust based on actual pricing

    @staticmethod
    def get_monthly_costs():
        """Calculate Ntropy costs for current month"""
        db = SessionLocal()

        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0)

        # Count transactions categorized by Ntropy this month
        ntropy_count = db.query(func.count(Transaction.id)).filter(
            Transaction.categorization_source == 'ntropy',
            Transaction.enriched_at >= start_of_month
        ).scalar()

        cost = ntropy_count * CostTracker.NTROPY_COST_PER_TRANSACTION

        return {
            'month': start_of_month.strftime('%Y-%m'),
            'ntropy_calls': ntropy_count,
            'estimated_cost': round(cost, 2),
            'cost_per_transaction': CostTracker.NTROPY_COST_PER_TRANSACTION
        }

    @staticmethod
    def get_cost_breakdown():
        """Get cost breakdown by categorization source"""
        db = SessionLocal()

        # Count by source
        breakdown = db.query(
            Transaction.categorization_source,
            func.count(Transaction.id)
        ).filter(
            Transaction.categorization_source != None
        ).group_by(
            Transaction.categorization_source
        ).all()

        total = sum(count for _, count in breakdown)

        result = []
        for source, count in breakdown:
            percentage = (count / total * 100) if total > 0 else 0
            cost = count * CostTracker.NTROPY_COST_PER_TRANSACTION if source == 'ntropy' else 0

            result.append({
                'source': source,
                'count': count,
                'percentage': round(percentage, 1),
                'cost': round(cost, 2)
            })

        return result
```

**Add Cost Endpoint** (`backend/app/routers/categorization.py`):

```python
from app.services.cost_tracker import CostTracker

@router.get("/costs/monthly")
def get_monthly_costs():
    """Get Ntropy API costs for current month"""
    return CostTracker.get_monthly_costs()

@router.get("/costs/breakdown")
def get_cost_breakdown():
    """Get cost breakdown by categorization source"""
    return CostTracker.get_cost_breakdown()
```

#### 3.5 Frontend Dashboard Updates (Week 12)

**Update Spending Chart** (`frontend/src/components/dashboard/SpendingChart.tsx`):

```typescript
// Add new color mapping for auto-detected categories
const getCategoryColor = (category: string) => {
  const colorMap: Record<string, string> = {
    groceries: 'emerald',
    dining: 'amber',
    shopping: 'violet',
    entertainment: 'pink',
    gas: 'blue',
    utilities: 'gray',
    healthcare: 'red',
    travel: 'cyan',
    income: 'green',
    transfer: 'slate',  // Hidden from spending
    uncategorized: 'neutral',
  };

  return colorMap[category.toLowerCase()] || 'neutral';
};
```

**Add Categorization Stats Widget** (`frontend/src/components/dashboard/CategorizationStats.tsx`):

```typescript
import { Card } from '@/components/ui/card';
import { useEffect, useState } from 'react';

export function CategorizationStats() {
  const [stats, setStats] = useState(null);
  const [costs, setCosts] = useState(null);

  useEffect(() => {
    fetch('http://localhost:8000/categorization/stats')
      .then(res => res.json())
      .then(setStats);

    fetch('http://localhost:8000/categorization/costs/monthly')
      .then(res => res.json())
      .then(setCosts);
  }, []);

  if (!stats || !costs) return null;

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Categorization Performance</h3>

      <div className="space-y-3">
        <div className="flex justify-between">
          <span className="text-sm text-gray-600">Cache Hit Rate:</span>
          <span className="font-medium">{stats.cache_hit_rate}</span>
        </div>

        <div className="flex justify-between">
          <span className="text-sm text-gray-600">AI API Usage:</span>
          <span className="font-medium">{stats.ntropy_usage_rate}</span>
        </div>

        <div className="flex justify-between">
          <span className="text-sm text-gray-600">This Month Cost:</span>
          <span className="font-medium text-green-600">
            ${costs.estimated_cost}
          </span>
        </div>

        <div className="flex justify-between text-xs text-gray-500">
          <span>Ntropy Calls:</span>
          <span>{costs.ntropy_calls}</span>
        </div>
      </div>
    </Card>
  );
}
```

### Deliverables
- ✅ Unified categorization service with 5-layer cascade
- ✅ Automatic model retraining pipeline
- ✅ Cost tracking and monitoring
- ✅ 90%+ cache hit rate after 1 month
- ✅ <5% transactions requiring Ntropy API

### Expected Monthly Costs

| Month | Transactions | Ntropy Calls | Cost |
|-------|--------------|--------------|------|
| 1 | 10,000 | 3,000 (30%) | $60 |
| 2 | 10,000 | 1,000 (10%) | $20 |
| 3 | 10,000 | 500 (5%) | $10 |
| 6+ | 10,000 | 200 (2%) | $4 |

**At 100k transactions/month:** ~$40/month (vs. $2,000+ with API-only)

---

## Success Metrics

### Accuracy Targets
- **Transfer Detection**: 99% accuracy (rule-based, very reliable)
- **Common Merchants**: 95% accuracy (cache + rules)
- **BERT Model**: 80-85% accuracy
- **Overall System**: 90%+ accuracy

### Performance Targets
- **Average Latency**: <100ms per transaction
- **Cache Hit Rate**: >80% after 1 month
- **Ntropy API Usage**: <5% of transactions

### Cost Targets
- **Month 1**: <$100 (testing and training)
- **Month 3**: <$20 (optimized hybrid)
- **Month 6+**: <$10 (mature cache)

---

## Maintenance & Operations

### Monthly Tasks
1. Review categorization accuracy
2. Retrain BERT model with new Ntropy examples
3. Add new merchant patterns to rule-based system
4. Monitor Ntropy API costs

### Quarterly Tasks
1. Audit transfer detection accuracy
2. Update category taxonomy if needed
3. Optimize BERT model hyperparameters
4. Review cost vs. accuracy tradeoff

### Annual Tasks
1. Consider upgrading to larger language model
2. Evaluate new categorization APIs
3. Review and update merchant pattern database

---

## Rollback Plan

If issues arise, each phase can be rolled back:

**Phase 1 → Phase 0**: Remove transfer detection, continue with Teller categories
**Phase 2 → Phase 1**: Disable BERT model, use Ntropy only
**Phase 3 → Phase 2**: Disable hybrid system, use BERT only

All changes are backward-compatible with database schema.

---

## Future Enhancements

### Potential Additions
1. **Merchant Logo Database**: Enrich UI with brand logos
2. **Recurring Transaction Detection**: Auto-categorize subscriptions
3. **Budget Predictions**: ML model to forecast spending
4. **Anomaly Detection**: Flag unusual transactions
5. **Custom Categories**: Let users define their own categories
6. **Receipt OCR**: Extract data from receipt images
7. **Multi-Currency Support**: International transaction handling

### Advanced ML Features
- **GPT-4 Integration**: For complex transaction descriptions
- **User Feedback Loop**: Learn from user corrections
- **Cross-Account Pattern Recognition**: Identify shared merchants across users
- **Time-Series Analysis**: Detect spending pattern changes

---

## Technical Stack Summary

### Backend Services
- **Transfer Detection**: Rule-based system (Python)
- **Merchant Patterns**: Keyword matching (Python)
- **BERT Model**: HuggingFace Transformers (PyTorch)
- **Ntropy API**: HTTP client (httpx)
- **Database**: SQLite with SQLAlchemy ORM

### ML Infrastructure
- **Model**: BERT-base-uncased (110M parameters)
- **Training**: HuggingFace Trainer API
- **Inference**: PyTorch with in-memory caching
- **Storage**: ~400MB per model version

### Dependencies
```
transformers==4.35.0
torch==2.1.0
scikit-learn==1.3.0
pandas==2.1.0
httpx==0.25.0
```

### Infrastructure Requirements
- **CPU**: 2+ cores (4+ recommended for training)
- **RAM**: 4GB minimum (8GB+ for training)
- **Storage**: 2GB for models and training data
- **Network**: Stable internet for Ntropy API calls

---

## Conclusion

This phased approach provides:

1. **Quick wins** (Phase 1): Fix transfer issue immediately with Ntropy
2. **Independence** (Phase 2): Build proprietary ML capability
3. **Optimization** (Phase 3): Minimize costs while maintaining accuracy

**Total Development Time**: ~12 weeks
**Final Operating Cost**: <$50/month for 100k transactions
**Accuracy**: 90%+ overall

The hybrid system ensures you're never locked into expensive API pricing while still benefiting from state-of-the-art categorization for edge cases.
