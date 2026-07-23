import imaplib
import email
from email.header import decode_header
from config import Config
from database import DatabaseManager

class ImapListener:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.host = getattr(Config, "IMAP_HOST", "imap.hostinger.com")
        self.port = int(getattr(Config, "IMAP_PORT", 993))
        self.user = Config.SMTP_USER
        self.password = Config.SMTP_PASS

    def connect(self) -> imaplib.IMAP4_SSL:
        if not self.user or not self.password or self.password == "change_me_to_your_real_password":
            raise ValueError("IMAP connection skipped: Hostinger SMTP credentials not set in .env")
        mail = imaplib.IMAP4_SSL(self.host, self.port)
        mail.login(self.user, self.password)
        return mail

    def sync_inbox(self) -> dict:
        summary = {"unsubscribed": 0, "replied": 0, "errors": 0}
        try:
            mail = self.connect()
            mail.select("INBOX")
            
            # Fetch unread emails
            status, messages = mail.search(None, 'UNSEEN')
            if status != 'OK' or not messages[0]:
                print("[*] IMAP Inbox Check: No new unread messages.")
                return summary

            msg_ids = messages[0].split()
            print(f"[*] IMAP Inbox Check: Found {len(msg_ids)} new message(s). Processing...")

            all_leads = {l["lead_email"].lower(): l for l in self.db.get_all_leads()}

            for msg_id in msg_ids:
                res, msg_data = mail.fetch(msg_id, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        from_header = msg.get("From", "")
                        subject_header = msg.get("Subject", "")
                        
                        # Extract sender email address
                        from_email = ""
                        if "<" in from_header and ">" in from_header:
                            from_email = from_header.split("<")[1].split(">")[0].strip().lower()
                        else:
                            from_email = from_header.strip().lower()

                        # Extract message body text
                        body_text = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                if content_type == "text/plain":
                                    body_text += part.get_payload(decode=True).decode(errors="ignore")
                        else:
                            body_text = msg.get_payload(decode=True).decode(errors="ignore")

                        combined_text = (subject_header + " " + body_text).lower()

                        # Check if sender matches a known lead in system
                        if from_email in all_leads:
                            lead_id = all_leads[from_email]["id"]
                            if "unsubscribe" in combined_text or "opt out" in combined_text or "remove" in combined_text:
                                self.db.mark_lead_unsubscribed(lead_id)
                                summary["unsubscribed"] += 1
                                print(f"   [!] Unsubscribe detected for lead: {from_email}")
                            else:
                                self.db.mark_lead_replied(lead_id)
                                summary["replied"] += 1
                                print(f"   [+] Prospect reply detected from lead: {from_email} (Status marked REPLIED)")

            mail.logout()
        except Exception as e:
            print(f"[X] IMAP Inbox Check Error: {str(e)}")
            summary["errors"] += 1

        return summary
