"""Run with PYTHONPATH=backend .venv/bin/python scripts/workspace_backup.py ..."""

import argparse
from app.services.backup import backup, restore

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verified DRAX backup/restore. Stop the server for a consistent file snapshot."
    )
    parser.add_argument("operation", choices=["backup", "restore"])
    parser.add_argument("destination")
    parser.add_argument("--snapshot")
    parser.add_argument("--server-stopped", action="store_true", required=True)
    args = parser.parse_args()
    if args.operation == "restore" and not args.snapshot:
        parser.error("restore requires --snapshot")
    print(backup(args.destination) if args.operation == "backup" else restore(args.snapshot, args.destination))
