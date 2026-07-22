from database import DatabaseManager
from config import Config

class EmailGenerator:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def generate_pitch(self, target_domain: str, company_name: str, lead_name: str = "") -> tuple[str, str]:
        sender_name = Config.SENDER_NAME or "Domain Owner"
        name_greeting = f" {lead_name}" if lead_name and lead_name != "Decision Maker" else ""
        company_mention = f" for {company_name}" if company_name else ""

        subject = f"Acquisition query: {target_domain}"

        body = f"""Hi{name_greeting},

I'm reaching out because I noticed your team's work{company_mention}.

I currently own the domain asset **{target_domain}** and am preparing to list it for sale or transfer it to a category leader. 

Given your presence in this space, acquiring **{target_domain}** could offer strong brand protection, direct category authority, and marketing advantages.

Are you open to receiving a quick price quote or making an offer for the domain?

Best regards,

{sender_name}
---
To opt out of future domain updates regarding {target_domain}, please reply with 'unsubscribe'.
"""
        return subject, body

    def generate_drafts_for_pending_leads(self) -> int:
        pending_leads = self.db.get_leads_by_status("DISCOVERED")
        if not pending_leads:
            print("\n[*] No pending DISCOVERED leads found needing email drafts.")
            return 0

        print(f"\n[*] Generating email drafts for {len(pending_leads)} lead(s)...")
        drafted_count = 0

        for lead in pending_leads:
            lead_id = lead["id"]
            target_domain = lead["target_domain"]
            company_name = lead["company_name"]
            lead_name = lead["lead_name"]

            subject, body = self.generate_pitch(target_domain, company_name, lead_name)
            self.db.update_lead_draft(lead_id, subject, body)
            drafted_count += 1
            print(f"   [OK] Drafted email for lead: {lead['lead_email']} ({target_domain})")

        return drafted_count
