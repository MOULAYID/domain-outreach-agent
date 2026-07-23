# 🌐 Domain Sales Cold Outreach Pipeline (Hostinger SMTP)

An automated Python pipeline designed to discover buyer leads for domain names, generate personalized cold email pitches, and dispatch emails safely using **Hostinger Webmail SMTP** with built-in rate-limiting and campaign tracking.

---

## ✨ Features

- **📄 CSV & TXT Domain Import**: Import target domain names from `.csv` files (with automatic header detection) or text files.
- **🔍 Automated Lead Discovery**: Queries WHOIS/RDAP endpoints for alternative domain extensions (`.org`, `.co`, `.net`, `.io`, `.ai`) and web search to discover decision-maker contacts.
- **✉️ Dynamic Cold Email Copy**: Drafts concise, high-converting, non-spammy outreach pitches tailored per domain asset.
- **⚡ Hostinger SMTP Integration**: Connects over SSL (`port 465`) or TLS (`port 587`) with `smtp.hostinger.com`.
- **🛡️ Rate-Limiting Safeguards**: Configurable daily sending quotas and randomized inter-message delays (3–7 mins) to protect domain deliverability.
- **📊 SQLite Database Logging**: Tracks lead pipeline states (`DISCOVERED` ➔ `DRAFTED` ➔ `SENT` / `FAILED`).
- **🧪 Dry-Run Simulation Mode**: Validate email payloads and workflow without dispatching real emails over SMTP.

---

## 🛠️ Project Structure

```text
domain-outreach-agent/
├── config.py           # Environment loader & Hostinger SMTP settings
├── database.py         # SQLite storage and lead status manager
├── lead_finder.py      # Keyword extractor, RDAP/WHOIS & search query engine
├── email_generator.py  # Personalized email copywriting engine
├── smtp_sender.py      # Hostinger SMTP client with rate-limiting & dry-run mode
├── main.py             # Unified CLI entry point
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── README.md           # Documentation
```

---

## 🚀 Quick Start

### 1. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/your-username/domain-outreach-agent.git
cd domain-outreach-agent
pip install -r requirements.txt
```

### 2. Configuration
Copy `.env.example` to `.env` and fill in your Hostinger Email credentials:
```bash
cp .env.example .env
```
Edit `.env`:
```env
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=465
SMTP_USER=your_email@yourdomain.com
SMTP_PASS=your_hostinger_email_password
SENDER_NAME=Your Name

MAX_DAILY_EMAILS=30
MIN_DELAY_SECONDS=180
MAX_DELAY_SECONDS=420

TEST_RECIPIENT_EMAIL=your_test_email@example.com
```

### 3. Usage

#### Import Domains
Import domains from a CSV file (e.g. `domain,category`):
```bash
python main.py import domains.csv
```
Or import a single domain name:
```bash
python main.py import mycoolbrand.com
```

#### Discover Leads & Generate Pitches
```bash
python main.py discover
python main.py generate
```

#### Send Outreach Emails
Simulate sending in `--dry-run` mode first:
```bash
python main.py send
```
Run live Hostinger SMTP email dispatch:
```bash
python main.py send --live
```

#### Launch Web Graphical Interface (GUI Dashboard)
Launch the interactive Streamlit web app in your default browser:
```bash
python main.py gui
```
Or directly via Streamlit:
```bash
streamlit run app.py
```

#### View CLI Pipeline Dashboard
```bash
python main.py status
```

---

## 🛡️ Security & Compliance
- **Credentials Protection**: Sensitive passwords and keys are loaded from `.env` (which is included in `.gitignore`).
- **Unsubscribe Link**: Emails include standard opt-out instructions to comply with email outreach standards.

---

## 📜 License
MIT License. Free to use and modify for domain portfolio management.
