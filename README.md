# FinTrack - Personal Finance Dashboard

A personal finance tracking application that connects to your bank accounts via Teller API and provides spending insights.

## Features

- **Connect multiple bank accounts** via Teller Connect
- **Spending breakdown** by category (pie chart)
- **Top merchants** analysis
- **Period comparison** (this month vs last month)
- **Income vs expenses** tracking
- **Savings rate** calculation

## Tech Stack

- **Backend**: Python + FastAPI
- **Frontend**: Next.js + Tremor (charts) + Tailwind CSS
- **Database**: SQLite (local)
- **Banking API**: Teller.io

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python run.py
```

Backend will be running at http://localhost:8000

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will be running at http://localhost:3000

### 3. Connect a Bank Account

1. Open http://localhost:3000
2. Click "Connect Bank Account"
3. In **sandbox mode**, use:
   - Username: `username`
   - Password: `password`
4. Select accounts to connect
5. View your dashboard!

## Project Structure

```
financeplanning/
├── backend/
│   ├── app/
│   │   ├── core/           # Config, database
│   │   ├── models/         # SQLAlchemy models
│   │   ├── routers/        # API endpoints
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Teller API service
│   │   └── main.py         # FastAPI app
│   ├── certificate.pem     # Teller certificate
│   ├── private_key.pem     # Teller private key
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js pages
│   │   ├── components/     # React components
│   │   └── lib/            # API client, utilities
│   └── package.json
└── README.md
```

## API Endpoints

### Accounts
- `GET /accounts/` - List all connected accounts
- `GET /accounts/summary/balances` - Get balance summary

### Transactions
- `GET /transactions/` - List transactions (with filters)
- `GET /transactions/recent` - Get recent transactions
- `GET /transactions/search?q=...` - Search transactions

### Analytics
- `GET /analytics/spending/by-category` - Spending breakdown by category
- `GET /analytics/spending/by-merchant` - Top merchants
- `GET /analytics/spending/trends` - Spending over time
- `GET /analytics/comparison` - Compare periods
- `GET /analytics/income-expenses` - Income vs expenses

### Teller Connect
- `POST /teller/connect` - Save new bank connection
- `POST /teller/sync/{institution_id}` - Sync transactions
- `DELETE /teller/disconnect/{institution_id}` - Disconnect bank

## Environment Variables

### Backend (.env)
```
TELLER_APP_ID=app_pn55bmnf8k4papve7o000
TELLER_CERT_PATH=./certificate.pem
TELLER_KEY_PATH=./private_key.pem
TELLER_ENV=sandbox
DATABASE_URL=sqlite:///./fintrack.db
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_TELLER_APP_ID=app_pn55bmnf8k4papve7o000
NEXT_PUBLIC_TELLER_ENV=sandbox
```

## Teller Environments

- **sandbox**: Test with fake data (username/password)
- **development**: Test with real bank accounts (your own)
- **production**: For real users

## Supported Banks (via Teller)

- Capital One ✅
- Chase ✅
- Bank of America ✅
- Wells Fargo ✅
- American Express ✅
- 7,000+ more institutions

**Note**: Discover is NOT supported by Teller. Consider adding Plaid integration for Discover support in the future.

## Future Enhancements

- [ ] Add Plaid integration for Discover
- [ ] AI chat interface for natural language queries
- [ ] Savings goals tracking
- [ ] Budget alerts
- [ ] CSV export
- [ ] Mobile app (React Native)
