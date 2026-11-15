"""
Authentication, password hashing, and session management.
Uses PBKDF2-HMAC-SHA256 with hmac.compare_digest for constant-time verification.
"""

import hashlib
import os
import binascii
import hmac
from typing import Optional, Tuple


def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with a fresh random salt.
    Returns: (password_hash_hex, salt_hex)
    """
    if salt is None:
        salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        iterations=100_000
    )
    salt_hex = binascii.hexlify(salt).decode('ascii')
    hash_hex = binascii.hexlify(hashed).decode('ascii')
    return hash_hex, salt_hex


def verify_password(stored_hash: str, stored_salt: str, provided_password: str) -> bool:
    """
    Verify a provided password against stored hash and salt using constant-time comparison.
    """
    if not stored_hash or not stored_salt or not provided_password:
        return False

    try:
        salt_bytes = binascii.unhexlify(stored_salt.encode('ascii'))
        new_hash = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode('utf-8'),
            salt_bytes,
            iterations=100_000
        )
        new_hash_hex = binascii.hexlify(new_hash).decode('ascii')
        return hmac.compare_digest(new_hash_hex, stored_hash)
    except Exception:
        return False


class Session:
    current_user: Optional[dict] = None

    @classmethod
    def login(cls, user_dict: dict):
        cls.current_user = user_dict

    @classmethod
    def logout(cls):
        cls.current_user = None

    @classmethod
    def get_username(cls) -> str:
        if cls.current_user and isinstance(cls.current_user, dict):
            return cls.current_user.get("username", "User")
        return "Guest"

    @classmethod
    def get_role(cls) -> str:
        if cls.current_user and isinstance(cls.current_user, dict):
            return cls.current_user.get("role", "admin")
        return "admin"

    @classmethod
    def is_authenticated(cls) -> bool:
        return cls.current_user is not None
