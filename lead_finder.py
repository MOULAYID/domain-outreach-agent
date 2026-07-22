import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from database import DatabaseManager

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

DISCARD_EMAILS = {
    'privacyprotect', 'whoisproxy', 'contactprivacy', 'domainprivacy', 
    'selectuser', 'domainsbyproxy', 'identityprotect', 'anonymousemail',
    'abuse@', 'postmaster@', 'webmaster@', 'hostmaster@', 'registrar@'
}

class LeadFinder:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def extract_niche_keywords(self, domain_name: str) -> str:
        base_name = domain_name.split('.')[0]
        cleaned = re.sub(r'[-_]', ' ', base_name)
        cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
        return cleaned.strip()

    def is_valid_lead_email(self, email: str) -> bool:
        email_lower = email.lower()
        if any(discard in email_lower for discard in DISCARD_EMAILS):
            return False
        if email_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
            return False
        return True

    def find_leads_via_rdap(self, domain_name: str) -> List[Dict[str, str]]:
        leads = []
        base_name = domain_name.split('.')[0]
        extensions_to_check = ['com', 'io', 'org', 'co', 'net', 'ai']
        
        current_ext = domain_name.split('.')[-1]
        extensions_to_check = [ext for ext in extensions_to_check if ext != current_ext]

        for ext in extensions_to_check:
            alt_domain = f"{base_name}.{ext}"
            rdap_url = f"https://rdap.org/domain/{alt_domain}"
            try:
                resp = self.session.get(rdap_url, timeout=5)
                if resp.status_code == 200:
                    text = resp.text
                    emails = set(EMAIL_REGEX.findall(text))
                    for email in emails:
                        if self.is_valid_lead_email(email):
                            leads.append({
                                'email': email,
                                'name': f"Owner of {alt_domain}",
                                'company': alt_domain,
                                'source': f"RDAP WHOIS ({alt_domain})"
                            })
            except Exception:
                continue
        return leads

    def find_leads_via_search(self, target_domain: str) -> List[Dict[str, str]]:
        keywords = self.extract_niche_keywords(target_domain)
        search_query = f'"{keywords}" contact OR "email us" OR "@"'
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(search_query)}"
        
        leads = []
        try:
            resp = self.session.get(url, timeout=8)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                snippets = soup.find_all('a', class_='result__snippet')
                titles = soup.find_all('a', class_='result__title')
                
                text_corpus = " ".join([s.get_text() for s in snippets] + [t.get_text() for t in titles])
                emails = set(EMAIL_REGEX.findall(text_corpus))
                
                for email in emails:
                    if self.is_valid_lead_email(email):
                        domain_part = email.split('@')[-1]
                        leads.append({
                            'email': email,
                            'name': 'Decision Maker',
                            'company': domain_part,
                            'source': f'Search ({keywords})'
                        })
        except Exception:
            pass
            
        return leads

    def discover_leads_for_domain(self, target_domain: str) -> int:
        print(f"\n[*] Searching for leads interested in: {target_domain}...")
        found_count = 0
        
        rdap_leads = self.find_leads_via_rdap(target_domain)
        for lead in rdap_leads:
            if self.db.add_lead(target_domain, lead['email'], lead['name'], lead['company'], lead['source']):
                found_count += 1
                print(f"   [+] Found lead via WHOIS: {lead['email']} ({lead['company']})")

        search_leads = self.find_leads_via_search(target_domain)
        for lead in search_leads:
            if self.db.add_lead(target_domain, lead['email'], lead['name'], lead['company'], lead['source']):
                found_count += 1
                print(f"   [+] Found lead via Search: {lead['email']} ({lead['company']})")

        if found_count == 0:
            print(f"   [-] No new unique leads discovered for {target_domain}.")
        else:
            print(f"   [OK] Discovered {found_count} new leads for {target_domain}.")
            
        return found_count
