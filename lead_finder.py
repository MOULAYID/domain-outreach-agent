import time
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from database import DatabaseManager
from enrichment import B2BLeadEnricher

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

DISCARD_EMAILS = {
    # Privacy Proxies & WHOIS Services
    'privacyprotect', 'whoisproxy', 'contactprivacy', 'domainprivacy', 
    'selectuser', 'domainsbyproxy', 'identityprotect', 'anonymousemail',
    'whoisrequest', 'privacyguard', 'proxyname', 'whoisguard', 'withheldforprivacy',
    # Registrars & Registries
    'pir.org', 'namebright.com', 'godaddy.com', 'namecheap.com', 'tucows.com',
    'enom.com', 'sedo.com', 'dan.com', 'hugedomains.com', 'domainmarket.com',
    'secureserver.net', 'markmonitor', 'cscglobal', 'gandi.net', 'networksolutions',
    'dynadot.com', 'porkbun.com', 'ovh.net', 'ionos.com', 'hostinger.com', 'verisign.com',
    'cloudflare.com', 'afternic.com', 'uniregistry.com', 'wildwestdomains.com',
    'aws.com', 'atom.com', 'gname.com',
    # Generic Roles & Prefixes
    'abuse@', 'postmaster@', 'webmaster@', 'hostmaster@', 'registrar@',
    'admin@', 'administrator@', 'support@', 'info@', 'sales@', 'contact@',
    'whois@', 'billing@', 'help@', 'dns@', 'noc@', 'privacy@', 'legal@',
    'compliance@', 'security@', 'service@', 'marketing@', 'press@', 'media@',
    'misuse@', 'trustandsafety@'
}

class LeadFinder:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.enricher = B2BLeadEnricher()
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
                time.sleep(0.5)
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
        
        # Method 1: TLD Competitor RDAP/WHOIS
        rdap_leads = self.find_leads_via_rdap(target_domain)
        for lead in rdap_leads:
            if self.db.add_lead(target_domain, lead['email'], lead['name'], lead['company'], lead['source']):
                found_count += 1
                print(f"   [+] Found lead via WHOIS: {lead['email']} ({lead['company']})")

        # Method 2: Niche Search Query Scraping
        search_leads = self.find_leads_via_search(target_domain)
        for lead in search_leads:
            if self.db.add_lead(target_domain, lead['email'], lead['name'], lead['company'], lead['source']):
                found_count += 1
                print(f"   [+] Found lead via Search: {lead['email']} ({lead['company']})")

        # Method 3: B2B API Enrichment (Hunter.io - Query only if free methods found 0 leads)
        if found_count == 0 and self.enricher.hunter_api_key:
            api_lead = self.enricher.find_lead_for_domain(target_domain)
            if api_lead:
                if self.db.add_lead(target_domain, api_lead['lead_email'], api_lead['lead_name'], api_lead['company_name'], api_lead['source']):
                    found_count += 1
                    print(f"   [+] Found lead via Hunter API: {api_lead['lead_email']} ({api_lead['company_name']})")

        if found_count == 0:
            print(f"   [-] No new unique leads discovered for {target_domain}.")
        else:
            print(f"   [OK] Discovered {found_count} new leads for {target_domain}.")
            
        return found_count
