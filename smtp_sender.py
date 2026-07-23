import smtplib
import time
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config
from database import DatabaseManager

class SmtpSender:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def create_message(self, to_email: str, subject: str, body: str) -> MIMEMultipart:
        msg = MIMEMultipart()
        msg['From'] = f"{Config.SENDER_NAME} <{Config.SMTP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        return msg

    def send_single_email(self, to_email: str, subject: str, body: str) -> bool:
        msg = self.create_message(to_email, subject, body)
        
        try:
            if Config.SMTP_PORT == 465:
                with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, timeout=15) as server:
                    server.login(Config.SMTP_USER, Config.SMTP_PASS)
                    server.sendmail(Config.SMTP_USER, [to_email], msg.as_string())
            else:
                with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=15) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(Config.SMTP_USER, Config.SMTP_PASS)
                    server.sendmail(Config.SMTP_USER, [to_email], msg.as_string())
            return True
        except Exception as e:
            raise RuntimeError(f"SMTP Dispatch Error ({Config.SMTP_HOST}:{Config.SMTP_PORT}): {str(e)}")

    def send_email(self, to_email: str, subject: str, body: str, dry_run: bool = False) -> bool:
        if dry_run:
            print(f"[DRY-RUN SIMULATION] Would send email to: {to_email}")
            return True
        return self.send_single_email(to_email, subject, body)

    def execute_campaign(self, dry_run: bool = True) -> int:
        drafed_leads = self.db.get_leads_by_status("DRAFTED")
        if not drafed_leads:
            print("\n[*] No DRAFTED leads available for dispatch.")
            return 0

        sent_today = self.db.get_sent_count_today()
        remaining_quota = Config.MAX_DAILY_EMAILS - sent_today

        if remaining_quota <= 0 and not dry_run:
            print(f"\n[!] Daily email quota limit reached ({sent_today}/{Config.MAX_DAILY_EMAILS}). Stopping dispatch for today.")
            return 0

        mode_label = "[DRY-RUN SIMULATION]" if dry_run else "[LIVE HOSTINGER SMTP DISPATCH]"
        print(f"\n[*] Starting campaign dispatch {mode_label}...")
        print(f"   Daily sent today: {sent_today}/{Config.MAX_DAILY_EMAILS} (Quota remaining: {remaining_quota})")

        if not dry_run and not Config.validate_smtp():
            print("[X] Invalid Hostinger SMTP credentials in .env file! Please update SMTP_USER and SMTP_PASS before running live.")
            return 0

        dispatched_count = 0

        for idx, lead in enumerate(drafed_leads):
            if not dry_run and dispatched_count >= remaining_quota:
                print(f"[!] Daily quota reached mid-campaign ({Config.MAX_DAILY_EMAILS} emails max). Stopping.")
                break

            lead_id = lead["id"]
            to_email = lead["lead_email"]
            subject = lead["email_subject"]
            body = lead["email_body"]
            target_dom = lead["target_domain"]

            print(f"\n[{idx + 1}/{len(drafed_leads)}] Target: {to_email} | Domain: {target_dom}")
            print(f"    Subject: {subject}")

            if dry_run:
                print("    [DRY-RUN] Email payload validated. Status marked SENT (Simulated).")
                self.db.mark_lead_sent(lead_id)
                dispatched_count += 1
            else:
                try:
                    self.send_single_email(to_email, subject, body)
                    self.db.mark_lead_sent(lead_id)
                    dispatched_count += 1
                    print("    [OK] Dispatched successfully via Hostinger SMTP!")

                    if idx < len(drafed_leads) - 1:
                        delay = random.randint(Config.MIN_DELAY_SECONDS, Config.MAX_DELAY_SECONDS)
                        print(f"    [WAIT] Rate limit delay: waiting {delay} seconds before next email...")
                        time.sleep(delay)

                except Exception as e:
                    error_msg = str(e)
                    print(f"    [X] Failed: {error_msg}")
                    self.db.mark_lead_failed(lead_id, error_msg)

        print(f"\n[OK] Campaign execution complete. Total processed: {dispatched_count}.")
        return dispatched_count

    def test_connection(self) -> tuple[bool, str]:
        try:
            if Config.SMTP_PORT == 465:
                with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
                    server.login(Config.SMTP_USER, Config.SMTP_PASS)
            else:
                with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(Config.SMTP_USER, Config.SMTP_PASS)
            return True, f"Successfully authenticated with {Config.SMTP_HOST}:{Config.SMTP_PORT} as {Config.SMTP_USER}"
        except Exception as e:
            return False, f"Connection Failed: {str(e)}"
