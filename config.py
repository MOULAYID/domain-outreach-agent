import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the current directory
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.hostinger.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")
    SENDER_NAME = os.getenv("SENDER_NAME", "Domain Sales")
    
    MAX_DAILY_EMAILS = int(os.getenv("MAX_DAILY_EMAILS", 30))
    MIN_DELAY_SECONDS = int(os.getenv("MIN_DELAY_SECONDS", 180))
    MAX_DELAY_SECONDS = int(os.getenv("MAX_DELAY_SECONDS", 420))
    
    DB_FILE = Path(__file__).parent / os.getenv("DB_FILE", "outreach.db")
    HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")

    @classmethod
    def validate_smtp(cls) -> bool:
        if not cls.SMTP_USER or cls.SMTP_PASS == "change_me_to_your_real_password" or not cls.SMTP_PASS:
            return False
        return True
