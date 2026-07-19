#!/usr/bin/env python3
"""
ew² Token Generator
Run this script after receiving Pix payment to generate a license token.

Usage:
    python generate_license.py
"""

import secrets
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Data directory
if sys.platform == "win32":
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "ew2"
else:
    DATA_DIR = Path.home() / ".local" / "share" / "ew2"

LOG_FILE = DATA_DIR / "token_log.json"


def generate_token():
    """Generate a new token in EW2-XXXXXXXX-XXXXXXXX-XXXXXXXX format."""
    def hex_group():
        return secrets.token_hex(4).upper()
    return f"EW2-{hex_group()}-{hex_group()}-{hex_group()}"


def log_token(token, email, payment_amount):
    """Log the generated token for record keeping."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    log = []
    if LOG_FILE.exists():
        try:
            log = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            log = []
    
    log.append({
        "token": token,
        "email": email,
        "amount": payment_amount,
        "generated_at": datetime.now().isoformat(),
        "sent": False,
    })
    
    LOG_FILE.write_text(json.dumps(log, indent=2), encoding="utf-8")


def copy_to_clipboard(text):
    """Try to copy text to clipboard."""
    try:
        if sys.platform == "win32":
            import subprocess
            subprocess.run(["clip"], input=text.encode(), check=True)
            return True
        elif sys.platform == "darwin":
            import subprocess
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
            return True
        else:
            import subprocess
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
            return True
    except Exception:
        return False


def main():
    print("\n" + "=" * 50)
    print("  ew² License Token Generator")
    print("=" * 50)
    
    # Get buyer info
    email = input("\n  Buyer's email: ").strip()
    if not email or "@" not in email:
        print("  Invalid email. Token not generated.")
        return
    
    amount = input("  Payment amount (BRL) [R$ 15,50]: ").strip()
    if not amount:
        amount = "R$ 15,50"
    
    # Confirm
    print(f"\n  Buyer: {email}")
    print(f"  Amount: {amount}")
    confirm = input("\n  Generate token? (y/n): ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return
    
    # Generate token
    token = generate_token()
    
    # Log it
    log_token(token, email, amount)
    
    # Show token
    print("\n" + "=" * 50)
    print("  TOKEN GENERATED!")
    print("=" * 50)
    print(f"\n  Token: {token}")
    print(f"\n  Buyer: {email}")
    print(f"  Amount: {amount}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "=" * 50)
    
    # Try to copy to clipboard
    if copy_to_clipboard(token):
        print("\n  Token copied to clipboard!")
    else:
        print("\n  Copy the token above and send it to the buyer.")
    
    # Show email template
    print("\n" + "-" * 50)
    print("  EMAIL TEMPLATE:")
    print("-" * 50)
    print(f"""
  Subject: Your ew² License Token

  Hi,

  Thank you for purchasing ew² License!

  Your license token:
  {token}

  How to activate:
  1. Open ew²
  2. Select "Enter token"
  3. Paste the token above
  4. Done! Your machine is now licensed.

  This token is single-use and will be locked to your machine after activation.

  Need help? Join our Discord: https://discord.gg/7FXYFJAYsz

  Best regards,
  ew² Team
""")
    print("-" * 50)
    
    # Log file location
    print(f"\n  Token logged to: {LOG_FILE}")
    print("  (For your records)\n")


if __name__ == "__main__":
    main()
