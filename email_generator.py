import re
from database import DatabaseManager
from config import Config

class EmailGenerator:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def generate_pitch(self, target_domain: str, company_name: str, lead_name: str = "", category: str = "") -> tuple[str, str]:
        greeting = "Hi,"

        if category:
            raw_items = [item.strip() for item in re.split(r'[,\|;]', category) if item.strip()]
            cat_items = [c for c in raw_items if len(c) <= 30]
            if len(cat_items) >= 2:
                niche_phrase = f"{cat_items[0]} & {cat_items[1]}"
            elif len(cat_items) == 1:
                niche_phrase = cat_items[0]
            else:
                niche_phrase = "your industry"
        else:
            niche_phrase = "your industry"

        subject = f"{target_domain} is available!"

        body = f"""{greeting}

I am reaching out because **{target_domain}** is currently available for acquisition.

Given your strong presence in the {niche_phrase} space, I wanted to see if securing this premium asset aligns with your current digital strategy.

Please let me know if acquiring this is of interest to your team.

Best,

Idris | DomainEpoch
linkedin.com/in/moulay-idris-daouadi-/
domainepoch.com | contact@domainepoch.com

P.S. To ensure a safe and smooth transfer, we conduct all transactions securely through GoDaddy Escrow.
"""
        return subject, body

    def generate_followup_pitch(self, target_domain: str, lead_name: str = "") -> tuple[str, str]:
        greeting = "Hi,"

        subject = f"Re: {target_domain}"

        body = f"""{greeting}

I know things get busy, so I will keep this brief.

If you aren't the right person to speak with regarding digital asset acquisitions for your team, could you kindly point me in the right direction?

Best,

Idris | DomainEpoch
linkedin.com/in/moulay-idris-daouadi-/
domainepoch.com | contact@domainepoch.com
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
            print(f"   [OK] Drafted initial email for lead: {lead['lead_email']} ({target_domain})")

        return drafted_count

