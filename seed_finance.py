from app import app
from models import db, User, Account, Transaction
from werkzeug.security import generate_password_hash
import uuid
from datetime import datetime, timedelta

def seed():
    with app.app_context():
        print("Resetting Finance DB...")
        db.drop_all()
        db.create_all()
        
        # ═══════════════════════════════════════════
        #  USERS
        # ═══════════════════════════════════════════
        
        admin = User(
            full_name="Yenepoya Admin", 
            email="25177@yenepoya.edu.in", 
            password_hash=generate_password_hash("Rai@yenepoya.", method='scrypt'),
            pass_prefix="Ra",
            pass_suffix="a.",
            role="Admin"
        )
        
        analyst = User(
            full_name="Raihana Anzar 2", 
            email="raihanaanzar2@gmail.com", 
            password_hash=generate_password_hash("Rai@yenepoya.", method='scrypt'),
            pass_prefix="Ra",
            pass_suffix="a.",
            role="Analyst"
        )
        
        auditor = User(
            full_name="Raihana Anzar",
            email="raihanaanzar@gmail.com",
            password_hash=generate_password_hash("Rai@yenepoya.", method='scrypt'),
            pass_prefix="Ra",
            pass_suffix="a.",
            role="Auditor"
        )
        
        db.session.add_all([admin, analyst, auditor])
        db.session.commit()
        print(f"  [OK] Requested Users created: Admin (ID:{admin.id}), Analyst (ID:{analyst.id}), Auditor (ID:{auditor.id})")
        
        # ═══════════════════════════════════════════
        #  ACCOUNTS (Encrypted holder names)
        # ═══════════════════════════════════════════
        
        accounts_data = [
            {"number": "VP-ACC-10001", "holder": "Nexus Capital Holdings", "type": "Corporate", "balance": 2450000.00, "risk": "Low", "status": "Active"},
            {"number": "VP-ACC-10002", "holder": "Alpha Retail Partners", "type": "Investment", "balance": 875340.50, "risk": "Medium", "status": "Active"},
            {"number": "VP-ACC-10003", "holder": "Titan Logistics Group", "type": "Current", "balance": 1250000.00, "risk": "Low", "status": "Active"},
            {"number": "VP-ACC-10004", "holder": "Beta Asset Management", "type": "Savings", "balance": 342890.75, "risk": "Low", "status": "Active"},
            {"number": "VP-ACC-10005", "holder": "Sterling Offshore Ltd", "type": "Corporate", "balance": 5600000.00, "risk": "High", "status": "Under Review"},
            {"number": "VP-ACC-10006", "holder": "Gamma Financials", "type": "Savings", "balance": 98500.25, "risk": "Low", "status": "Active"},
            {"number": "VP-ACC-10007", "holder": "Blackstone Ventures Inc", "type": "Investment", "balance": 12750000.00, "risk": "Critical", "status": "Frozen"},
        ]
        
        created_accounts = []
        for acc in accounts_data:
            account = Account(
                account_number=acc["number"],
                holder_name=acc["holder"],
                account_type=acc["type"],
                balance=acc["balance"],
                risk_level=acc["risk"],
                status=acc["status"],
                assigned_analyst_id=analyst.id
            )
            db.session.add(account)
            created_accounts.append(account)
        
        db.session.commit()
        print(f"  [OK] {len(created_accounts)} accounts created")
        
        # ═══════════════════════════════════════════
        #  TRANSACTIONS (Encrypted descriptions)
        # ═══════════════════════════════════════════
        
        transactions_data = [
            {"acc_idx": 0, "amount": 150000.00, "type": "Credit", "desc": "Quarterly dividend deposit from subsidiary", "status": "Completed"},
            {"acc_idx": 0, "amount": 45000.00, "type": "Debit", "desc": "Vendor payment — IT Infrastructure", "status": "Completed"},
            {"acc_idx": 1, "amount": 25000.00, "type": "Credit", "desc": "Monthly investment return", "status": "Completed"},
            {"acc_idx": 2, "amount": 78000.00, "type": "Debit", "desc": "Fleet maintenance contract renewal", "status": "Completed"},
            {"acc_idx": 3, "amount": 5000.00, "type": "Credit", "desc": "Salary deposit — March 2026", "status": "Completed"},
            {"acc_idx": 4, "amount": 750000.00, "type": "Transfer", "desc": "Cross-border wire to Cayman Islands", "status": "Flagged", "flagged": True},
            {"acc_idx": 1, "amount": 120000.00, "type": "Debit", "desc": "Portfolio rebalancing — Equity withdrawal", "status": "Flagged", "flagged": True},
            {"acc_idx": 5, "amount": 2500.00, "type": "Credit", "desc": "Refund — insurance claim #RC-4421", "status": "Completed"},
            {"acc_idx": 2, "amount": 340000.00, "type": "Credit", "desc": "Client payment received — Invoice #INV-2892", "status": "Completed"},
            {"acc_idx": 6, "amount": 2000000.00, "type": "Debit", "desc": "Emergency fund liquidation — Board directive", "status": "Flagged", "flagged": True},
        ]
        
        for i, txn in enumerate(transactions_data):
            transaction = Transaction(
                transaction_id=f"TXN-{uuid.uuid4().hex[:10].upper()}",
                account_id=created_accounts[txn["acc_idx"]].id,
                amount=txn["amount"],
                txn_type=txn["type"],
                description=txn["desc"],
                status=txn["status"],
                flagged=txn.get("flagged", False),
                initiated_by=analyst.id,
                timestamp=datetime.utcnow() - timedelta(hours=i * 8)
            )
            db.session.add(transaction)
        
        db.session.commit()
        print(f"  [OK] {len(transactions_data)} transactions created")
        
        print("\n=======================================")
        print("  Finance Seeding Successful!")
        print("=======================================")
        print("\n  Login Credentials:")
        print("  -------------------------------------")
        print("  Admin:   25177@yenepoya.edu.in   / Rai@yenepoya.")
        print("  Analyst: raihanaanzar2@gmail.com / Rai@yenepoya.")
        print("  Auditor: raihanaanzar@gmail.com  / Rai@yenepoya.")
        print("  -------------------------------------")

if __name__ == "__main__":
    seed()
