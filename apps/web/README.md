# Pace Web Dashboard (`apps/web`)

Next.js 14 (App Router) web dashboard for real-time LLM cost analytics, telemetry exploration, budget alert configuration, and pricing calculations.

## Architecture Overview

The web dashboard is built using standard React/Next.js client and server components:

- **Framework**: Next.js 14 App Router
- **Styling**: Tailwind CSS with custom Pace dark design system tokens (`pace-bg`, `pace-surface`, `pace-lime`, `pace-cyan`, `pace-coral`, `pace-border`)
- **State Management**: React Context API (`ProjectContext`) for global project selection and API token state
- **Icons**: Lucide React icons

## Folder Structure

```
apps/web/
├── src/
│   ├── app/
│   │   ├── (auth)/         # Sign-in and authentication pages
│   │   └── (dashboard)/    # Analytics pages (explorer, budgets, live-tail, pricing, quickstart)
│   ├── components/         # Reusable UI components (MetricCard, ApiKeyModal, Navbar, Sidebar)
│   ├── context/            # React context providers (ProjectContext)
│   └── lib/                # API wrapper, currency formatters, and utility functions
├── public/                 # Static assets
├── tailwind.config.js      # Custom Pace design theme configuration
├── tsconfig.json           # TypeScript configuration
└── package.json            # Scripts and dependencies
```

## Dashboard Routes

- `/` - Main Analytics Overview Dashboard (timeseries, cost breakdown, p95 latencies)
- `/explorer` - Telemetry Event Explorer with filtering by provider, model, latency, and error status
- `/live-tail` - Real-time SSE streaming telemetry log feed
- `/budgets` - Project cost budgets and visual breach alerts
- `/pricing` - Interactive LLM cost calculator comparing OpenAI vs Anthropic models
- `/quickstart` - SDK setup instructions and copyable code snippets for Python, TypeScript, and PHP
- `/settings` - API Key management and project configuration

## Development Scripts

```bash
# Typecheck TypeScript definitions
npm run typecheck

# Start local Next.js development server
npm run dev

# Build production distribution bundle
npm run build
```

## Environment Variables

- `NEXT_PUBLIC_API_URL` (default: `http://localhost:8000/v1`): Base API URL for backend requests.
