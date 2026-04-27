'use client';

import Link from 'next/link';
import { useState, useCallback } from 'react';

// --- Reusable Components ---

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 hover:shadow-lg hover:-translate-y-1 transition-all duration-200">
      <div className="w-12 h-12 bg-slate-100 rounded-xl flex items-center justify-center mb-4">
        {icon}
      </div>
      <h3 className="font-semibold text-slate-900 mb-2">{title}</h3>
      <p className="text-sm text-slate-600 leading-relaxed">{description}</p>
    </div>
  );
}

function EnrichmentStep({ label, before, after }: { label: string; before: string; after: string }) {
  return (
    <div className="bg-slate-800 rounded-lg p-4">
      <div className="text-xs text-slate-500 font-mono mb-2">{label}</div>
      <div className="flex items-center gap-3">
        <span className="text-slate-400 text-sm font-mono line-through">{before}</span>
        <svg className="w-4 h-4 text-emerald-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
        </svg>
        <span className="text-emerald-400 text-sm font-mono">{after}</span>
      </div>
    </div>
  );
}

// --- Spending Chart ---

const chartData = [
  { month: 'Sep', amount: 3240 },
  { month: 'Oct', amount: 2890 },
  { month: 'Nov', amount: 3450 },
  { month: 'Dec', amount: 4120 },
  { month: 'Jan', amount: 3180 },
  { month: 'Feb', amount: 2760 },
];

function SpendingChart() {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const width = 560;
  const height = 220;
  const padX = 40;
  const padY = 30;
  const padBottom = 32;
  const chartW = width - padX * 2;
  const chartH = height - padY - padBottom;

  const maxVal = Math.max(...chartData.map(d => d.amount));
  const minVal = Math.min(...chartData.map(d => d.amount)) * 0.85;
  const range = maxVal - minVal;

  const points = chartData.map((d, i) => ({
    x: padX + (i / (chartData.length - 1)) * chartW,
    y: padY + chartH - ((d.amount - minVal) / range) * chartH,
  }));

  // Smooth curve through points
  const pathD = points.reduce((acc, p, i) => {
    if (i === 0) return `M ${p.x} ${p.y}`;
    const prev = points[i - 1];
    const cpx = (prev.x + p.x) / 2;
    return `${acc} C ${cpx} ${prev.y}, ${cpx} ${p.y}, ${p.x} ${p.y}`;
  }, '');

  // Area fill path
  const areaD = `${pathD} L ${points[points.length - 1].x} ${padY + chartH} L ${points[0].x} ${padY + chartH} Z`;

  const gridLines = [minVal, minVal + range * 0.33, minVal + range * 0.66, maxVal];

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * width;
    let closest = 0;
    let closestDist = Infinity;
    points.forEach((p, i) => {
      const dist = Math.abs(p.x - mouseX);
      if (dist < closestDist) {
        closestDist = dist;
        closest = i;
      }
    });
    setHoveredIndex(closestDist < 50 ? closest : null);
  }, [points]);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-auto"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setHoveredIndex(null)}
    >
      {/* Grid lines */}
      {gridLines.map((val, i) => {
        const y = padY + chartH - ((val - minVal) / range) * chartH;
        return (
          <g key={i}>
            <line x1={padX} y1={y} x2={width - padX} y2={y} stroke="#e2e8f0" strokeWidth={1} />
            <text x={padX - 6} y={y + 4} textAnchor="end" className="fill-slate-400" fontSize={10}>
              ${(val / 1000).toFixed(1)}k
            </text>
          </g>
        );
      })}

      {/* Month labels */}
      {chartData.map((d, i) => (
        <text key={d.month} x={points[i].x} y={height - 8} textAnchor="middle" className="fill-slate-500" fontSize={11}>
          {d.month}
        </text>
      ))}

      {/* Area fill */}
      <path d={areaD} fill="url(#chartGradient)" />
      <defs>
        <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#10b981" stopOpacity={0.15} />
          <stop offset="100%" stopColor="#10b981" stopOpacity={0.02} />
        </linearGradient>
      </defs>

      {/* Line */}
      <path d={pathD} fill="none" stroke="#10b981" strokeWidth={2.5} strokeLinecap="round" />

      {/* Data points */}
      {points.map((p, i) => (
        <g key={i}>
          <circle
            cx={p.x}
            cy={p.y}
            r={hoveredIndex === i ? 6 : 3.5}
            fill={hoveredIndex === i ? '#10b981' : '#fff'}
            stroke="#10b981"
            strokeWidth={2}
            className="transition-all duration-150"
          />
        </g>
      ))}

      {/* Hover tooltip */}
      {hoveredIndex !== null && (
        <g>
          {/* Vertical line */}
          <line
            x1={points[hoveredIndex].x}
            y1={padY}
            x2={points[hoveredIndex].x}
            y2={padY + chartH}
            stroke="#10b981"
            strokeWidth={1}
            strokeDasharray="4 4"
            opacity={0.4}
          />
          {/* Tooltip background */}
          <rect
            x={points[hoveredIndex].x - 42}
            y={points[hoveredIndex].y - 36}
            width={84}
            height={26}
            rx={6}
            fill="#0f172a"
          />
          {/* Tooltip text */}
          <text
            x={points[hoveredIndex].x}
            y={points[hoveredIndex].y - 19}
            textAnchor="middle"
            className="fill-white font-medium"
            fontSize={12}
          >
            ${chartData[hoveredIndex].amount.toLocaleString()}
          </text>
        </g>
      )}
    </svg>
  );
}

// --- MCP Conversation Demos ---

type AiClient = 'claude' | 'gemini' | 'chatgpt';

const mcpConversations: Record<AiClient, { name: string; messages: { role: 'user' | 'ai'; text: string; tool?: string }[] }> = {
  claude: {
    name: 'Claude',
    messages: [
      { role: 'user', text: 'What\'s my biggest expense category this month?' },
      { role: 'ai', text: '', tool: 'get_spending_summary → { period: "2026-02", group_by: "category" }' },
      { role: 'ai', text: 'Your top category this month is **Dining & Restaurants** at $847, which is 28% of your total spending. That\'s up from $612 last month — a 38% increase. The jump is mostly from 3 visits to Nobu ($340 total). Housing ($1,200) and Transportation ($423) round out the top three.' },
    ],
  },
  gemini: {
    name: 'Gemini',
    messages: [
      { role: 'user', text: 'Am I on track for my savings goals?' },
      { role: 'ai', text: '', tool: 'get_budget_status → { include_goals: true }' },
      { role: 'ai', text: 'You have 2 active goals. **Emergency Fund**: $8,400 of $10,000 (84%) — on track to hit by March 15. **Japan Trip**: $1,800 of $5,000 (36%) — you need to save $457/mo to hit your September deadline. At your current rate ($320/mo), you\'d arrive in December instead.' },
    ],
  },
  chatgpt: {
    name: 'ChatGPT',
    messages: [
      { role: 'user', text: 'How much have I spent on Amazon the last 6 months? Is it trending up?' },
      { role: 'ai', text: '', tool: 'search_transactions → { merchant: "Amazon", days: 180 }' },
      { role: 'ai', text: 'Over the last 6 months you spent **$2,147** across 63 Amazon orders. Monthly trend: Sep $287, Oct $312, Nov $489 (holiday spike), Dec $421, Jan $338, Feb $300. After the Nov-Dec bump, it\'s settling back down. Your trailing 3-month average is $353/mo.' },
    ],
  },
};

const aiClientColors: Record<AiClient, { bg: string; accent: string; dot: string }> = {
  claude: { bg: 'bg-orange-50', accent: 'text-orange-700', dot: 'bg-orange-500' },
  gemini: { bg: 'bg-blue-50', accent: 'text-blue-700', dot: 'bg-blue-500' },
  chatgpt: { bg: 'bg-emerald-50', accent: 'text-emerald-700', dot: 'bg-emerald-500' },
};

// --- Main Page ---

export default function LandingPage() {
  const [mcpTab, setMcpTab] = useState<'claude-desktop' | 'claude-code' | 'cursor'>('claude-desktop');
  const [aiTab, setAiTab] = useState<AiClient>('claude');
  const [copied, setCopied] = useState(false);

  const mcpConfigs = {
    'claude-desktop': `{
  "mcpServers": {
    "ledgi": {
      "command": "npx",
      "args": ["-y", "@ledgi/mcp-server"],
      "env": {
        "LEDGI_API_KEY": "your-api-key"
      }
    }
  }
}`,
    'claude-code': `{
  "mcpServers": {
    "ledgi": {
      "command": "npx",
      "args": ["-y", "@ledgi/mcp-server"],
      "env": {
        "LEDGI_API_KEY": "your-api-key"
      }
    }
  }
}`,
    'cursor': `{
  "mcpServers": {
    "ledgi": {
      "command": "npx",
      "args": ["-y", "@ledgi/mcp-server"],
      "env": {
        "LEDGI_API_KEY": "your-api-key"
      }
    }
  }
}`,
  };

  const copyConfig = () => {
    navigator.clipboard.writeText(mcpConfigs[mcpTab]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const convo = mcpConversations[aiTab];
  const colors = aiClientColors[aiTab];

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-emerald-400 to-cyan-500 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <span className="font-bold text-slate-900">Ledgi</span>
            </div>
            <div className="hidden sm:flex items-center gap-6 text-sm text-slate-600">
              <a href="#features" className="hover:text-slate-900 transition-colors">Features</a>
              <a href="#enrichment" className="hover:text-slate-900 transition-colors">AI Enrichment</a>
              <a href="#mcp" className="hover:text-slate-900 transition-colors">MCP</a>
            </div>
            <div className="flex items-center gap-4">
              <Link href="/login" className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors">
                Log in
              </Link>
              <Link href="/register" className="bg-slate-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-800 transition-colors">
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="py-16 sm:py-24 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full text-sm font-medium mb-6">
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              Now with MCP server support
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-900 mb-6">
              Your finances,{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-cyan-500">
                enriched by AI
              </span>
            </h1>
            <p className="text-lg sm:text-xl text-slate-600 mb-8 leading-relaxed">
              Connect your bank accounts, and let AI do the rest. Automatic categorization, merchant enrichment, anomaly detection, and a conversational agent that actually understands your data. Access it all from the app, the API, or any MCP-compatible client.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link href="/register" className="bg-slate-900 text-white px-6 py-3 rounded-xl text-center font-medium hover:bg-slate-800 hover:-translate-y-0.5 transition-all shadow-lg">
                Get Started Free
              </Link>
              <a href="#mcp" className="border border-slate-200 bg-white text-slate-700 px-6 py-3 rounded-xl text-center font-medium hover:bg-slate-50 transition-colors">
                See MCP Setup
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Dashboard Preview */}
      <section className="pb-16 sm:pb-24 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden">
            {/* Window chrome */}
            <div className="flex items-center gap-2 px-5 py-3 bg-slate-50 border-b border-slate-200">
              <div className="w-3 h-3 bg-rose-400 rounded-full" />
              <div className="w-3 h-3 bg-amber-400 rounded-full" />
              <div className="w-3 h-3 bg-emerald-400 rounded-full" />
              <span className="ml-3 text-xs text-slate-400 font-mono">ledgi.co/dashboard</span>
            </div>
            <div className="p-6 sm:p-8">
              {/* Stats row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-xs text-slate-500 mb-1">Total Balance</p>
                  <p className="text-xl font-bold text-slate-900">$24,831</p>
                  <p className="text-xs text-emerald-600 mt-1">+2.4% from last month</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-xs text-slate-500 mb-1">Monthly Spending</p>
                  <p className="text-xl font-bold text-slate-900">$2,760</p>
                  <p className="text-xs text-emerald-600 mt-1">13% under budget</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-xs text-slate-500 mb-1">Savings Rate</p>
                  <p className="text-xl font-bold text-slate-900">32%</p>
                  <p className="text-xs text-emerald-600 mt-1">Goal: 30%</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-xs text-slate-500 mb-1">Transactions</p>
                  <p className="text-xl font-bold text-slate-900">147</p>
                  <p className="text-xs text-slate-500 mt-1">This month</p>
                </div>
              </div>

              {/* Chart */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-slate-900">Monthly Spending</h3>
                  <span className="text-xs text-slate-400">Hover to explore</span>
                </div>
                <SpendingChart />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Core Finance Features */}
      <section id="features" className="py-16 sm:py-24 px-4 sm:px-6 bg-slate-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold tracking-tight text-slate-900 mb-4">All the fundamentals, done right</h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Everything you expect from a finance app. Multi-account aggregation, categorization, budgets, goals, and analytics&mdash;all in one place.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard
              icon={
                <svg className="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
              }
              title="Bank Connections"
              description="Link checking, savings, and credit cards from 7,000+ institutions via Teller. Transactions sync automatically."
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              }
              title="Spending Analytics"
              description="Category breakdowns, merchant rankings, daily timelines, and monthly trend charts. See where your money goes."
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              }
              title="Budgets"
              description="Set per-category monthly limits. Get warnings at 80% and alerts when you go over. Track progress across accounts."
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              }
              title="Savings Goals"
              description="Define targets with deadlines. Track progress across accounts and see what you need to save each month to stay on track."
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              }
              title="Recurring Detection"
              description="Automatically detects subscriptions and recurring charges. See your committed monthly spend at a glance."
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
              title="Anomaly Detection"
              description="Statistical analysis flags unusual transactions. AI verification reduces false positives so you only see what matters."
            />
          </div>
        </div>
      </section>

      {/* AI Enrichment Pipeline */}
      <section id="enrichment" className="py-16 sm:py-24 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 bg-violet-50 text-violet-700 px-3 py-1 rounded-full text-sm font-medium mb-6">
                AI Enrichment
              </div>
              <h2 className="text-3xl font-bold tracking-tight text-slate-900 mb-4">
                Raw bank data in, clean financial data out
              </h2>
              <p className="text-lg text-slate-600 mb-6 leading-relaxed">
                Banks give you cryptic transaction descriptions like &ldquo;CHECKCARD 0215 AMZN MKTP US&rdquo;. Our multi-stage enrichment pipeline uses Gemini Flash to resolve merchant names, assign categories, detect recurring patterns, and flag anomalies&mdash;automatically, on every transaction.
              </p>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-violet-100 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-violet-600 font-bold text-sm">1</span>
                  </div>
                  <div>
                    <p className="font-semibold text-slate-900">Merchant resolution</p>
                    <p className="text-sm text-slate-600">Maps raw descriptions to clean merchant names using AI + semantic matching against known patterns.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-violet-100 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-violet-600 font-bold text-sm">2</span>
                  </div>
                  <div>
                    <p className="font-semibold text-slate-900">Category classification</p>
                    <p className="text-sm text-slate-600">Assigns granular categories (not just &ldquo;Shopping&rdquo; but &ldquo;Electronics&rdquo;, &ldquo;Groceries&rdquo;, &ldquo;Pet Supplies&rdquo;) based on merchant + amount context.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-violet-100 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-violet-600 font-bold text-sm">3</span>
                  </div>
                  <div>
                    <p className="font-semibold text-slate-900">Pattern detection</p>
                    <p className="text-sm text-slate-600">Identifies recurring charges, income streams, and spending anomalies across your full history.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Enrichment demo */}
            <div className="bg-slate-900 rounded-2xl p-6 space-y-4">
              <div className="text-xs text-slate-400 font-mono mb-2">ENRICHMENT PIPELINE</div>
              <EnrichmentStep label="RAW DESCRIPTION" before="CHECKCARD 0215 AMZN MKTP US" after="Amazon" />
              <EnrichmentStep label="CATEGORY" before="uncategorized" after="Shopping > Electronics" />
              <EnrichmentStep label="RAW DESCRIPTION" before="SQ *BLUE BOTTLE COFFE" after="Blue Bottle Coffee" />
              <EnrichmentStep label="CATEGORY" before="uncategorized" after="Food & Drink > Coffee" />
              <EnrichmentStep label="RAW DESCRIPTION" before="UBER *EATS PENDING" after="Uber Eats" />
              <EnrichmentStep label="PATTERN" before="one-time" after="recurring (3x/week avg)" />
              <div className="mt-4 pt-4 border-t border-slate-700">
                <div className="flex items-center gap-2 text-emerald-400 text-sm">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Processed in &lt;2s per transaction batch
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Agentic Chat */}
      <section className="py-16 sm:py-24 px-4 sm:px-6 bg-slate-50">
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Chat demo */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-xl p-6 order-2 lg:order-1">
              <div className="flex items-center gap-2 mb-4 pb-4 border-b border-slate-100">
                <div className="w-3 h-3 bg-rose-400 rounded-full" />
                <div className="w-3 h-3 bg-amber-400 rounded-full" />
                <div className="w-3 h-3 bg-emerald-400 rounded-full" />
                <span className="ml-2 text-sm text-slate-500">Ledgi Chat</span>
              </div>
              <div className="space-y-4">
                <div className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl px-4 py-2.5 bg-slate-900 text-white">
                    <p className="text-sm">I think I&apos;m spending too much on food delivery. What does the data say?</p>
                  </div>
                </div>
                <div className="flex justify-start">
                  <div className="max-w-[85%] rounded-2xl px-4 py-2.5 bg-slate-100 text-slate-800">
                    <p className="text-sm">Looking at your last 90 days:</p>
                    <div className="mt-2 bg-white rounded-lg p-3 text-xs font-mono space-y-1">
                      <p className="text-slate-500">tool: search_transactions</p>
                      <p className="text-slate-500">category: &quot;Food &amp; Drink &gt; Delivery&quot;</p>
                      <p className="text-emerald-600">Found 34 transactions, $847.23 total</p>
                    </div>
                    <p className="text-sm mt-2">You&apos;ve spent <strong>$847</strong> on delivery in 3 months&mdash;that&apos;s $282/mo, up 35% from Q3. DoorDash ($412) and Uber Eats ($389) are nearly equal. Most orders are weeknight dinners between 7&ndash;9pm. Want me to set a monthly delivery budget alert?</p>
                  </div>
                </div>
                <div className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl px-4 py-2.5 bg-slate-900 text-white">
                    <p className="text-sm">Yeah, alert me at $200/month. And what would I save if I cut it in half?</p>
                  </div>
                </div>
                <div className="flex justify-start">
                  <div className="max-w-[85%] rounded-2xl px-4 py-2.5 bg-slate-100 text-slate-800">
                    <p className="text-sm">Done&mdash;you&apos;ll get an alert at $200. Cutting delivery in half saves ~$1,700/year. That would fully fund your &ldquo;Japan trip&rdquo; goal by October instead of January.</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="order-1 lg:order-2">
              <div className="inline-flex items-center gap-2 bg-cyan-50 text-cyan-700 px-3 py-1 rounded-full text-sm font-medium mb-6">
                Agentic Chat
              </div>
              <h2 className="text-3xl font-bold tracking-tight text-slate-900 mb-4">
                An AI agent that does the work, not just the talking
              </h2>
              <p className="text-lg text-slate-600 mb-6 leading-relaxed">
                This isn&apos;t a chatbot that parrots back your numbers. It&apos;s an agent with tool access to your financial data. It can search transactions, cross-reference categories, calculate trends, and take actions like setting budget alerts&mdash;all from a natural conversation.
              </p>
              <div className="space-y-3">
                <div className="flex items-center gap-3 text-slate-700">
                  <svg className="w-5 h-5 text-emerald-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm">Searches and aggregates across all your accounts</span>
                </div>
                <div className="flex items-center gap-3 text-slate-700">
                  <svg className="w-5 h-5 text-emerald-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm">Multi-step reasoning: compares periods, finds patterns, projects goals</span>
                </div>
                <div className="flex items-center gap-3 text-slate-700">
                  <svg className="w-5 h-5 text-emerald-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm">Takes actions: creates budgets, sets alerts, tags transactions</span>
                </div>
                <div className="flex items-center gap-3 text-slate-700">
                  <svg className="w-5 h-5 text-emerald-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm">Powered by Claude with structured tool use</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* MCP Section */}
      <section id="mcp" className="py-16 sm:py-24 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 bg-amber-50 text-amber-700 px-3 py-1 rounded-full text-sm font-medium mb-6">
              Model Context Protocol
            </div>
            <h2 className="text-3xl font-bold tracking-tight text-slate-900 mb-4">
              Your financial data, in any AI client
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Ledgi exposes your financial data as an MCP server. Paste a config snippet into Claude Desktop, Claude Code, Cursor, or any MCP-compatible client&mdash;and your AI can query your transactions, check budgets, and analyze spending directly.
            </p>
          </div>

          <div className="grid lg:grid-cols-2 gap-8">
            {/* Left: Config snippet */}
            <div>
              <div className="bg-slate-900 rounded-2xl overflow-hidden">
                <div className="flex items-center gap-2 px-6 pt-6 pb-4">
                  {(['claude-desktop', 'claude-code', 'cursor'] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setMcpTab(tab)}
                      className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                        mcpTab === tab ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {tab === 'claude-desktop' ? 'Claude Desktop' : tab === 'claude-code' ? 'Claude Code' : 'Cursor'}
                    </button>
                  ))}
                  <button
                    onClick={copyConfig}
                    className="ml-auto text-sm text-slate-400 hover:text-white transition-colors flex items-center gap-1.5"
                  >
                    {copied ? (
                      <>
                        <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Copied
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        Copy
                      </>
                    )}
                  </button>
                </div>
                <div className="px-6 pb-6">
                  <pre className="text-sm font-mono text-slate-300 bg-slate-800 rounded-lg p-4 overflow-x-auto">
                    {mcpConfigs[mcpTab]}
                  </pre>
                </div>
              </div>

              {/* MCP tools */}
              <div className="mt-6 grid grid-cols-2 gap-3">
                <div className="bg-slate-50 rounded-lg p-3">
                  <div className="font-mono text-xs text-slate-900 mb-0.5">search_transactions</div>
                  <p className="text-xs text-slate-500">Merchant, category, amount, date range</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3">
                  <div className="font-mono text-xs text-slate-900 mb-0.5">get_spending_summary</div>
                  <p className="text-xs text-slate-500">Aggregated spending by category or merchant</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3">
                  <div className="font-mono text-xs text-slate-900 mb-0.5">get_account_balances</div>
                  <p className="text-xs text-slate-500">Balances across all connected accounts</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3">
                  <div className="font-mono text-xs text-slate-900 mb-0.5">get_budget_status</div>
                  <p className="text-xs text-slate-500">Budget progress and projections</p>
                </div>
              </div>
            </div>

            {/* Right: AI conversation demos */}
            <div>
              <div className="bg-white rounded-2xl border border-slate-200 shadow-lg overflow-hidden">
                {/* AI client tabs */}
                <div className="flex items-center gap-1 px-4 pt-4 pb-3 border-b border-slate-100">
                  {(['claude', 'gemini', 'chatgpt'] as const).map((client) => {
                    const c = aiClientColors[client];
                    const isActive = aiTab === client;
                    return (
                      <button
                        key={client}
                        onClick={() => setAiTab(client)}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                          isActive
                            ? `${c.bg} ${c.accent}`
                            : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        <span className={`w-2 h-2 rounded-full ${isActive ? c.dot : 'bg-slate-300'}`} />
                        {mcpConversations[client].name}
                      </button>
                    );
                  })}
                </div>

                {/* Conversation */}
                <div className="p-5 space-y-4 min-h-[340px]">
                  {convo.messages.map((msg, i) => (
                    <div key={`${aiTab}-${i}`}>
                      {msg.role === 'user' ? (
                        <div className="flex justify-end">
                          <div className="max-w-[85%] rounded-2xl px-4 py-2.5 bg-slate-900 text-white">
                            <p className="text-sm">{msg.text}</p>
                          </div>
                        </div>
                      ) : msg.tool ? (
                        <div className="flex justify-start">
                          <div className={`rounded-lg px-3 py-2 text-xs font-mono ${colors.bg} ${colors.accent} border border-current/10`}>
                            <span className="opacity-60">mcp:</span> {msg.tool}
                          </div>
                        </div>
                      ) : (
                        <div className="flex justify-start">
                          <div className="max-w-[90%] rounded-2xl px-4 py-2.5 bg-slate-50 text-slate-800">
                            <p className="text-sm leading-relaxed" dangerouslySetInnerHTML={{ __html: msg.text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Footer hint */}
                <div className="px-5 py-3 border-t border-slate-100 bg-slate-50">
                  <p className="text-xs text-slate-400 text-center">
                    Same Ledgi MCP tools, any AI model. Switch tabs to see different clients.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 text-center">
            <p className="text-sm text-slate-500">
              Generate an API key in <Link href="/settings" className="text-emerald-600 hover:text-emerald-700 underline">Settings</Link>, paste the config, and start asking your AI about your finances.
            </p>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-16 sm:py-24 px-4 sm:px-6 bg-slate-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold tracking-tight text-slate-900 mb-4">Three minutes to set up</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-12 h-12 bg-slate-900 text-white rounded-full flex items-center justify-center font-bold text-lg mx-auto mb-4">1</div>
              <h3 className="font-semibold text-slate-900 mb-2">Connect your banks</h3>
              <p className="text-sm text-slate-600">Link accounts through Teller&apos;s secure bank connection. No credentials stored on our servers.</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-slate-900 text-white rounded-full flex items-center justify-center font-bold text-lg mx-auto mb-4">2</div>
              <h3 className="font-semibold text-slate-900 mb-2">AI enriches your data</h3>
              <p className="text-sm text-slate-600">Transactions are automatically categorized, merchants resolved, and patterns detected.</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-slate-900 text-white rounded-full flex items-center justify-center font-bold text-lg mx-auto mb-4">3</div>
              <h3 className="font-semibold text-slate-900 mb-2">Ask questions, anywhere</h3>
              <p className="text-sm text-slate-600">Use the dashboard, chat in the app, call the API, or connect via MCP to your favorite AI client.</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 sm:py-24 px-4 sm:px-6 bg-slate-900">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-6">
            Stop staring at spreadsheets.{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">
              Ask your data.
            </span>
          </h2>
          <p className="text-lg text-slate-300 mb-8">
            Connect your banks. Let AI enrich your transactions. Query from anywhere.
          </p>
          <Link href="/register" className="inline-flex bg-white text-slate-900 px-8 py-4 rounded-xl font-semibold hover:bg-slate-100 hover:-translate-y-0.5 transition-all shadow-lg">
            Get Started Free
          </Link>
          <p className="text-sm text-slate-400 mt-4">No credit card required.</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-4 sm:px-6 border-t border-slate-200">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-emerald-400 to-cyan-500 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <span className="font-bold text-slate-900">Ledgi</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-slate-500">
              <Link href="/privacy" className="hover:text-slate-700 transition-colors">Privacy</Link>
              <Link href="/terms" className="hover:text-slate-700 transition-colors">Terms</Link>
              <a href="mailto:support@example.com" className="hover:text-slate-700 transition-colors">Contact</a>
            </div>
          </div>
          <div className="mt-8 text-center text-sm text-slate-400">
            Bank connections powered by Teller. AI powered by Claude &amp; Gemini.
          </div>
        </div>
      </footer>
    </div>
  );
}
