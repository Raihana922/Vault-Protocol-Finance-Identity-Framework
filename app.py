from flask import Flask, render_template, redirect, url_for, request, flash, abort, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from models import db, User, Account, Transaction, AuditLog, PendingTransaction, ExchangeRateCache, DailySnapshot
from functools import wraps
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
import pyotp
import qrcode
import io
import base64
import os
import uuid
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FIN_SECRET_KEY', 'vault-protocol-secret-key-789')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance_users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# OAuth Configuration
app.config['GOOGLE_CLIENT_ID'] = os.getenv('FIN_GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('FIN_GOOGLE_CLIENT_SECRET')

db.init_app(app)
csrf = CSRFProtect(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["500 per day", "100 per hour"],
    storage_uri="memory://"
)

# ═══════════════════════════════════════════
#  SECURITY UTILITIES & MIDDLEWARE
# ═══════════════════════════════════════════

def audit_log(action, financial_data=None):
    """Logs critical actions for SOX/PCI-DSS Compliance."""
    new_log = AuditLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        role=current_user.role if current_user.is_authenticated else 'Guest',
        ip_address=request.remote_addr,
        financial_data_accessed=financial_data
    )
    db.session.add(new_log)
    db.session.commit()

@app.before_request
def check_maintenance_mode():
    """Restricts access if system is in maintenance (Admin only)."""
    if app.config.get('MAINTENANCE_MODE') and request.endpoint not in ['login', 'static', 'logout']:
        if current_user.is_authenticated and current_user.role != 'Admin':
            logout_user()
            flash('System is currently undergoing regulatory maintenance. Please try again later.', 'warning')
            return redirect(url_for('login'))

def mfa_reauth_required(f):
    """Requires a fresh 2FA check for high-value financial operations."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('mfa_verified_at'):
            session['pending_reauth_endpoint'] = request.endpoint
            session['pending_reauth_args'] = kwargs
            return redirect(url_for('verify_2fa', reauth=True))
        
        # Check if re-auth is older than 5 minutes
        last_auth = datetime.fromisoformat(session['mfa_verified_at'])
        if datetime.now() - last_auth > timedelta(minutes=5):
            session['pending_reauth_endpoint'] = request.endpoint
            return redirect(url_for('verify_2fa', reauth=True))
            
        return f(*args, **kwargs)
    return decorated_function

def trading_hours_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # [DISABLED FOR TESTING] - Allow testing on weekends and off-hours
        # Admin and Auditor are exempt
        # if current_user.role in ['Admin', 'Auditor']:
        #     return f(*args, **kwargs)
            
        # Mon-Fri (0-4), 09:00 to 17:00 UTC (For demo using UTC)
        # now = datetime.utcnow()
        # if now.weekday() > 4 or now.hour < 9 or now.hour >= 17:
        #     audit_log("OFF_HOURS_ACCESS_ATTEMPT", financial_data=f"Tried accessing {request.endpoint}")
        #     flash('Trading floor is closed. Market hours are Mon-Fri 09:00 - 17:00 UTC.', 'error')
        #     return redirect(url_for('analyst_dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

# Security Headers (Anti-Hack)
csp = {
    'default-src': '\'self\'',
    'script-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        'https://cdn.jsdelivr.net'
    ],
    'style-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        'https://fonts.googleapis.com'
    ],
    'font-src': [
        '\'self\'',
        'https://fonts.gstatic.com'
    ],
    'img-src': ['\'self\'', 'data:'],
    'connect-src': ['\'self\'']
}
Talisman(app, content_security_policy=csp)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

oauth = OAuth(app)
google = oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            # Universal access for Admin
            if current_user.role == 'Admin':
                return f(*args, **kwargs)
            if current_user.role != role:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ═══════════════════════════════════════════
#  AUTHENTICATION ROUTES
# ═══════════════════════════════════════════

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered in the system.', 'error')
            return redirect(url_for('signup'))

        # Prevent unauthorized Admin registration
        if role == 'Admin':
            flash('The Admin role is restricted to pre-authorized personnel.', 'error')
            return redirect(url_for('signup'))

        pass_prefix = None
        pass_suffix = None
        if password:
            padded_pass = (password * 4)[:4]
            if len(password) >= 4:
                pass_prefix = password[:2]
                pass_suffix = password[-2:]
            else:
                pass_prefix = padded_pass[:2]
                pass_suffix = padded_pass[-2:]

        new_user = User(
            full_name=full_name, 
            email=email, 
            password_hash=generate_password_hash(password, method='scrypt'),
            pass_prefix=pass_prefix,
            pass_suffix=pass_suffix,
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        audit_log(f"NEW_ACCOUNT_REGISTERED: {role}")
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Login failed. Check your credentials.', 'error')
            return redirect(url_for('login'))

        # Check for 2FA
        if user.is_2fa_enabled:
            session['pending_2fa_user_id'] = user.id
            return redirect(url_for('verify_2fa'))

        login_user(user)
        session['mfa_verified_at'] = datetime.now().isoformat()
        audit_log("LOGIN_SUCCESS", financial_data=user.full_name)
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
def google_callback():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    if not user_info:
        audit_log("GOOGLE_AUTH_FAILED", financial_data="Guest")
        flash('Google authentication failed. Vault access denied.', 'error')
        return redirect(url_for('login'))
    
    user = User.query.filter_by(google_id=user_info['sub']).first()
    if not user:
        user = User.query.filter_by(email=user_info['email']).first()
        if user:
            user.google_id = user_info['sub']
        else:
            # 🏛️ Institutional Role Mapping (Sticky Identities)
            # Update these email lists with your actual institutional emails
            ADMIN_EMAILS = ['25177@yenepoya.edu.in']
            ANALYST_EMAILS = ['raihanaanzar2@gmail.com']
            AUDITOR_EMAILS = ['raihanaanzar@gmail.com']

            if user_info['email'] in ADMIN_EMAILS:
                assigned_role = 'Admin'
            elif user_info['email'] in ANALYST_EMAILS:
                assigned_role = 'Analyst'
            elif user_info['email'] in AUDITOR_EMAILS:
                assigned_role = 'Auditor'
            else:
                assigned_role = 'Analyst'  # Default role for new users

            user = User(
                full_name=user_info['name'],
                email=user_info['email'],
                google_id=user_info['sub'],
                role=assigned_role
            )
            db.session.add(user)
            flash('Account created via Google!', 'success')
        db.session.commit()
    
    audit_log(f"GOOGLE_LOGIN_SUCCESS: {user.role}", financial_data=user.full_name)

    if user.is_2fa_enabled:
        session['pending_2fa_user_id'] = user.id
        return redirect(url_for('verify_2fa'))

    login_user(user)
    session['mfa_verified_at'] = datetime.now().isoformat()
    return redirect(url_for('dashboard'))

# ═════ PASSWORD RESET PIPELINE ═════

@app.route('/reset-password', endpoint='reset_request', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Identity not found. Access denied.', 'error')
            return redirect(url_for('reset_request'))
        
        session['reset_user_id'] = user.id
        
        if user.is_2fa_enabled:
            return redirect(url_for('reset_mfa'))
        else:
            return redirect(url_for('reset_fallback'))
    return render_template('reset_request.html')

@app.route('/reset/mfa', endpoint='reset_mfa', methods=['GET', 'POST'])
def reset_mfa():
    user_id = session.get('reset_user_id')
    if not user_id:
        return redirect(url_for('reset_request'))
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        otp = request.form.get('otp_code')
        if pyotp.TOTP(user.totp_secret).verify(otp):
            session['reset_authorized'] = True
            return redirect(url_for('reset_new'))
        else:
            flash('Invalid MFA code.', 'error')
    
    return render_template('verify_2fa.html', reauth=True)

@app.route('/reset/fallback', endpoint='reset_fallback', methods=['GET', 'POST'])
def reset_fallback():
    user_id = session.get('reset_user_id')
    if not user_id:
        return redirect(url_for('reset_request'))
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        prefix = request.form.get('prefix')
        suffix = request.form.get('suffix')
        
        match_prefix = user.pass_prefix == prefix if user.pass_prefix else True
        match_suffix = user.pass_suffix == suffix if user.pass_suffix else True
        
        if match_prefix and match_suffix:
            session['reset_authorized'] = True
            return redirect(url_for('reset_new'))
        else:
            flash('Verification failed. Invalid credential fragments.', 'error')
    return render_template('reset_fallback.html')

@app.route('/reset/new-password', endpoint='reset_new', methods=['GET', 'POST'])
def reset_new():
    if not session.get('reset_authorized'):
        return redirect(url_for('reset_request'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('reset_new'))
            
        user_id = session.get('reset_user_id')
        user = User.query.get(user_id)
        user.password_hash = generate_password_hash(password, method='scrypt')
        
        padded_pass = (password * 4)[:4]
        if len(password) >= 4:
            user.pass_prefix = password[:2]
            user.pass_suffix = password[-2:]
        else:
            user.pass_prefix = padded_pass[:2]
            user.pass_suffix = padded_pass[-2:]
            
        db.session.commit()
        session.pop('reset_user_id', None)
        session.pop('reset_authorized', None)
        audit_log("PASSWORD_RESET_COMPLETED", financial_data=user.full_name)
        flash('Vault credentials updated. Protocol accepted.', 'success')
        return redirect(url_for('login'))
        
    return render_template('reset_new.html')

# ═══════════════════════════════════════════
#  TWO-FACTOR AUTHENTICATION (2FA / TOTP)
# ═══════════════════════════════════════════

@app.route('/setup-2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    if request.method == 'POST':
        otp_code = request.form.get('otp_code')
        if not session.get('temp_totp_secret'):
            return redirect(url_for('setup_2fa'))
        
        totp = pyotp.TOTP(session['temp_totp_secret'])
        if totp.verify(otp_code):
            current_user.totp_secret = session['temp_totp_secret']
            current_user.is_2fa_enabled = True
            db.session.commit()
            session.pop('temp_totp_secret')
            audit_log("MFA_ENABLED", financial_data=current_user.full_name)
            flash('2FA has been successfully enabled on your vault account!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid OTP code. Please try again.', 'error')

    secret = pyotp.random_base32()
    session['temp_totp_secret'] = secret
    otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email, 
        issuer_name="Vault Protocol Finance"
    )
    
    img = qrcode.make(otp_uri)
    buf = io.BytesIO()
    img.save(buf)
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    return render_template('setup_2fa.html', qr_code=qr_b64, secret=secret)

@app.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    # If it's a re-auth, current_user is already logged in
    # If it's a first login, pending_2fa_user_id is in session
    target_user = None
    if current_user.is_authenticated:
        target_user = current_user
    elif 'pending_2fa_user_id' in session:
        target_user = User.query.get(session['pending_2fa_user_id'])
    
    if not target_user:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        otp_code = request.form.get('otp_code')
        totp = pyotp.TOTP(target_user.totp_secret)
        if totp.verify(otp_code):
            session['mfa_verified_at'] = datetime.now().isoformat()
            
            # Case 1: Initial Login MFA
            if not current_user.is_authenticated:
                login_user(target_user)
                session.pop('pending_2fa_user_id', None)
            
            # Case 2: Financial Re-Auth
            audit_log("MFA_VERIFIED", financial_data=target_user.full_name)
            flash('Identity Verified. Vault session restored.', 'success')
            endpoint = session.pop('pending_reauth_endpoint', 'dashboard')
            args = session.pop('pending_reauth_args', {})
            return redirect(url_for(endpoint, **args))
        else:
            audit_log("MFA_FAILED")
            flash('Invalid MFA code. Vault access rejected.', 'error')
            
    return render_template('verify_2fa.html', reauth=request.args.get('reauth'))

# ═══════════════════════════════════════════
#  DASHBOARD & ROLE-BASED VIEWS
# ═══════════════════════════════════════════

@app.route('/dashboard')
@login_required
def dashboard():
    audit_log("Accessed Main Dashboard")
    if current_user.role == 'Analyst':
        return redirect(url_for('analyst_dashboard'))
    elif current_user.role == 'Auditor':
        return redirect(url_for('auditor_dashboard'))
    elif current_user.role == 'Admin':
        return redirect(url_for('admin_dashboard'))
    return abort(403)

@app.route('/analyst')
@role_required('Analyst')
def analyst_dashboard():
    accounts = Account.query.filter_by(assigned_analyst_id=current_user.id).all()
    recent_transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(10).all()
    total_balance = sum(a.balance for a in accounts)
    audit_log("Viewed Analyst Portfolio")
    return render_template('analyst_dashboard.html', 
                         accounts=accounts, 
                         transactions=recent_transactions,
                         total_balance=total_balance)

def get_fx_rate(base, target):
    if base == target:
        return 1.0
    
    # Check cache
    cache = ExchangeRateCache.query.filter_by(base_currency=base, target_currency=target).order_by(ExchangeRateCache.fetched_at.desc()).first()
    if cache and cache.expires_at > datetime.utcnow():
        return cache.rate
        
    # Mock External API call
    mock_rates = {
        'USD-EUR': 0.92, 'EUR-USD': 1.09,
        'USD-GBP': 0.79, 'GBP-USD': 1.27,
        'USD-JPY': 150.0, 'JPY-USD': 0.0067,
        'USD-INR': 83.5, 'INR-USD': 0.012
    }
    key = f"{base}-{target}"
    rate = mock_rates.get(key, 1.0)
    
    # Cache it
    new_cache = ExchangeRateCache(
        base_currency=base, target_currency=target, rate=rate,
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    db.session.add(new_cache)
    db.session.commit()
    return rate

@app.route('/analyst/submit_transaction', methods=['POST'])
@role_required('Analyst')
@trading_hours_required
@mfa_reauth_required
def submit_transaction():
    account_id = int(request.form.get('account_id'))
    amount = float(request.form.get('amount'))
    txn_type = request.form.get('txn_type')
    description = request.form.get('description', '')
    target_currency = request.form.get('target_currency', 'USD')
    
    account = Account.query.get_or_404(account_id)
    
    # Cyber Attack Proof: Server-side validation against negative number injection
    if amount <= 0:
        audit_log("THREAT_DETECTED", financial_data="Malicious Negative/Zero Amount Injection Attempt")
        flash("System Error: Invalid volume parameter.", "error")
        return redirect(url_for("analyst_dashboard"))

    if txn_type not in ["Credit", "Debit", "Transfer"]:
        audit_log("THREAT_DETECTED", financial_data="Invalid Transaction Vector Injection")
        flash("System Error: Unknown vector type.", "error")
        return redirect(url_for("analyst_dashboard"))
        
    import hashlib
    
    # Multi-Currency Conversion (Phase 2)
    fx_rate = get_fx_rate(account.currency_code, target_currency)
    converted_amount = amount * fx_rate
    
    # Validate sufficient funds for debit/transfer
    if txn_type in ["Debit", "Transfer"] and account.balance < converted_amount:
        flash(f"Insufficient funds. Required: {converted_amount:.2f} {account.currency_code}", "error")
        return redirect(url_for("analyst_dashboard"))
    
    # Maker-Checker (Phase 1): Reserve funds logically, do not deduct yet.
    tx_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"
    crypto_hash_data = f"{tx_id}{account_id}{amount}{txn_type}{description}".encode('utf-8')
    crypto_hash = hashlib.sha256(crypto_hash_data).hexdigest()

    ptxn = PendingTransaction(
        transaction_id=tx_id,
        account_id=account_id,
        amount=amount,  # Original requested amount
        txn_type=txn_type,
        source_currency=account.currency_code,
        target_currency=target_currency,
        fx_rate_applied=fx_rate,
        fx_timestamp=datetime.utcnow() if fx_rate != 1.0 else None,
        description=description,
        status="pending",
        maker_user_id=current_user.id,
        crypto_hash=crypto_hash,
        mfa_verified_at_maker=session.get('mfa_verified_at')
    )
    
    db.session.add(ptxn)
    db.session.commit()
    audit_log("TRANSACTION_PENDING", financial_data=f"Account {account.account_number}")
    flash(f"Transaction {ptxn.transaction_id} escalated to Checker for Approval.", "success")
    return redirect(url_for("analyst_dashboard"))

@app.route('/auditor')
@role_required('Auditor')
def auditor_dashboard():
    all_transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(50).all()
    flagged_transactions = Transaction.query.filter_by(flagged=True).all()
    pending_transactions = PendingTransaction.query.filter_by(status='pending').order_by(PendingTransaction.maker_timestamp.asc()).all()
    all_accounts = Account.query.all()
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(20).all()
    audit_log("Viewed Auditor Compliance Dashboard")
    return render_template('auditor_dashboard.html', 
                         transactions=all_transactions,
                         flagged=flagged_transactions,
                         pending_transactions=pending_transactions,
                         accounts=all_accounts,
                         logs=logs)

@app.route('/auditor/approve_transaction/<int:ptxn_id>', methods=['POST'])
@role_required('Auditor')
@mfa_reauth_required
def approve_transaction(ptxn_id):
    ptxn = PendingTransaction.query.get_or_404(ptxn_id)
    if ptxn.status != 'pending':
        flash("Transaction is no longer pending.", "error")
        return redirect(url_for('auditor_dashboard'))
    
    # Process the transaction
    account = Account.query.get(ptxn.account_id)
    
    converted_amount = ptxn.amount * ptxn.fx_rate_applied
    
    # Check liquidity again
    if ptxn.txn_type in ["Debit", "Transfer"] and account.balance < converted_amount:
        flash("Target account lacks sufficient liquidity to approve this transfer.", "error")
        return redirect(url_for("auditor_dashboard"))

    # Update balance
    if ptxn.txn_type == "Credit":
        account.balance += converted_amount
    elif ptxn.txn_type in ["Debit", "Transfer"]:
        account.balance -= converted_amount

    # Convert to real transaction
    txn = Transaction(
        transaction_id=ptxn.transaction_id,
        account_id=ptxn.account_id,
        amount=ptxn.amount,
        txn_type=ptxn.txn_type,
        source_currency=ptxn.source_currency,
        target_currency=ptxn.target_currency,
        fx_rate_applied=ptxn.fx_rate_applied,
        fx_timestamp=ptxn.fx_timestamp,
        description=ptxn.description,
        status="Completed",
        initiated_by=ptxn.maker_user_id
    )

    # Auto-flag high-value transactions
    if ptxn.amount > 50000:
        txn.flagged = True
        txn.status = 'Flagged'

    ptxn.status = 'approved'
    ptxn.checker_user_id = current_user.id
    ptxn.checker_timestamp = datetime.utcnow()

    db.session.add(txn)
    db.session.commit()
    
    audit_log("TRANSACTION_APPROVED", financial_data=f"Approved TXN {ptxn.transaction_id}")
    flash(f"Transaction {ptxn.transaction_id} approved and executed.", "success")
    return redirect(url_for('auditor_dashboard'))

@app.route('/auditor/reject_transaction/<int:ptxn_id>', methods=['POST'])
@role_required('Auditor')
def reject_transaction(ptxn_id):
    ptxn = PendingTransaction.query.get_or_404(ptxn_id)
    if ptxn.status != 'pending':
        flash("Transaction is no longer pending.", "error")
        return redirect(url_for('auditor_dashboard'))
        
    ptxn.status = 'rejected'
    ptxn.checker_user_id = current_user.id
    ptxn.checker_timestamp = datetime.utcnow()
    db.session.commit()
    
    audit_log("TRANSACTION_REJECTED", financial_data=f"Rejected TXN {ptxn.transaction_id}")
    flash(f"Transaction {ptxn.transaction_id} rejected.", "success")
    return redirect(url_for('auditor_dashboard'))

@app.route('/transaction/<int:txn_id>/receipt')
@login_required
def transaction_receipt(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    account = Account.query.get(txn.account_id)
    
    if current_user.role == 'Analyst' and account.assigned_analyst_id != current_user.id:
        abort(403)
        
    audit_log("GENERATED_RECEIPT", financial_data=txn.transaction_id)
    return render_template('receipt.html', txn=txn, account=account)

@app.route('/account/<int:account_id>/statement')
@login_required
def account_statement(account_id):
    account = Account.query.get_or_404(account_id)
    
    # Security: Analysts can only see their assigned accounts
    if current_user.role == 'Analyst' and account.assigned_analyst_id != current_user.id:
        abort(403)
        
    # Standard Period: Last 30 Days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    # Fetch all transactions for this account in the window
    transactions = Transaction.query.filter(
        Transaction.account_id == account_id,
        Transaction.timestamp >= start_date,
        Transaction.timestamp <= end_date
    ).order_by(Transaction.timestamp.desc()).all()
    
    # Net Velocity Calculation (All amounts adjusted to Base Currency)
    net_velocity = 0
    for t in transactions:
        # If txn was FX, we use the amount in base currency (txn.amount * rate)
        # Note: If txn.amount was already in base, rate is 1.0
        val = t.amount * (t.fx_rate_applied if t.fx_rate_applied else 1.0)
        if t.txn_type == 'Credit':
            net_velocity += val
        else:
            net_velocity -= val
            
    opening_balance = account.balance - net_velocity
    
    audit_log("GENERATED_STATEMENT", financial_data=f"Account {account.account_number}")
    
    return render_template('statement.html', 
                         account=account, 
                         transactions=transactions,
                         opening_balance=opening_balance,
                         net_velocity=net_velocity,
                         start_date=start_date.strftime('%Y-%m-%d'),
                         end_date=end_date.strftime('%Y-%m-%d'))

@app.route('/api/portfolio/history')
@login_required
def portfolio_history():
    # Simple aggregation for velocity graphs
    account_id = request.args.get('account_id')
    if not account_id:
        return {'error': 'account_id required'}, 400
        
    account = Account.query.get_or_404(int(account_id))
    
    # Generate 30 days of mock/real data (simplified for demo)
    import random
    dates = [(datetime.utcnow() - timedelta(days=x)).strftime('%Y-%m-%d') for x in range(30, -1, -1)]
    balances = []
    
    current_b = account.balance * 0.8 # Starts slightly lower
    for d in dates[:-1]:
        current_b += random.uniform(-1000, 2000)
        balances.append(round(current_b, 2))
    balances.append(round(account.balance, 2)) # Today's true logic
    
    return {
        "dates": dates,
        "balances": balances,
        "currency": account.currency_code
    }

@app.route('/admin')
@role_required('Admin')
def admin_dashboard():
    users = User.query.all()
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(15).all()
    total_accounts = Account.query.count()
    total_transactions = Transaction.query.count()
    flagged_count = Transaction.query.filter_by(flagged=True).count()
    audit_log("Accessed System Administration Dashboard")
    return render_template('admin_dashboard.html', 
                         users=users, 
                         logs=logs,
                         total_accounts=total_accounts,
                         total_transactions=total_transactions,
                         flagged_count=flagged_count)

# ═══════════════════════════════════════════
#  ADMIN CONTROL & SYSTEM OPS
# ═══════════════════════════════════════════

@app.route('/admin/toggle-maintenance', methods=['POST'])
@role_required('Admin')
def toggle_maintenance():
    app.config['MAINTENANCE_MODE'] = not app.config.get('MAINTENANCE_MODE', False)
    audit_log(f"System Maintenance Mode: {'Enabled' if app.config['MAINTENANCE_MODE'] else 'Disabled'}")
    flash(f"Maintenance Mode {'Activated' if app.config['MAINTENANCE_MODE'] else 'Deactivated'}.", 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reset-2fa/<int:user_id>', methods=['POST'])
@role_required('Admin')
def reset_2fa(user_id):
    user = User.query.get_or_404(user_id)
    user.is_2fa_enabled = False
    user.totp_secret = None
    db.session.commit()
    audit_log(f"MFA Reset for User {user.email}")
    flash(f"TOTP credentials for {user.full_name} have been reset.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle-user/<int:user_id>', methods=['POST'])
@role_required('Admin')
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    status = "Activated" if user.is_active else "Suspended"
    audit_log(f"User {status}: {user.email}")
    flash(f"User {user.full_name} has been {status.lower()}.", 'success')
    return redirect(url_for('admin_dashboard'))

# ═══════════════════════════════════════════

@app.route('/logout')
@login_required
def logout():
    audit_log("LOGOUT")
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5002)
