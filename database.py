import sqlite3
from typing import List, Dict, Optional, Tuple
from config import Config

class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = str(db_path or Config.DB_FILE)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Domains table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS domains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain_name TEXT UNIQUE NOT NULL,
                    category TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Leads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_domain TEXT NOT NULL,
                    lead_email TEXT UNIQUE NOT NULL,
                    lead_name TEXT,
                    company_name TEXT,
                    source TEXT,
                    status TEXT DEFAULT 'DISCOVERED',
                    email_subject TEXT,
                    email_body TEXT,
                    sent_at DATETIME,
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (target_domain) REFERENCES domains(domain_name)
                );
            """)
            conn.commit()

    def add_domains(self, domains_data: List[Tuple[str, str]]) -> Tuple[int, int]:
        added = 0
        skipped = 0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for item in domains_data:
                if isinstance(item, (tuple, list)):
                    dom = item[0] if len(item) > 0 else ""
                    cat = item[1] if len(item) > 1 else ""
                else:
                    dom = str(item)
                    cat = ""

                clean_dom = dom.strip().lower()
                clean_cat = cat.strip() if cat else ""
                if not clean_dom:
                    continue
                
                # Check if domain already exists
                existing = cursor.execute("SELECT id, category FROM domains WHERE domain_name = ?", (clean_dom,)).fetchone()
                if existing:
                    if clean_cat and not existing["category"]:
                        cursor.execute("UPDATE domains SET category = ? WHERE domain_name = ?", (clean_cat, clean_dom))
                    skipped += 1
                else:
                    cursor.execute("INSERT INTO domains (domain_name, category) VALUES (?, ?)", (clean_dom, clean_cat))
                    added += 1
            conn.commit()
        return added, skipped

    def get_all_domains(self) -> List[sqlite3.Row]:
        with self.get_connection() as conn:
            return conn.cursor().execute("SELECT * FROM domains ORDER BY created_at DESC").fetchall()

    def add_lead(self, target_domain: str, lead_email: str, lead_name: str = "", company_name: str = "", source: str = "Web Search") -> bool:
        clean_email = lead_email.strip().lower()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO leads (target_domain, lead_email, lead_name, company_name, source, status)
                    VALUES (?, ?, ?, ?, ?, 'DISCOVERED')
                """, (target_domain, clean_email, lead_name, company_name, source))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Contact already exists in system
                return False

    def add_manual_leads(self, leads_data: List[Dict[str, str]]) -> Tuple[int, int]:
        added = 0
        skipped = 0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for lead in leads_data:
                dom = lead.get("target_domain", "").strip().lower()
                email = lead.get("lead_email", "").strip().lower()
                name = lead.get("lead_name", "").strip()
                company = lead.get("company_name", "").strip()
                field = lead.get("field", "").strip()

                if not dom or not email:
                    continue

                # Ensure domain exists in domains table
                existing_dom = cursor.execute("SELECT id, category FROM domains WHERE domain_name = ?", (dom,)).fetchone()
                if not existing_dom:
                    cursor.execute("INSERT INTO domains (domain_name, category) VALUES (?, ?)", (dom, field))
                elif field and not existing_dom["category"]:
                    cursor.execute("UPDATE domains SET category = ? WHERE domain_name = ?", (field, dom))

                try:
                    cursor.execute("""
                        INSERT INTO leads (target_domain, lead_email, lead_name, company_name, source, status)
                        VALUES (?, ?, ?, ?, 'Manual CSV Import', 'DISCOVERED')
                    """, (dom, email, name, company))
                    added += 1
                except sqlite3.IntegrityError:
                    skipped += 1
            conn.commit()
        return added, skipped

    def get_leads_by_status(self, status: str) -> List[sqlite3.Row]:
        with self.get_connection() as conn:
            return conn.cursor().execute("""
                SELECT l.*, d.category as domain_category 
                FROM leads l 
                LEFT JOIN domains d ON l.target_domain = d.domain_name 
                WHERE l.status = ? 
                ORDER BY l.id ASC
            """, (status,)).fetchall()

    def get_all_leads(self) -> List[sqlite3.Row]:
        with self.get_connection() as conn:
            return conn.cursor().execute("""
                SELECT l.*, d.category as domain_category 
                FROM leads l 
                LEFT JOIN domains d ON l.target_domain = d.domain_name 
                ORDER BY l.created_at DESC
            """).fetchall()

    def update_lead_draft(self, lead_id: int, subject: str, body: str):
        with self.get_connection() as conn:
            conn.cursor().execute("""
                UPDATE leads 
                SET email_subject = ?, email_body = ?, status = 'DRAFTED'
                WHERE id = ?
            """, (subject, body, lead_id))
            conn.commit()

    def mark_lead_sent(self, lead_id: int):
        with self.get_connection() as conn:
            conn.cursor().execute("""
                UPDATE leads 
                SET status = 'SENT', sent_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (lead_id,))
            conn.commit()

    def mark_lead_unsubscribed(self, lead_id: int):
        with self.get_connection() as conn:
            conn.cursor().execute("""
                UPDATE leads 
                SET status = 'UNSUBSCRIBED'
                WHERE id = ?
            """, (lead_id,))
            conn.commit()

    def mark_lead_replied(self, lead_id: int):
        with self.get_connection() as conn:
            conn.cursor().execute("""
                UPDATE leads 
                SET status = 'REPLIED'
                WHERE id = ?
            """, (lead_id,))
            conn.commit()

    def get_leads_due_for_followup(self, days_delay: int = 3) -> List[sqlite3.Row]:
        with self.get_connection() as conn:
            return conn.cursor().execute("""
                SELECT l.*, d.category as domain_category 
                FROM leads l 
                LEFT JOIN domains d ON l.target_domain = d.domain_name 
                WHERE (l.status = 'SENT' OR l.status = 'INITIAL_SENT') 
                  AND julianday('now') - julianday(l.sent_at) >= ?
                ORDER BY l.id ASC
            """, (days_delay,)).fetchall()

    def mark_lead_failed(self, lead_id: int, error_msg: str):
        with self.get_connection() as conn:
            conn.cursor().execute("""
                UPDATE leads 
                SET status = 'FAILED', error_message = ?
                WHERE id = ?
            """, (error_msg, lead_id))
            conn.commit()

    def get_sent_count_today(self) -> int:
        with self.get_connection() as conn:
            res = conn.cursor().execute("""
                SELECT COUNT(*) as cnt FROM leads 
                WHERE (status = 'SENT' OR status = 'INITIAL_SENT' OR status = 'FOLLOWUP_SENT') 
                  AND date(sent_at) = date('now')
            """).fetchone()
            return res["cnt"] if res else 0
