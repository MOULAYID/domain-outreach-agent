import re
import socket
from typing import Tuple

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

class EmailVerifier:
    @staticmethod
    def verify_syntax(email: str) -> bool:
        if not email or not isinstance(email, str):
            return False
        return bool(EMAIL_REGEX.match(email.strip()))

    @staticmethod
    def verify_mx_record(email: str) -> bool:
        if not EmailVerifier.verify_syntax(email):
            return False
        domain = email.strip().split('@')[-1]
        try:
            # Check if domain host resolves
            socket.gethostbyname(domain)
            return True
        except Exception:
            return False

    @classmethod
    def is_deliverable(cls, email: str) -> Tuple[bool, str]:
        if not cls.verify_syntax(email):
            return False, "Invalid email syntax"
        if not cls.verify_mx_record(email):
            return False, "Domain host/MX lookup failed"
        return True, "Valid"
