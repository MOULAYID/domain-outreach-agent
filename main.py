import sys
import io
import csv
import argparse
from pathlib import Path
from tabulate import tabulate

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from config import Config
from database import DatabaseManager
from lead_finder import LeadFinder
from email_generator import EmailGenerator
from smtp_sender import SmtpSender
from imap_listener import ImapListener
from email_verifier import EmailVerifier

def banner():
    print("=" * 60)
    print("  [+] DOMAIN SALES COLD OUTREACH PIPELINE (HOSTINGER SMTP)  ")
    print("=" * 60)

def parse_domains_from_file(file_path: Path) -> list[tuple[str, str]]:
    domains_to_add = []
    suffix = file_path.suffix.lower()

    if suffix == '.csv':
        with open(file_path, "r", encoding="utf-8-sig") as f:
            sample = f.readline()
            f.seek(0)
            delimiter = ';' if ';' in sample and sample.count(';') > sample.count(',') else ','
            
            reader = csv.reader(f, delimiter=delimiter)
            header = next(reader, None)
            domain_col_idx = 0
            cat_col_idxs = []

            # Detect domain and category column headers
            if header:
                header_lower = [h.strip().lower() for h in header]
                for possible_name in ['domain name', 'domain_name', 'domain', 'domains', 'name', 'url']:
                    if possible_name in header_lower:
                        domain_col_idx = header_lower.index(possible_name)
                        break
                
                # Check for category / target audience columns
                for idx, col_name in enumerate(header_lower):
                    if any(key in col_name for key in ['category', 'target audience', 'keywords', 'niche', 'use cases']):
                        cat_col_idxs.append(idx)

            for row in reader:
                if row and len(row) > domain_col_idx:
                    dom_val = row[domain_col_idx].strip()
                    if dom_val and '.' in dom_val and not dom_val.startswith('#'):
                        cats = []
                        for c_idx in cat_col_idxs:
                            if len(row) > c_idx and row[c_idx].strip():
                                # Extract items split by | or ,
                                raw_cat = row[c_idx].strip()
                                parts = [p.strip() for p in raw_cat.replace(';', '|').split('|') if p.strip()]
                                cats.extend(parts)
                        
                        # Deduplicate categories maintaining order
                        seen = set()
                        unique_cats = [c for c in cats if not (c.lower() in seen or seen.add(c.lower()))]
                        cat_str = " | ".join(unique_cats)
                        
                        domains_to_add.append((dom_val, cat_str))
    else:
        # Plain text file (one domain per line)
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                d = line.strip()
                if d and not d.startswith("#"):
                    domains_to_add.append((d, ""))

    return domains_to_add

def parse_leads_from_file(file_path: Path) -> list[dict[str, str]]:
    leads_to_add = []
    suffix = file_path.suffix.lower()

    if suffix == '.csv':
        with open(file_path, "r", encoding="utf-8-sig") as f:
            sample = f.readline()
            f.seek(0)
            delimiter = ';' if ';' in sample and sample.count(';') > sample.count(',') else ','
            
            reader = csv.reader(f, delimiter=delimiter)
            header = next(reader, None)
            
            dom_idx = 0
            email_idx = 1
            name_idx = None
            company_idx = None
            field_idx = None

            if header:
                header_lower = [h.strip().lower() for h in header]
                
                # Detect Domain column
                for key in ['target_domain', 'domain_name', 'domain name', 'domain', 'url']:
                    if key in header_lower:
                        dom_idx = header_lower.index(key)
                        break

                # Detect Email column
                for key in ['lead_email', 'contact_email', 'email', 'e-mail']:
                    if key in header_lower:
                        email_idx = header_lower.index(key)
                        break

                # Detect Name column
                for key in ['lead_name', 'contact_name', 'full_name', 'name']:
                    if key in header_lower:
                        name_idx = header_lower.index(key)
                        break

                # Detect Company column
                for key in ['company_name', 'organization', 'company', 'org']:
                    if key in header_lower:
                        company_idx = header_lower.index(key)
                        break

                # Detect Field/Industry column
                for key in ['field', 'industry', 'category', 'niche', 'target audience & uses', 'target audience']:
                    if key in header_lower:
                        field_idx = header_lower.index(key)
                        break

            for row in reader:
                if row and len(row) > dom_idx and len(row) > email_idx:
                    dom_val = row[dom_idx].strip()
                    email_val = row[email_idx].strip()
                    if dom_val and email_val and '@' in email_val:
                        name_val = row[name_idx].strip() if name_idx is not None and len(row) > name_idx else ""
                        comp_val = row[company_idx].strip() if company_idx is not None and len(row) > company_idx else ""
                        field_val = row[field_idx].strip() if field_idx is not None and len(row) > field_idx else ""
                        
                        leads_to_add.append({
                            "target_domain": dom_val,
                            "lead_email": email_val,
                            "lead_name": name_val,
                            "company_name": comp_val,
                            "field": field_val
                        })
    return leads_to_add

def cmd_import_leads(args, db: DatabaseManager):
    file_path = Path(args.target)
    if not file_path.is_file():
        print(f"[!] File not found: {file_path}")
        return

    leads_to_add = parse_leads_from_file(file_path)
    if not leads_to_add:
        print("[!] No valid lead records found in the provided CSV file.")
        return

    added, skipped = db.add_manual_leads(leads_to_add)
    print(f"\n[OK] Manual Leads Import Summary: {added} new lead(s) imported, {skipped} duplicate(s) skipped.")

def cmd_import(args, db: DatabaseManager):
    target = args.target
    domains_to_add = []
    
    file_path = Path(target)
    if file_path.is_file():
        domains_to_add = parse_domains_from_file(file_path)
    else:
        domains_to_add.append((target, ""))

    if not domains_to_add:
        print("[!] No valid domain names provided to import.")
        return

    added, skipped = db.add_domains(domains_to_add)
    print(f"\n[OK] Domain Import Summary: {added} new domain(s) added, {skipped} duplicate(s) skipped.")

def cmd_discover(args, db: DatabaseManager):
    domains = db.get_all_domains()
    if not domains:
        print("\n[!] No domains found in database. Run 'python main.py import <file.csv_or_domain>' first.")
        return

    finder = LeadFinder(db)
    total_found = 0
    for dom_row in domains:
        domain_name = dom_row["domain_name"]
        total_found += finder.discover_leads_for_domain(domain_name)

    print(f"\n[OK] Lead discovery complete. Total new leads saved: {total_found}")

def cmd_generate(args, db: DatabaseManager):
    generator = EmailGenerator(db)
    drafted = generator.generate_drafts_for_pending_leads()
    print(f"\n[OK] Email drafting complete. Total leads ready for send: {drafted}")

def cmd_send(args, db: DatabaseManager):
    sender = SmtpSender(db)
    is_live = getattr(args, 'live', False)
    dry_run = not is_live
    sender.execute_campaign(dry_run=dry_run)

def cmd_sync_inbox(args, db: DatabaseManager):
    print("\n[*] Connecting to Hostinger IMAP Inbox (imap.hostinger.com:993)...")
    listener = ImapListener(db)
    summary = listener.sync_inbox()
    print(f"\n[OK] Inbox Sync Summary: {summary['replied']} reply(ies) detected, {summary['unsubscribed']} unsubscribe(s) processed.")

def cmd_verify_emails(args, db: DatabaseManager):
    leads = db.get_leads_by_status("DISCOVERED")
    if not leads:
        print("\n[*] No pending DISCOVERED leads found needing email verification.")
        return

    print(f"\n[*] Running Pre-Send Email Verification for {len(leads)} lead(s)...")
    valid_count = 0
    invalid_count = 0

    for lead in leads:
        email_addr = lead["lead_email"]
        is_valid, reason = EmailVerifier.is_deliverable(email_addr)
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1
            print(f"   [!] Failed Verification: {email_addr} ({reason}) ➔ Marking FAILED")
            db.mark_lead_failed(lead["id"], f"Pre-Send Verification Error: {reason}")

    print(f"\n[OK] Pre-Send Email Verification Complete: {valid_count} valid, {invalid_count} failed.")

def cmd_auto_run(args, db: DatabaseManager):
    print("\n" + "=" * 60)
    print("  [+] EXECUTING UNIFIED AUTOMATION SUITE (AUTO-RUN)  ")
    print("=" * 60)

    # 1. Sync Inbox for Unsubscribes & Replies
    cmd_sync_inbox(args, db)

    # 2. Run Pre-Send Email Verification
    cmd_verify_emails(args, db)

    # 3. Generate Pitch Drafts
    cmd_generate(args, db)

    # 4. Check Follow-Up Drafts
    print("\n[*] Checking for Follow-Up Emails Due...")
    due_followups = db.get_leads_due_for_followup(days_delay=3)
    if due_followups:
        print(f"[*] Found {len(due_followups)} lead(s) due for follow-up outreach...")
        generator = EmailGenerator(db)
        for lead in due_followups:
            lead_id = lead["id"]
            target_domain = lead["target_domain"]
            lead_name = lead["lead_name"]
            subj, body = generator.generate_followup_pitch(target_domain, lead_name)
            db.update_lead_draft(lead_id, subj, body)
            print(f"   [OK] Drafted Follow-Up email for: {lead['lead_email']} ({target_domain})")

    # 5. Dispatch Email Campaign
    cmd_send(args, db)

def cmd_status(args, db: DatabaseManager):
    domains = db.get_all_domains()
    leads = db.get_all_leads()
    sent_today = db.get_sent_count_today()

    status_counts = {"DISCOVERED": 0, "DRAFTED": 0, "SENT": 0, "FAILED": 0, "REPLIED": 0, "UNSUBSCRIBED": 0}
    for lead in leads:
        st = lead["status"]
        status_counts[st] = status_counts.get(st, 0) + 1

    table_data = [
        ["Total Domains Managed", len(domains)],
        ["Total Leads Tracked", len(leads)],
        ["Pending Drafts (DRAFTED)", status_counts["DRAFTED"]],
        ["Dispatched Leads (SENT)", status_counts["SENT"]],
        ["Prospect Replies (REPLIED)", status_counts["REPLIED"]],
        ["Opted Out (UNSUBSCRIBED)", status_counts["UNSUBSCRIBED"]],
        ["Failed Dispatches (FAILED)", status_counts["FAILED"]],
        ["Emails Sent Today", f"{sent_today} / {Config.MAX_DAILY_EMAILS}"]
    ]

    print("\n[+] PIPELINE STATUS OVERVIEW")
    print(tabulate(table_data, headers=["Metric", "Value"], tablefmt="grid"))

    if domains:
        print("\n[+] DOMAIN INVENTORY SUMMARY (Last 10)")
        recent_doms = [
            [d["domain_name"], (d["category"][:45] + "...") if d["category"] and len(d["category"]) > 45 else (d["category"] or "N/A"), d["created_at"]]
            for d in domains[:10]
        ]
        print(tabulate(recent_doms, headers=["Domain Name", "Categories", "Import Date"], tablefmt="grid"))

    if leads:
        print("\n[+] RECENT LEADS SUMMARY (Last 10)")
        recent_leads = [
            [l["target_domain"], l["lead_email"], l["company_name"] or "N/A", l["status"], l["created_at"]]
            for l in leads[:10]
        ]
        print(tabulate(recent_leads, headers=["Target Domain", "Email", "Company", "Status", "Date"], tablefmt="grid"))

def cmd_gui(args, db: DatabaseManager):
    print("\n[*] Launching Streamlit Graphical Web Dashboard...")
    import subprocess
    app_path = Path(__file__).parent / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])

def main():
    banner()
    db = DatabaseManager()

    parser = argparse.ArgumentParser(description="Domain Sales Outreach Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Available Commands")

    # Import Domains
    p_import = subparsers.add_parser("import", help="Import domain names from CSV, TXT file, or domain string")
    p_import.add_argument("target", help="File path (e.g. my_domains.csv, domains.txt) or domain string (e.g. cloudai.com)")

    # Import Manual Leads
    p_import_leads = subparsers.add_parser("import-leads", help="Import pre-qualified leads CSV (domain, email, name, company, field)")
    p_import_leads.add_argument("target", help="Leads CSV file path (e.g. my_leads.csv)")

    # Discover
    p_discover = subparsers.add_parser("discover", help="Search and discover buyer leads for domains")

    # Generate
    p_generate = subparsers.add_parser("generate", help="Generate personalized pitch email copy for discovered leads")

    # Send
    p_send = subparsers.add_parser("send", help="Send emails to drafted leads")
    p_send.add_argument("--live", action="store_true", help="Run live Hostinger SMTP dispatch (default is --dry-run)")

    # Sync Inbox
    p_sync = subparsers.add_parser("sync-inbox", help="Sync Hostinger IMAP inbox for replies and unsubscribes")

    # Verify Emails
    p_verify = subparsers.add_parser("verify-emails", help="Run pre-send syntax and MX DNS verification on leads")

    # Auto-Run
    p_autorun = subparsers.add_parser("auto-run", help="Run complete daily automation (Sync Inbox -> Verify -> Pitch -> Follow-up -> Send)")
    p_autorun.add_argument("--live", action="store_true", help="Run live Hostinger SMTP dispatch")

    # GUI Dashboard
    p_gui = subparsers.add_parser("gui", help="Launch Streamlit Graphical Web Dashboard in browser")

    # Run-All
    p_runall = subparsers.add_parser("run-all", help="Execute discover, generate, and send in sequence")
    p_runall.add_argument("--live", action="store_true", help="Run live Hostinger SMTP dispatch")

    # Status
    p_status = subparsers.add_parser("status", help="Show pipeline dashboard and lead tracking status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "import": cmd_import,
        "import-leads": cmd_import_leads,
        "discover": cmd_discover,
        "generate": cmd_generate,
        "send": cmd_send,
        "sync-inbox": cmd_sync_inbox,
        "verify-emails": cmd_verify_emails,
        "auto-run": cmd_auto_run,
        "gui": cmd_gui,
        "run-all": cmd_auto_run,
        "status": cmd_status
    }

    cmd_map[args.command](args, db)

if __name__ == "__main__":
    main()
