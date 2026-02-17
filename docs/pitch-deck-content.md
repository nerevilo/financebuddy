# Finance Buddy - Pitch Content

## One-Liner
The first personal finance app with an AI that remembers you.

## Elevator Pitch (30 seconds)
Finance Buddy connects to your bank accounts and lets you ask questions about your money in plain English. Unlike other apps that just show charts, our AI actually learns your patterns—it knows you're saving for a house, watches the merchants you care about, and gets smarter over time. Think of it as a financial advisor in your pocket, at a fraction of the cost.

---

## The Problem

### Current finance apps are broken:
- They show charts and numbers, but can't answer simple questions
- Every month you start from zero—no memory of what you care about
- Generic alerts that don't know your situation
- Can't have a conversation or ask follow-ups
- No programmability for power users

### User pain points:
- "My app tells me I spent $500 on dining, but is that good or bad for ME?"
- "I can't just ask 'am I on track for my vacation fund?'"
- "I have to manually check everything—nothing proactive"

---

## The Solution

### Finance Buddy is different:
1. **Conversational AI** - Ask questions in plain English, get real answers
2. **Memory** - Learns your goals, patterns, and preferences over time
3. **Proactive insights** - Alerts that understand your context
4. **API access** - Build your own tools on top of your data

### Key differentiator: The Memory Layer
```
User: "How am I doing?"

Without memory: "What do you mean? Spending? Goals?"

With memory: "Your vacation fund is at 48%. Dining is up 15%.
             Amazon spending is normal this week (you asked me to watch it)."
```

---

## Core Features

| Feature | Description |
|---------|-------------|
| Bank Aggregation | 7,000+ institutions via Teller |
| AI Chat | Natural language queries powered by Claude |
| Spending Analytics | Category breakdowns, merchant analysis, trends |
| Smart Alerts | Statistical + LLM anomaly detection |
| Budget Tracking | Per-category limits with threshold alerts |
| Savings Goals | Target-based goals with progress tracking |
| API Access | Full REST API for developers |

---

## Workflows That Demonstrate Value

### Workflow 1: Conversational Query
```
User: "How much did I spend on Amazon last 3 months?"
     ↓
AI executes: search_transactions(merchant="Amazon", days=90)
     ↓
Response: "You spent $1,247.83 across 47 orders. That's 12% higher
          than your 6-month average. Your biggest purchase was
          AirPods Pro ($189.99) on Jan 15."
```

### Workflow 2: Proactive Insight
```
System detects: Dining spending up 23% from baseline
     ↓
AI generates insight: "Dining is running high this month.
I see 4 new DoorDash orders ($127) you didn't have last month."
     ↓
User action: "Set an alert if dining goes over $400"
     ↓
Memory stored: Alert preference saved for future months
```

### Workflow 3: Goal Tracking
```
User: "How's my vacation fund?"
     ↓
AI retrieves: Goal data + savings rate + timeline
     ↓
Response: "You've saved $2,400 of $5,000 (48%). At your current
          rate of $400/month, you'll hit your goal by August—
          one month ahead of schedule."
```

### Workflow 4: Developer Integration
```python
# Slack bot that checks spending
response = requests.post(
    "https://api.financebuddy.com/llm/tools/check-budget-pace",
    headers={"Authorization": f"Bearer {api_key}"},
    json={"category": "dining"}
)
# Returns: {"spent": 340, "budget": 500, "pace": "on_track"}
```

---

## Competitive Positioning

| Feature | Finance Buddy | Rocket Money | Mint | Copilot |
|---------|---------------|--------------|------|---------|
| Price | $4/mo | $3-12/mo | Free | $10/mo |
| AI Chat | Full agentic | None | None | Basic |
| Memory/Learning | Yes | No | No | No |
| Anomaly Detection | Statistical+LLM | Basic | Basic | None |
| API Access | Yes | No | No | No |
| Bank Coverage | 7,000+ | 7,000+ | 10,000+ | 7,000+ |

### Why we win:
- **vs Rocket Money**: Same basics, half the price, plus AI that works
- **vs Mint**: Privacy-focused, no ads, actual AI capabilities
- **vs Copilot**: API access + memory layer at lower price

---

## The Moat Strategy

### Phase 1: Capture Learning Signals (Now)
- Log user recategorizations → train own model
- Track anomaly feedback → improve detection
- Store chat patterns → understand user intent

### Phase 2: Build Proprietary Intelligence (3-6 months)
- Own merchant database from aggregated data
- Personalized spending predictions
- Category models trained on user corrections

### Phase 3: Network Effects (6-12 months)
- Anonymized benchmarking ("You spend 20% more than similar users")
- Merchant intelligence from crowd
- Developer ecosystem via API

---

## Target Users

### Primary: Tech-Savvy Professionals (25-45)
- Comfortable with AI tools
- Want to build automations
- Value API access
- Will pay for quality

### Secondary: Budget-Conscious Millennials
- Looking for Rocket Money alternative
- Price sensitive
- Want basics done well
- AI is a bonus, not requirement

---

## Technical Architecture (Simplified)

```
┌─────────────────────────────────────┐
│      Next.js Frontend               │
│   (Dashboard, Chat, Analytics)      │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│      FastAPI Backend (Python)       │
│  • Claude for chat (tool-calling)   │
│  • Gemini for insights (free tier)  │
│  • Anomaly detection engine         │
│  • Memory/preference store          │
└────────┬───────────┬───────────┬────┘
         │           │           │
     PostgreSQL   Teller     Claude/
     (Data)      (Banks)     Gemini
```

---

## Business Model

### Pricing Tiers:
| Tier | Price | Features |
|------|-------|----------|
| Free | $0 | 2 bank connections, basic analytics |
| Pro | $4/mo | Unlimited banks, AI chat, budgets, goals |
| API | $9/mo | Everything + API access, webhooks |

### Unit Economics:
- LLM costs: ~$0.15/user/month (Claude Haiku + Gemini free tier)
- Teller costs: ~$0.50/user/month
- Gross margin: ~85% at scale

---

## Traction & Roadmap

### Current Status (Phase 2):
- MVP complete with all core features
- AI chat with tool-calling working
- Anomaly detection operational
- API key management in place

### Next 6 Months:
- [ ] Memory layer implementation
- [ ] Mobile app (React Native)
- [ ] Plaid integration for broader coverage
- [ ] Spending predictions
- [ ] User benchmarking (beta)

---

## Key Metrics to Track

| Metric | Why It Matters |
|--------|----------------|
| Chat queries/user/week | AI engagement |
| Recategorization rate | Learning signal quality |
| Anomaly review rate | Alert relevance |
| API calls/developer | Platform stickiness |
| Churn at month 3 | True retention |

---

## FAQ for Investors

**Q: Why not just use ChatGPT with a bank export?**
A: No real-time data, no memory, no automation. Users want answers, not to upload CSVs.

**Q: What's the moat?**
A: Memory layer + proprietary models trained on user behavior. Gets better with scale.

**Q: Why Claude over GPT-4?**
A: Better tool-calling, lower cost at scale, Anthropic partnership potential.

**Q: How do you compete with Plaid building this?**
A: Plaid is infrastructure, not consumer. Different business. We could use Plaid.

**Q: What's the path to $1M ARR?**
A: 20,000 Pro users at $4/mo = $960K. Focus on tech-savvy early adopters.

---

## Contact

[Your contact info here]
