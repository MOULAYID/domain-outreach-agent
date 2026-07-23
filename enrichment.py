import os
import requests
from typing import Optional, Dict

class B2BLeadEnricher:
    def __init__(self):
        self.hunter_api_key = os.getenv("HUNTER_API_KEY", "")
        self.apollo_api_key = os.getenv("APOLLO_API_KEY", "")
        self.session = requests.Session()

    def find_lead_via_hunter(self, domain_name: str) -> Optional[Dict[str, str]]:
        if not self.hunter_api_key:
            return None
        url = f"https://api.hunter.io/v2/domain-search?domain={domain_name}&api_key={self.hunter_api_key}"
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                emails = data.get("emails", [])
                if emails:
                    top_email = emails[0]
                    first_name = top_email.get("first_name", "")
                    last_name = top_email.get("last_name", "")
                    full_name = f"{first_name} {last_name}".strip()
                    company = data.get("organization") or domain_name
                    return {
                        "target_domain": domain_name,
                        "lead_email": top_email.get("value"),
                        "lead_name": full_name or "Decision Maker",
                        "company_name": company,
                        "source": "Hunter.io B2B API"
                    }
        except Exception:
            pass
        return None

    def find_lead_for_domain(self, domain_name: str) -> Optional[Dict[str, str]]:
        # 1. Try Hunter.io API if key configured
        hunter_res = self.find_lead_via_hunter(domain_name)
        if hunter_res:
            return hunter_res

        # 2. Return None if no enrichment API key available
        return None
