# PROJECT PROPOSAL

### I. Title of the Project
**Identity Security Framework for Banking and Finance**  
(Implementation of The Reserve Torrent Protocol)

### II. Statement of the Problem
The financial industry faces an existential threat from sophisticated identity theft and unauthorized ledger access. Traditional login systems, often relying on insecure password storage and lacking secondary verification, cannot protect high-value assets effectively. The problem is to develop a robust, institutional-grade authentication system using Python, Flask-Login, and SQLite that integrates OAuth2 and TOTP-MFA to ensure absolute non-repudiation and access control.

### III. Why this particular topic chosen?
Financial security is the most demanding domain for identity management. This topic was chosen to explore the technical implementation of "Zero Trust" principles in a banking context—specifically focusing on Maker-Checker workflows, encrypted data persistence, and institutional single sign-on (SSO). It provides a high-stakes environment to demonstrate how software can enforce regulatory compliance and prevent financial fraud.

### IV. Objective and Scope
- **Objective:** To develop a secure Identity and Access Management (IAM) system for financial operatives using Python, Flask-Login, and encrypted SQLite storage.
- **Scope:** 
    - Secure Operative Registration and Cryptographic Hashing (Scrypt).
    - Multi-Factor Authentication (TOTP/QR scan) for vault access.
    - Institutional Identity Integration (Google OAuth2).
    - Role-Based Access Control (Analyst, Auditor, Admin).
    - Transaction Telemetry and Audit Logging.

### V. Methodology
The project follows an **Incremental and Security-First Development** methodology:
1. **Relational Data Mapping:** Defining the ledger and identity schemas.
2. **Authentication Backbone:** Implementing scrypt-based password management and OIDC (Google Sign-On).
3. **MFA Handshake Layer:** Development of the secondary TOTP verification portal.
4. **Governance Layer:** Implementing RBAC decorators and the Maker-Checker approval pipeline.
5. **Telemetry & Hardening:** Adding audit logging and Talisman security headers.

### VI. Process Description
- **Authentication Module:** Handles secure entry via local credentials or external Google identity tokens.
- **Session Management:** Flask-Login maintains stateful operative sessions with mandatory 5-minute MFA re-authentication for high-value operations.
- **Authorization Engine (RBAC):** Restricts access to sensitive routes (e.g., transaction approval) based on the assigned institutional role.
- **Database Layer:** SQLite encrypted engine storing ledger records and identity hashes securely.

### VII. Resources and Limitations
- **Hardware:** Standard development machine with internet access for OAuth callback verification.
- **Software:** Python 3.x, Flask, Werkzeug, Authlib, PyOTP, SQLAlchemy, SQLite.
- **Limitations:** This is a security prototype focusing on IAM; it does not include actual integration with the SWIFT network or live stock exchanges.

### VIII. Testing Technologies used
- **Black Box Testing:** Simulating unauthorized access attempts to restricted Dashboards.
- **White Box Testing:** Verifying the accuracy of scrypt-hashing and password fragment fallback logic.
- **Integration Testing:** Ensuring the Google SSO callback correctly maps email domains to internal system roles.

### IX. Conclusion
The **Identity Security Framework for Banking and Finance** serves as a modern blueprint for financial identity protection. By incorporating Google SSO and MFA, it demonstrates how institutions can bridge the gap between user convenience and clinical security. This project provides a scalable foundation for building advanced digital vaults and regulatory compliance tools.
