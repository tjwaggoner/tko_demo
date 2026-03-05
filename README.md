# TKO Brick-Con FY27: Agentic Fraud Triage Demo

**Live App:** https://tko-fraud-triage-1444828305810485.aws.databricksapps.com

## The 30-Second Version

1. Claude Code read the Brick-Con use case doc and Slack channel context, then built everything from a single prompt.
2. Generated 2,000 realistic mock banking transactions and 1,500 login events with fraud patterns baked in.
3. Created a Unity Catalog catalog, schema, Volume, and three Delta tables — all via Databricks CLI in seconds.
4. Built and deployed a full-stack Databricks App (FastAPI + JS frontend) with a live fraud queue, AI-powered risk explanations via Foundation Model API, and one-click Block/Clear/Escalate actions.
5. Zero to deployed in ~10 minutes using Claude Code (Opus 4.6), FE Vibe skills, and MCP integrations — no manual coding.

## What It Does

A real-time fraud triage application for banking investigators. Flagged transactions are displayed in a priority queue sorted by risk score. Analysts can:

- View flagged transactions with risk scores, amounts, merchants, and flag reasons
- Click **AI Explain** to get a plain-English risk assessment from the Foundation Model API
- Take action: **Block**, **Clear**, or **Escalate** transactions
- Track review progress with live session stats

## Databricks Features Showcased

| Feature | How It's Used |
|---|---|
| **Unity Catalog** | `twaggoner_financial_security` catalog with `fraud_detection` schema, managed Volume for raw CSVs |
| **Delta Tables** | `transactions` (2,000 rows, 320 flagged), `login_logs` (1,500 rows), `triage_actions` (write-back) |
| **Databricks SQL** | Serverless Starter Warehouse (`e9b34f7a2e4b0561`) for all queries |
| **Databricks Apps** | FastAPI backend + inline HTML/JS frontend deployed as a Databricks App |
| **Foundation Model API** | `databricks-claude-sonnet-4` for AI-powered risk explanations via OpenAI-compatible endpoint |
| **Unity Catalog Volumes** | `source_data` volume stores raw CSV files for data lineage |

## AI Tools & Skills Used During Build

### Claude Code Skills (FE Vibe / AI Dev Kit)
- **`fe-databricks-tools:databricks-authentication`** — Verified e2-field workspace OAuth
- **`fe-databricks-tools:databricks-data-generation`** — Informed mock data generation patterns (transactions, login logs)
- **`fe-workflows:slack-discovery-agent`** — Retrieved context from `#ext-tko-amer-fy27` Slack channel
- **`fe-google-tools:google-drive`** — Read the TKO Brick-Con Brief Google Doc for use case requirements

### Claude Code MCP Servers
- **Google MCP** — Extracted use case requirements from the shared Google Doc
- **Slack MCP** — Pulled recent messages from the TKO channel for event context

### Databricks CLI
- `databricks catalogs create` — Created Unity Catalog catalog
- `databricks schemas create` — Created fraud_detection schema
- `databricks volumes create` — Created managed Volume
- `databricks fs cp` — Uploaded CSV data to Volume
- `databricks api post /api/2.0/sql/statements` — Created Delta tables via SQL
- `databricks apps create` / `deploy` — Created and deployed the app
- `databricks workspace import` — Uploaded source code to workspace

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Databricks App                        │
│              (FastAPI + HTML/JS Frontend)                │
│                                                         │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Fraud    │  │ AI Explain   │  │ Triage Actions    │  │
│  │ Queue UI │  │ (FMAPI)      │  │ (Block/Clear/Esc) │  │
│  └────┬─────┘  └──────┬───────┘  └────────┬──────────┘  │
│       │               │                   │              │
└───────┼───────────────┼───────────────────┼──────────────┘
        │               │                   │
        ▼               ▼                   ▼
┌──────────────┐ ┌─────────────┐  ┌─────────────────────┐
│ Databricks   │ │ Foundation  │  │ Delta Table         │
│ SQL Warehouse│ │ Model API   │  │ triage_actions      │
│ (Serverless) │ │ (Claude     │  │ (MERGE write-back)  │
│              │ │  Sonnet)    │  │                     │
└──────┬───────┘ └─────────────┘  └─────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Unity Catalog                        │
│ twaggoner_financial_security         │
│  └─ fraud_detection                  │
│      ├─ transactions (2,000 rows)    │
│      ├─ login_logs (1,500 rows)      │
│      ├─ triage_actions               │
│      └─ [Volume] source_data/        │
│           ├─ transactions.csv        │
│           └─ login_logs.csv          │
└──────────────────────────────────────┘
```

## Mock Data Summary

**Transactions** — 2,000 banking transactions with ~12% fraud rate
- Legitimate: everyday merchants (Amazon, Starbucks, Shell Gas) with $5–$500 amounts
- Suspicious: wire transfers (Cayman Islands, Nigeria), crypto exchanges, luxury goods with $2,000–$50,000 amounts
- Flag reasons: velocity_spike, geo_anomaly, amount_threshold, device_mismatch, mfa_change, new_merchant, cross_channel

**Login Logs** — 1,500 login events with ~8% suspicious activity
- Suspicious logins: new device fingerprints, foreign geolocations (Lagos, Moscow, Bucharest), MFA changes, high failed attempt counts

## Project Structure

```
tko_demo/
├── app.py              # FastAPI backend + HTML frontend
├── app.yaml            # Databricks App config
├── databricks.yml      # Bundle config (e2-field workspace)
├── requirements.txt    # Python dependencies
├── README.md
├── data/
│   ├── transactions.csv
│   └── login_logs.csv
└── scripts/
    └── generate_data.py  # Mock data generator
```

## Built With

- **Claude Code (Opus 4.6)** — End-to-end build orchestration
- **Databricks E2 Field Eng workspace** — Runtime environment
- **FastAPI + Uvicorn** — App backend
- **Databricks SDK** — SQL execution, workspace client
- **OpenAI SDK** — Foundation Model API integration

## Build Time

~10 minutes from zero to deployed app, fully automated via Claude Code.
