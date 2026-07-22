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

    def add_domains(self, domain_names: List[str]) -> Tuple[int, int]:
        added = 0
        skipped = 0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for dom in domain_names:
                clean_dom = dom.strip().lower()
                if not clean_dom:
                    continue
                try:
                    cursor.execute("INSERT INTO domains (domain_name) VALUES (?)", (clean_dom,))
                    added += 1
                except sqlite3.IntegrityError:
                    skipped += 1
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

    def get_leads_by_status(self, status: str) -> List[sqlite3.Row]:
        with self.get_connection() as conn:
            return conn.cursor().execute("SELECT * FROM leads WHERE status = ? ORDER BY id ASC", (status,)).fetchall()

    def get_all_leads(self) -> List[sqlite3.Row]:
        with self.get_connection() as conn:
            return conn.cursor().execute("SELECT * FROM leads ORDER BY created_at DESC").fetchall()

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
                WHERE status = 'SENT' AND date(sent_at) = date('now')
            """).fetchone()
            return res["cnt"] if res else 0
