"""Fraud Triage Agent - Live Fraud Queue App (Databricks App)."""
import os
import json
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

app = FastAPI(title="Fraud Triage Agent")

WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "f4040a30fe978741")
CATALOG = "ticket_master"
SCHEMA = "fraud_detection"

def get_ws_client():
    return WorkspaceClient()

def run_sql(statement: str):
    w = get_ws_client()
    resp = w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID,
        statement=statement,
        wait_timeout="30s",
    )
    if resp.status.state != StatementState.SUCCEEDED:
        raise Exception(f"SQL failed: {resp.status.error}")
    columns = [c.name for c in resp.manifest.schema.columns]
    rows = []
    if resp.result and resp.result.data_array:
        for row in resp.result.data_array:
            rows.append(dict(zip(columns, row)))
    return rows

def get_ai_explanation(txn: dict) -> str:
    """Generate AI risk explanation using Foundation Model API."""
    try:
        import openai
        w = get_ws_client()
        token = w.config.authenticate()
        host = w.config.host.rstrip("/")

        client = openai.OpenAI(
            api_key=token(),
            base_url=f"{host}/serving-endpoints",
        )

        prompt = f"""You are a fraud analyst AI. Analyze this transaction and provide a brief (2-3 sentence)
risk assessment explaining why it was flagged.

Transaction Details:
- Amount: ${txn.get('amount', 'N/A')}
- Merchant: {txn.get('merchant', 'N/A')}
- Category: {txn.get('category', 'N/A')}
- Channel: {txn.get('channel', 'N/A')}
- Location: {txn.get('location', 'N/A')}
- Risk Score: {txn.get('risk_score', 'N/A')}
- Flag Reason: {txn.get('flag_reason', 'N/A')}

Provide a concise, professional risk explanation."""

        response = client.chat.completions.create(
            model="databricks-claude-sonnet-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Risk flagged: {txn.get('flag_reason', 'Unknown')} — ${txn.get('amount', '?')} at {txn.get('merchant', '?')} via {txn.get('channel', '?')}. Score: {txn.get('risk_score', '?')}"


@app.get("/api/flagged")
def get_flagged_transactions(limit: int = 50):
    """Get flagged transactions sorted by risk score."""
    rows = run_sql(f"""
        SELECT txn_id, account_id, amount, merchant, category, timestamp,
               channel, location, risk_score, flag_reason
        FROM {CATALOG}.{SCHEMA}.transactions
        WHERE is_flagged = true
        ORDER BY risk_score DESC
        LIMIT {limit}
    """)
    return {"transactions": rows, "count": len(rows)}


@app.get("/api/transaction/{txn_id}/explain")
def explain_transaction(txn_id: str):
    """Get AI-powered risk explanation for a transaction."""
    rows = run_sql(f"""
        SELECT * FROM {CATALOG}.{SCHEMA}.transactions
        WHERE txn_id = '{txn_id}'
    """)
    if not rows:
        return {"error": "Transaction not found"}
    explanation = get_ai_explanation(rows[0])
    return {"txn_id": txn_id, "explanation": explanation}


@app.post("/api/transaction/{txn_id}/action")
async def take_action(txn_id: str, request: Request):
    """Record a triage action (block/clear/escalate)."""
    body = await request.json()
    action = body.get("action", "pending")
    # For the demo, we'll track actions in a simple table
    try:
        run_sql(f"""
            MERGE INTO {CATALOG}.{SCHEMA}.triage_actions AS t
            USING (SELECT '{txn_id}' as txn_id) AS s
            ON t.txn_id = s.txn_id
            WHEN MATCHED THEN UPDATE SET status = '{action}', reviewed_at = current_timestamp()
            WHEN NOT MATCHED THEN INSERT (txn_id, status, reviewed_at)
                VALUES ('{txn_id}', '{action}', current_timestamp())
        """)
    except Exception:
        # Table might not exist yet, create it
        run_sql(f"""
            CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.triage_actions (
                txn_id STRING, status STRING, reviewed_at TIMESTAMP
            )
        """)
        run_sql(f"""
            INSERT INTO {CATALOG}.{SCHEMA}.triage_actions
            VALUES ('{txn_id}', '{action}', current_timestamp())
        """)
    return {"txn_id": txn_id, "action": action, "status": "recorded"}


@app.get("/api/stats")
def get_stats():
    """Get summary stats for the dashboard."""
    flagged = run_sql(f"""
        SELECT COUNT(*) as total_flagged,
               SUM(CAST(amount AS DOUBLE)) as total_amount,
               AVG(CAST(risk_score AS DOUBLE)) as avg_risk
        FROM {CATALOG}.{SCHEMA}.transactions
        WHERE is_flagged = true
    """)
    by_reason = run_sql(f"""
        SELECT flag_reason, COUNT(*) as count
        FROM {CATALOG}.{SCHEMA}.transactions
        WHERE is_flagged = true AND flag_reason != ''
        GROUP BY flag_reason
        ORDER BY count DESC
    """)
    return {"summary": flagged[0] if flagged else {}, "by_reason": by_reason}


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return HTML_PAGE


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fraud Triage Agent - Live Queue</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1117; color: #e0e0e0; }
        .header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 20px 30px; border-bottom: 2px solid #e74c3c; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 24px; color: #fff; }
        .header h1 span { color: #e74c3c; }
        .stats-bar { display: flex; gap: 30px; padding: 15px 30px; background: #1a1a2e; border-bottom: 1px solid #2a2a3e; }
        .stat { text-align: center; }
        .stat-value { font-size: 28px; font-weight: 700; color: #e74c3c; }
        .stat-label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
        .container { max-width: 1400px; margin: 20px auto; padding: 0 20px; }
        .queue-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .queue-header h2 { color: #fff; font-size: 18px; }
        .badge { background: #e74c3c; color: #fff; padding: 3px 10px; border-radius: 12px; font-size: 13px; }
        table { width: 100%; border-collapse: collapse; background: #1a1a2e; border-radius: 8px; overflow: hidden; }
        th { background: #16213e; color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; padding: 12px 15px; text-align: left; }
        td { padding: 12px 15px; border-bottom: 1px solid #2a2a3e; font-size: 14px; }
        tr:hover { background: #1e2a3e; }
        .risk-high { color: #e74c3c; font-weight: 700; }
        .risk-medium { color: #f39c12; font-weight: 600; }
        .risk-low { color: #27ae60; }
        .amount { font-family: 'SF Mono', monospace; font-weight: 600; }
        .amount-high { color: #e74c3c; }
        .btn { padding: 5px 12px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600; margin-right: 4px; transition: all 0.2s; }
        .btn-block { background: #e74c3c; color: #fff; }
        .btn-block:hover { background: #c0392b; }
        .btn-clear { background: #27ae60; color: #fff; }
        .btn-clear:hover { background: #219a52; }
        .btn-escalate { background: #f39c12; color: #fff; }
        .btn-escalate:hover { background: #d68910; }
        .btn-explain { background: #3498db; color: #fff; }
        .btn-explain:hover { background: #2980b9; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .explanation { background: #16213e; padding: 10px 15px; border-left: 3px solid #3498db; margin-top: 8px; border-radius: 4px; font-size: 13px; line-height: 1.5; display: none; }
        .flag-badge { background: #2a2a3e; color: #ccc; padding: 2px 8px; border-radius: 3px; font-size: 11px; }
        .status-blocked { color: #e74c3c; }
        .status-cleared { color: #27ae60; }
        .status-escalated { color: #f39c12; }
        .loading { text-align: center; padding: 40px; color: #888; }
        .refresh-btn { background: #3498db; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; }
    </style>
</head>
<body>
    <div class="header">
        <h1><span>&#9888;</span> Fraud Triage Agent <span>|</span> Live Queue</h1>
        <button class="refresh-btn" onclick="loadData()">Refresh Queue</button>
    </div>
    <div class="stats-bar" id="stats-bar">
        <div class="stat"><div class="stat-value" id="stat-total">--</div><div class="stat-label">Flagged Transactions</div></div>
        <div class="stat"><div class="stat-value" id="stat-amount">--</div><div class="stat-label">Total Amount at Risk</div></div>
        <div class="stat"><div class="stat-value" id="stat-risk">--</div><div class="stat-label">Avg Risk Score</div></div>
        <div class="stat"><div class="stat-value" id="stat-reviewed">0</div><div class="stat-label">Reviewed This Session</div></div>
    </div>
    <div class="container">
        <div class="queue-header">
            <h2>Priority Queue <span class="badge" id="queue-count">Loading...</span></h2>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Risk</th>
                    <th>Transaction</th>
                    <th>Account</th>
                    <th>Amount</th>
                    <th>Merchant</th>
                    <th>Channel</th>
                    <th>Location</th>
                    <th>Flag Reason</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="queue-body">
                <tr><td colspan="9" class="loading">Loading flagged transactions...</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        let reviewedCount = 0;

        async function loadData() {
            try {
                const [txnResp, statsResp] = await Promise.all([
                    fetch('/api/flagged?limit=50'),
                    fetch('/api/stats')
                ]);
                const txnData = await txnResp.json();
                const statsData = await statsResp.json();

                renderStats(statsData);
                renderQueue(txnData.transactions);
            } catch (e) {
                document.getElementById('queue-body').innerHTML =
                    '<tr><td colspan="9" class="loading">Error loading data: ' + e.message + '</td></tr>';
            }
        }

        function renderStats(data) {
            const s = data.summary;
            document.getElementById('stat-total').textContent = Number(s.total_flagged || 0).toLocaleString();
            document.getElementById('stat-amount').textContent = '$' + Number(s.total_amount || 0).toLocaleString(undefined, {maximumFractionDigits: 0});
            document.getElementById('stat-risk').textContent = Number(s.avg_risk || 0).toFixed(3);
        }

        function riskClass(score) {
            const s = parseFloat(score);
            if (s >= 0.7) return 'risk-high';
            if (s >= 0.4) return 'risk-medium';
            return 'risk-low';
        }

        function renderQueue(transactions) {
            const tbody = document.getElementById('queue-body');
            document.getElementById('queue-count').textContent = transactions.length + ' items';

            tbody.innerHTML = transactions.map(t => `
                <tr id="row-${t.txn_id}">
                    <td><span class="${riskClass(t.risk_score)}">${parseFloat(t.risk_score).toFixed(3)}</span></td>
                    <td style="font-family: monospace; font-size: 12px;">${t.txn_id}</td>
                    <td style="font-family: monospace; font-size: 12px;">${t.account_id}</td>
                    <td class="amount ${parseFloat(t.amount) > 5000 ? 'amount-high' : ''}">$${Number(t.amount).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                    <td>${t.merchant}</td>
                    <td>${t.channel}</td>
                    <td>${t.location}</td>
                    <td><span class="flag-badge">${t.flag_reason || '-'}</span></td>
                    <td>
                        <button class="btn btn-explain" onclick="explainTxn('${t.txn_id}')">AI Explain</button>
                        <button class="btn btn-block" onclick="takeAction('${t.txn_id}', 'blocked')">Block</button>
                        <button class="btn btn-clear" onclick="takeAction('${t.txn_id}', 'cleared')">Clear</button>
                        <button class="btn btn-escalate" onclick="takeAction('${t.txn_id}', 'escalated')">Escalate</button>
                        <div class="explanation" id="explain-${t.txn_id}"></div>
                    </td>
                </tr>
            `).join('');
        }

        async function explainTxn(txnId) {
            const el = document.getElementById('explain-' + txnId);
            el.style.display = 'block';
            el.textContent = 'Generating AI explanation...';
            try {
                const resp = await fetch('/api/transaction/' + txnId + '/explain');
                const data = await resp.json();
                el.textContent = data.explanation;
            } catch (e) {
                el.textContent = 'Error generating explanation: ' + e.message;
            }
        }

        async function takeAction(txnId, action) {
            try {
                await fetch('/api/transaction/' + txnId + '/action', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action})
                });
                const row = document.getElementById('row-' + txnId);
                row.style.opacity = '0.4';
                const statusClass = 'status-' + action;
                row.querySelector('td:first-child').innerHTML += '<br><span class="' + statusClass + '">' + action.toUpperCase() + '</span>';
                row.querySelectorAll('.btn').forEach(b => b.disabled = true);
                reviewedCount++;
                document.getElementById('stat-reviewed').textContent = reviewedCount;
            } catch (e) {
                alert('Error: ' + e.message);
            }
        }

        loadData();
    </script>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
