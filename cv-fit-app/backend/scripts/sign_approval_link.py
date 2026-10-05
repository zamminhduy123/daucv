#!/usr/bin/env python3
"""Regenerate a manual-payment approval link.

Outside development, the signed approval link is never written to logs. If a
request could not be delivered to Telegram, the backend logs an error with
user_id, package_id and timestamp. Run this on the server (same env as the
backend) to rebuild the link:

    python scripts/sign_approval_link.py <user_id> <package_id> <timestamp>

The link still expires 7 days after <timestamp>, and approving it twice credits
only once.
"""

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.api.routes.billing import PACKAGES, build_approval_url  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("user_id")
    parser.add_argument("package_id", choices=sorted(PACKAGES))
    parser.add_argument("timestamp", type=int)
    args = parser.parse_args()
    print(build_approval_url(args.user_id, args.package_id, args.timestamp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
