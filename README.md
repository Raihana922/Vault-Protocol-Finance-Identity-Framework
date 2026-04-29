# Identity Security Framework for Banking and Finance
## Implementation of The Reserve Torrent Protocol

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Security](https://img.shields.io/badge/security-TOTP%20%7C%20OAuth2-green.svg)](#features)

### 🏦 Overview
The **Identity Security Framework for Banking and Finance** is an institutional-grade authentication and access management system designed to protect high-value financial assets. Implementing the "Zero Trust" principle, this framework ensures absolute non-repudiation and granular control over operative access through multi-layered security protocols.

---

### ✨ Key Features

- **🔐 Advanced Authentication**: 
  - Secure Operative Registration using **Scrypt** cryptographic hashing.
  - Institutional Single Sign-On (SSO) via **Google OAuth2**.
- **📱 Multi-Factor Authentication (MFA)**:
  - Time-based One-Time Password (TOTP) integration.
  - Seamless QR Code generation for mobile authenticator synchronization.
- **🛡️ Governance & Compliance**:
  - **Role-Based Access Control (RBAC)**: Analyst, Auditor, and Admin tiers.
  - **Maker-Checker Workflows**: Ensuring critical transactions require multi-party approval.
- **📊 Transaction Telemetry**:
  - Real-time audit logging and operative activity tracking.
  - Encrypted ledger persistence for regulatory compliance.
- **🛡️ System Hardening**:
  - **Flask-Talisman**: Forced HTTPS and security headers (CSP, HSTS).
  - **Flask-Limiter**: Rate limiting to prevent brute-force attacks.

---

### 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python 3.x, Flask |
| **Database** | SQLite, SQLAlchemy (ORM) |
| **Security** | Authlib (OAuth), PyOTP (MFA), Cryptography (Scrypt) |
| **Middleware** | Flask-Login, Flask-Talisman, Flask-Limiter |
| **Frontend** | HTML5, Vanilla CSS (Modern Slate & Emerald Design) |

---

### 🚀 Getting Started

#### 1. Clone the Repository
```bash
git clone <repository-url>
cd finance_identity_framework
```

#### 2. Environment Configuration
Create a `.env` file in the root directory (referencing `.env.example` if available):
```env
# Google OAuth Credentials
FIN_GOOGLE_CLIENT_ID=your_google_client_id
FIN_GOOGLE_CLIENT_SECRET=your_google_client_secret

# Security Keys
FIN_SECRET_KEY=your_secure_random_string
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Initialize the Database
```bash
python seed_finance.py
```

#### 5. Launch the Application
```bash
python app.py
```
The application will be accessible at `http://127.0.0.1:5002`.

---

### 📖 Methodology
The framework follows an **Incremental and Security-First Development** methodology:
1. **Relational Data Mapping**: Defining ledger and identity schemas.
2. **Authentication Backbone**: Scrypt-based password management and OIDC.
3. **MFA Handshake Layer**: TOTP verification portal.
4. **Governance Layer**: RBAC decorators and Maker-Checker pipelines.
5. **Telemetry & Hardening**: Audit logging and security headers.

---

### ⚖️ Disclaimer
This project is a security prototype focusing on Identity and Access Management (IAM). It is intended for educational and demonstrative purposes and does not include live integration with financial networks like SWIFT.

---
*Developed as part of the Reserve Torrent Protocol Initiative.*
