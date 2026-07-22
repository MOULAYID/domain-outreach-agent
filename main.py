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

def banner():
    print("=" * 60)
    print("  [+] DOMAIN SALES COLD OUTREACH PIPELINE (HOSTINGER SMTP)  ")
    print("=" * 60)

def parse_domains_from_file(file_path: Path) -> list[str]:
    domains_to_add = []
    suffix = file_path.suffix.lower()

    if suffix == '.csv':
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            domain_col_idx = 0

            # Detect domain column header if present
            if header:
                header_lower = [h.strip().lower() for h in header]
                for possible_name in ['domain', 'domain_name', 'domains', 'domain name', 'name', 'url']:
                    if possible_name in header_lower:
                        domain_col_idx = header_lower.index(possible_name)
                        break
                else:
                    # If header line wasn't a recognized header, treat it as first row if it looks like a domain
                    if '.' in header[0]:
                        domains_to_add.append(header[0].strip())

            for row in reader:
                if row and len(row) > domain_col_idx:
                    val = row[domain_col_idx].strip()
                    if val and '.' in val and not val.startswith('#'):
                        domains_to_add.append(val)
    else:
        # Plain text file (one domain per line)
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                d = line.strip()
                if d and not d.startswith("#"):
                    domains_to_add.append(d)

    return domains_to_add

def cmd_import(args, db: DatabaseManager):
    target = args.target
    domains_to_add = []
    
    file_path = Path(target)
    if file_path.is_file():
        domains_to_add = parse_domains_from_file(file_path)
    else:
        domains_to_add.append(target)

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

def cmd_run_all(args, db: DatabaseManager):
    print("\n[*] Executing Full Automation Workflow...")
    cmd_discover(args, db)
    cmd_generate(args, db)
    cmd_send(args, db)

def cmd_status(args, db: DatabaseManager):
    domains = db.get_all_domains()
    leads = db.get_all_leads()
    sent_today = db.get_sent_count_today()

    status_counts = {"DISCOVERED": 0, "DRAFTED": 0, "SENT": 0, "FAILED": 0}
    for lead in leads:
        st = lead["status"]
        status_counts[st] = status_counts.get(st, 0) + 1

    table_data = [
        ["Total Domains Managed", len(domains)],
        ["Total Leads Discovered", len(leads)],
        ["Pending Drafts (DRAFTED)", status_counts["DRAFTED"]],
        ["Dispatched Leads (SENT)", status_counts["SENT"]],
        ["Failed Dispatches (FAILED)", status_counts["FAILED"]],
        ["Emails Sent Today", f"{sent_today} / {Config.MAX_DAILY_EMAILS}"]
    ]

    print("\n[+] PIPELINE STATUS OVERVIEW")
    print(tabulate(table_data, headers=["Metric", "Value"], tablefmt="grid"))

    if leads:
        print("\n[+] RECENT LEADS SUMMARY (Last 10)")
        recent_leads = [
            [l["target_domain"], l["lead_email"], l["company_name"] or "N/A", l["status"], l["created_at"]]
            for l in leads[:10]
        ]
        print(tabulate(recent_leads, headers=["Target Domain", "Email", "Company", "Status", "Date"], tablefmt="grid"))

def main():
    banner()
    db = DatabaseManager()

    parser = argparse.ArgumentParser(description="Domain Sales Outreach Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Available Commands")

    # Import
    p_import = subparsers.add_parser("import", help="Import domain names from CSV, TXT file, or domain string")
    p_import.add_argument("target", help="File path (e.g. my_domains.csv, domains.txt) or domain string (e.g. cloudai.com)")

    # Discover
    p_discover = subparsers.add_parser("discover", help="Search and discover buyer leads for domains")

    # Generate
    p_generate = subparsers.add_parser("generate", help="Generate personalized pitch email copy for discovered leads")

    # Send
    p_send = subparsers.add_parser("send", help="Send emails to drafted leads")
    p_send.add_argument("--live", action="store_true", help="Run live Hostinger SMTP dispatch (default is --dry-run)")

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
        "discover": cmd_discover,
        "generate": cmd_generate,
        "send": cmd_send,
        "run-all": cmd_run_all,
        "status": cmd_status
    }

    cmd_map[args.command](args, db)

if __name__ == "__main__":
    main()
