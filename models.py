from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from security_utils import shield

db = SQLAlchemy()

# ═══════════════════════════════════════════
#  IDENTITY & ACCESS MANAGEMENT (RBAC)
# ═══════════════════════════════════════════

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)  # Nullable for Google-only users
    role = db.Column(db.String(50), nullable=False)  # Analyst, Auditor, Admin

    # Security Fields
    pass_prefix = db.Column(db.String(2), nullable=True)
    pass_suffix = db.Column(db.String(2), nullable=True)
    google_id = db.Column(db.String(150), unique=True, nullable=True)
    totp_secret = db.Column(db.String(32), nullable=True)
    is_2fa_enabled = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    accounts = db.relationship('Account', backref='analyst', lazy=True, foreign_keys='Account.assigned_analyst_id')

    def __repr__(self):
        return f'<User {self.full_name} - {self.role}>'

# ═══════════════════════════════════════════
#  FINANCIAL DATA ARCHITECTURE
# ═══════════════════════════════════════════

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    _holder_name = db.Column('holder_name', db.String(512), nullable=False)
    account_type = db.Column(db.String(50), default='Savings')  # Savings, Current, Corporate, Investment
    currency_code = db.Column(db.String(3), default='USD') # USD, EUR, GBP, JPY
    balance = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='Active')  # Active, Frozen, Closed, Under Review
    risk_level = db.Column(db.String(20), default='Low')  # Low, Medium, High, Critical
    assigned_analyst_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    transactions = db.relationship('Transaction', backref='account', lazy=True)

    @property
    def holder_name(self):
        return shield.decrypt_data(self._holder_name)

    @holder_name.setter
    def holder_name(self, value):
        self._holder_name = shield.encrypt_data(value)

    def __repr__(self):
        return f'<Account {self.account_number} - {self.account_type}>'

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(30), unique=True, nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    txn_type = db.Column(db.String(20), nullable=False)  # Credit, Debit, Transfer
    source_currency = db.Column(db.String(3), default='USD')
    target_currency = db.Column(db.String(3), default='USD')
    fx_rate_applied = db.Column(db.Float, default=1.0)
    fx_timestamp = db.Column(db.DateTime, nullable=True)
    _description = db.Column('description', db.String(512))
    status = db.Column(db.String(50), default='Completed')  # Completed, Pending, Flagged, Reversed
    flagged = db.Column(db.Boolean, default=False)
    initiated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def description(self):
        return shield.decrypt_data(self._description)

    @description.setter
    def description(self, value):
        self._description = shield.encrypt_data(value)

    def __repr__(self):
        return f'<Transaction {self.transaction_id} - {self.txn_type} ${self.amount}>'

# ═══════════════════════════════════════════
#  AUDIT & COMPLIANCE
# ═══════════════════════════════════════════

class PendingTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(30), unique=True, nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    txn_type = db.Column(db.String(20), nullable=False)  # Credit, Debit, Transfer
    source_currency = db.Column(db.String(3), default='USD')
    target_currency = db.Column(db.String(3), default='USD')
    fx_rate_applied = db.Column(db.Float, default=1.0)
    fx_timestamp = db.Column(db.DateTime, nullable=True)
    _description = db.Column('description', db.String(512))
    status = db.Column(db.String(50), default='pending')  # pending, approved, rejected, expired
    
    # Maker-Checker Attributes
    maker_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    checker_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    maker_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    checker_timestamp = db.Column(db.DateTime, nullable=True)
    crypto_hash = db.Column(db.String(256), nullable=True)
    mfa_verified_at_maker = db.Column(db.String(50), nullable=True)

    @property
    def description(self):
        return shield.decrypt_data(self._description)

    @description.setter
    def description(self, value):
        self._description = shield.encrypt_data(value)

    def __repr__(self):
        return f'<PendingTransaction {self.transaction_id} - Maker: {self.maker_user_id}>'

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50))
    ip_address = db.Column(db.String(45))
    financial_data_accessed = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ExchangeRateCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    base_currency = db.Column(db.String(3), nullable=False)
    target_currency = db.Column(db.String(3), nullable=False)
    rate = db.Column(db.Float, nullable=False)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

class DailySnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    balance = db.Column(db.Float, nullable=False)
