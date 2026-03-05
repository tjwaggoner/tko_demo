"""Generate mock fraud detection datasets and upload to Unity Catalog."""
import csv
import random
import os
from datetime import datetime, timedelta

random.seed(42)

MERCHANTS = [
    ("Amazon", "Online Retail"), ("Walmart", "Retail"), ("Best Buy", "Electronics"),
    ("Shell Gas", "Gas Station"), ("Starbucks", "Food & Drink"), ("Target", "Retail"),
    ("Home Depot", "Home Improvement"), ("CVS Pharmacy", "Pharmacy"),
    ("Uber", "Transportation"), ("Netflix", "Digital Services"),
    ("Wire Transfer - Cayman Islands", "Wire Transfer"), ("Wire Transfer - Nigeria", "Wire Transfer"),
    ("Wire Transfer - Switzerland", "Wire Transfer"), ("ATM Withdrawal - Foreign", "ATM"),
    ("Crypto Exchange XYZ", "Cryptocurrency"), ("Online Casino Royal", "Gambling"),
    ("Luxury Watches Inc", "Luxury Goods"), ("High-End Electronics Ltd", "Electronics"),
]

CITIES = ["New York", "Los Angeles", "Chicago", "Houston", "Miami", "Seattle", "Denver", "Atlanta", "Boston", "Dallas"]
CHANNELS = ["mobile", "web", "branch", "atm"]
FLAG_REASONS = ["velocity_spike", "geo_anomaly", "amount_threshold", "device_mismatch", "mfa_change", "new_merchant", "cross_channel"]

def generate_transactions(n=2000):
    rows = []
    base_time = datetime(2026, 3, 4, 8, 0, 0)
    accounts = [f"ACCT-{i:05d}" for i in range(1, 201)]

    for i in range(n):
        acct = random.choice(accounts)
        is_fraud = random.random() < 0.12
        merchant, category = random.choice(MERCHANTS[:10]) if not is_fraud else random.choice(MERCHANTS[10:])
        amount = round(random.uniform(5, 500), 2) if not is_fraud else round(random.uniform(2000, 50000), 2)
        channel = random.choice(CHANNELS)
        city = random.choice(CITIES)
        ts = base_time + timedelta(minutes=random.randint(0, 1440))
        is_flagged = is_fraud or (random.random() < 0.05)
        risk_score = round(random.uniform(0.7, 0.99), 3) if is_fraud else round(random.uniform(0.01, 0.45), 3)

        rows.append({
            "txn_id": f"TXN-{i+1:06d}",
            "account_id": acct,
            "amount": amount,
            "merchant": merchant,
            "category": category,
            "timestamp": ts.isoformat(),
            "channel": channel,
            "location": city,
            "is_flagged": is_flagged,
            "risk_score": risk_score,
            "flag_reason": random.choice(FLAG_REASONS) if is_flagged else "",
        })
    return rows

def generate_login_logs(n=1500):
    rows = []
    base_time = datetime(2026, 3, 4, 6, 0, 0)
    accounts = [f"ACCT-{i:05d}" for i in range(1, 201)]

    for i in range(n):
        acct = random.choice(accounts)
        suspicious = random.random() < 0.08
        ts = base_time + timedelta(minutes=random.randint(0, 1440))
        ip_prefix = f"{random.randint(1,255)}.{random.randint(0,255)}"
        ip = f"{ip_prefix}.{random.randint(0,255)}.{random.randint(1,254)}"
        device = f"DEV-{random.randint(1000,9999)}" if not suspicious else f"DEV-NEW-{random.randint(10000,99999)}"
        geo = random.choice(CITIES) if not suspicious else random.choice(["Lagos", "Moscow", "Bucharest", "Shenzhen", "Unknown"])

        rows.append({
            "session_id": f"SESS-{i+1:06d}",
            "account_id": acct,
            "ip_address": ip,
            "device_fingerprint": device,
            "login_time": ts.isoformat(),
            "mfa_changed": suspicious and random.random() < 0.4,
            "geo_location": geo,
            "login_success": True,
            "failed_attempts_prior": random.randint(3, 10) if suspicious else random.randint(0, 1),
        })
    return rows

def write_csv(rows, filename):
    path = os.path.join(os.path.dirname(__file__), "..", "data", filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {path}")
    return path

if __name__ == "__main__":
    txns = generate_transactions(2000)
    logins = generate_login_logs(1500)
    write_csv(txns, "transactions.csv")
    write_csv(logins, "login_logs.csv")
    print("Done generating mock data!")
