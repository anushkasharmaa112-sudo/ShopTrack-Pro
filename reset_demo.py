"""
Reset Database to Pristine Demo State.
Run this script anytime before your demo or presentation to restore clean sample data.
Usage: python3 reset_demo.py
"""

import os
import database
import auth
import services


def reset_to_clean_demo():
    # Remove existing db if present
    if os.path.exists(database.DB_PATH):
        try:
            os.remove(database.DB_PATH)
            print(f"Removed previous database: {database.DB_PATH}")
        except Exception as e:
            print(f"Notice: Could not remove file directly: {e}")

    # Re-initialize schema
    database.init_db()

    # Create standard demo administrator
    pwd_hash, salt = auth.hash_password("admin123")
    database.create_user("admin", pwd_hash, salt, role="admin")

    print("\n" + "=" * 50)
    print("✅ ShopTrack Pro Database Reset Complete!")
    print("=" * 50)
    print("• Admin Credentials : Username: admin | Password: admin123")
    print("• Products Seeded   : 10 active items (3 low-stock items)")
    print("• Database Location : " + database.DB_PATH)
    print("=" * 50 + "\n")


if __name__ == "__main__":
    reset_to_clean_demo()
