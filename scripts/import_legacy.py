"""Explicitly re-upload legacy local PDFs into the new workspace. Does not modify originals."""

import argparse
from pathlib import Path
import requests
import os
from dotenv import load_dotenv

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", type=Path)
parser.add_argument("--url", default="http://127.0.0.1:8007")
args = parser.parse_args()
load_dotenv(Path(__file__).resolve().parents[1] / "backend" / ".env")
headers = {"X-DRAX-Key": os.getenv("DRAX_API_KEY", "")}
if not args.directory.is_dir():
    parser.error("Choose a directory containing your PDFs.")
for path in sorted(args.directory.glob("*.pdf")):
    with path.open("rb") as handle:
        response = requests.post(
            args.url + "/api/uploads",
            files={"file": (path.name, handle, "application/pdf")},
            headers=headers,
            timeout=60,
        )
    response.raise_for_status()
    book_id = response.json()["id"]
    result = requests.post(args.url + "/api/embed/" + book_id, headers=headers, timeout=300)
    result.raise_for_status()
    print("Imported one PDF:", book_id)
