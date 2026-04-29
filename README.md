# ManufacturingVault
### *Hardened Cloud Infrastructure for Manufacturing Data*
**Zero-Knowledge Encryption + Purdue Model OT/IT Segmentation on Azure**

[![IEC 62443](https://img.shields.io/badge/IEC%2062443--3--3-SL2%20Compliant-green)](docs/compliance/iec62443_mapping.md)
[![NIST SP 800-171](https://img.shields.io/badge/NIST%20SP%20800--171-CUI%20Protected-blue)](docs/compliance/nist800171_mapping.md)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Terraform](https://img.shields.io/badge/Terraform-4.x-purple)](https://terraform.io)

---

## What is ManufacturingVault?

ManufacturingVault is a production-grade, cloud-native file encryption system for industrial manufacturing environments. It protects sensitive intellectual property — CNC programs, PLC logic, CAD models, firmware binaries, and production logs — using **Zero-Knowledge AES-256-GCM encryption** with an Argon2id key derivation function.

The entire Azure infrastructure is architected on the **ISA/IEC 62443 Purdue Reference Model**, enforcing strict OT/IT network separation.

---

## Project Structure

```
ManufacturingVault/
├── README.md
├── app/
│   ├── app.py               # Flask web application (MES UI)
│   ├── crypto_utils.py      # AES-256-GCM + Argon2id engine
│   ├── blob_utils.py        # Azure Blob Storage manager
│   ├── auth.py              # Local auth (SQLite, Argon2id)
│   └── templates/
│       ├── base.html
│       ├── index.html
│       └── decrypt.html
├── terraform/
│   ├── main.tf              # Purdue Model 4-tier VNet, VMs, WAF
│   ├── storage.tf           # Azure Storage Account + Blob container
│   ├── variables.tf
│   ├── outputs.tf
│   └── secure_storage.py    # CLI encryption tool (batch + HSM)
├── scripts/
│   ├── scada_simulator.py   # Modbus TCP PLC simulator (Level 2)
│   └── docker-compose.yml   # Docker alternative for SCADA sim
├── tests/
│   ├── test_crypto.py       # Cryptographic unit tests
│   └── test_ot_integration.py # OT/IT integration tests
└── docs/
    ├── proposal.md
    ├── HLD.md               # High-Level Design (Purdue Model)
    ├── LLD.md               # Low-Level Design (specs & functions)
    ├── final_report.md      # Project case study
    ├── security_test_report.md
    └── compliance/
        ├── iec62443_mapping.md
        └── nist800171_mapping.md
```

---

## Quick Start

### 1. Install Dependencies

```bash
pip install flask cryptography argon2-cffi azure-identity azure-storage-blob pymodbus
```

### 2. Run the Web Application (Local)

```bash
cd app/
python app.py
# Open http://localhost:5000
```

> **Note:** The web app runs fully offline. Azure Blob Storage is optional — files are returned directly as downloads.

### 3. CLI Encryption (Single File)

```bash
cd terraform/
python secure_storage.py encrypt ./cnc_programs/spindle.nc
# Produces: spindle.nc.enc
```

### 4. CLI Batch Encryption (Entire Directory)

```bash
python secure_storage.py encrypt --batch ./cnc_programs/
# All files recursively encrypted → .enc in same directory
```

### 5. HSM-Backed Encryption (Azure Key Vault)

```bash
export AZURE_KEY_VAULT_URL="https://your-manufacturing-vault.vault.azure.net/"
export AZURE_KEY_NAME="manufacturing-aes-key"

python secure_storage.py encrypt firmware.bin --use-hsm
```

> **Setup required:** Deploy an Azure Key Vault, create an AES-256 key, assign `Key Vault Crypto User` role to the VM Managed Identity.

### 6. SCADA Simulator (Level 2 VM)

```bash
# Direct
cd scripts/
pip install pymodbus
python scada_simulator.py --host 0.0.0.0 --port 502

# Docker
docker-compose up -d
```

---

## Deploy to Azure (Terraform)

```powershell
cd terraform/
terraform init
terraform apply -auto-approve `
  -var="sql_admin_password=HardenedMfg2026!" `
  -var="sql_admin_login=sqladmin" `
  -var="location=centralindia" `
  -var="resource_group_name=rg-manufacturing-hardened-prod"
```

Terraform will provision:
- **4-tier VNet** (DMZ / MES / SCADA / Controller subnets)
- **Azure App Gateway (WAF_v2)** with OWASP 3.2 + custom Modbus rules
- **MES VM** (`Standard_B2s_v2`) with Managed Identity
- **SCADA VM** (`Standard_B1s`) in isolated subnet
- **Azure Blob Storage** (private, Managed Identity access only)
- **Azure SQL Database** (Manufacturing Historian)

---

## Industrial File Whitelist

The web application accepts only manufacturing-relevant file types:

| Category | Extensions |
|:---|:---|
| CNC Programs | `.nc`, `.gcode`, `.tap`, `.cnc` |
| PLC/Logic | `.l5x`, `.l5k`, `.rss`, `.pkg` |
| CAD/3D Models | `.stl`, `.step`, `.dwg`, `.dxf` |
| Quality Documents | `.pdf`, `.docx`, `.xlsx` |
| Sensor/Production Logs | `.log`, `.dat`, `.csv`, `.txt` |
| Firmware | `.bin`, `.hex`, `.s19` |

Override via environment variable:
```bash
export ALLOWED_EXTENSIONS=".nc,.gcode,.l5x,.bin"
```

---

## Compliance

| Standard | Requirement | Status |
|:---|:---|:---|
| IEC 62443-3-3 SR 3.4 | Data confidentiality | ✅ AES-256-GCM |
| IEC 62443-3-3 SR 5.2 | Zone isolation | ✅ Purdue NSG rules |
| NIST SP 800-171 3.13.10 | FIPS cryptography | ✅ Argon2id + AES-256-GCM |
| NIST SP 800-171 3.1.3 | Control CUI flow | ✅ VNet segmentation |

Full mapping: [`docs/compliance/`](docs/compliance/)

---

## Security Architecture

```
Internet → [WAF/DMZ] → [MES App] → [SCADA Sim]
                           ↓              ↑
                     [Azure Blob]   Modbus TCP/502
                     [SQL DB]       (MES only)
                                   [Controller] ← Fully Isolated
```

- **Internet → SCADA: BLOCKED** (NSG DenyInternetToSCADA)
- **DMZ → SCADA: BLOCKED** (NSG DenyDMZToSCADA)
- **MES → SCADA: Allowed on TCP 502, 102, 44818 only**

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

