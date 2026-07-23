import re
from database import DatabaseManager
from config import Config

class EmailGenerator:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def generate_pitch(self, target_domain: str, company_name: str, lead_name: str = "", category: str = "") -> tuple[str, str]:
        sender_name = Config.SENDER_NAME or "Domain Owner"
        name_greeting = f" {lead_name}" if lead_name and lead_name.strip() and lead_name != "Decision Maker" else ""
        
        if category:
            raw_items = [item.strip() for item in re.split(r'[,\|;]', category) if item.strip()]
            cat_items = [c for c in raw_items if len(c) <= 30]
            if len(cat_items) > 1:
                sector_phrase = f"in sectors like {', '.join(cat_items[:3])}"
            elif len(cat_items) == 1:
                sector_phrase = f"in the {cat_items[0]} space"
            else:
                sector_phrase = "in your sector"
        else:
            sector_phrase = "in your sector"

        company_phrase = f"leading {company_name}" if company_name else "your work"

        subject = f"Acquisition query: {target_domain}"

        body = f"""Hi{name_greeting},

I'm reaching out directly because of {company_phrase} {sector_phrase}.

I currently hold the domain asset **{target_domain}** and am preparing to transfer it to a category leader. 

Given your footprint {sector_phrase}, acquiring **{target_domain}** would provide immediate brand authority, defense against competitors, and marketing advantages.

Are you open to receiving a quick acquisition proposal or discussing terms for the domain?

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
            category = lead["domain_category"] if "domain_category" in lead.keys() and lead["domain_category"] else ""

            subject, body = self.generate_pitch(target_domain, company_name, lead_name, category)
            self.db.update_lead_draft(lead_id, subject, body)
            drafted_count += 1
            print(f"   [OK] Drafted email for lead: {lead['lead_email']} ({target_domain})")

        return drafted_count

