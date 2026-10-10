"""Verified local snapshots. Restore only into an empty, stopped workspace."""

import hashlib
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from app import config
from app.services import store


def backup(destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("Choose a new backup directory.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        root = Path(temp)
        with store.connect() as source, sqlite3.connect(root / "workspace.sqlite3") as target:
            source.backup(target)
        (root / "pdfs").mkdir()
        with sqlite3.connect(root / "workspace.sqlite3") as db:
            identities = [row[0] for row in db.execute("SELECT id FROM books")]
        manifest = {}
        for identity in identities:
            relative = f"pdfs/{identity}.pdf"
            shutil.copyfile(config.DATA_DIR / relative, root / relative)
            manifest[relative] = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        manifest["workspace.sqlite3"] = hashlib.sha256((root / "workspace.sqlite3").read_bytes()).hexdigest()
        (root / "manifest.json").write_text(json.dumps({"version": 1, "files": manifest}, indent=2))
        verify(root)
        # A complete snapshot appears at the destination only after verification.
        root.rename(destination)
    return destination


def verify(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("version") != 1:
        raise ValueError("Unknown snapshot format.")
    for relative, expected in manifest["files"].items():
        raw_path = root / relative
        path = raw_path.resolve()
        if not path.is_relative_to(root.resolve()) or raw_path.is_symlink():
            raise ValueError("Unsafe snapshot path.")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Snapshot checksum mismatch: {relative}")
    with sqlite3.connect(root / "workspace.sqlite3") as db:
        if (
            db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
            or db.execute("PRAGMA foreign_key_check").fetchall()
        ):
            raise ValueError("Snapshot database integrity failed.")
        for (identity,) in db.execute("SELECT id FROM books"):
            if f"pdfs/{identity}.pdf" not in manifest["files"]:
                raise ValueError("Snapshot is missing a document.")
    return manifest


def restore(snapshot, destination):
    snapshot, destination = Path(snapshot).resolve(), Path(destination).resolve()
    manifest = verify(snapshot)
    if destination.exists():
        raise ValueError("Restore into a new empty directory with the server stopped.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        root = Path(temp)
        for relative in manifest["files"]:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(snapshot / relative, target)
        with sqlite3.connect(root / "workspace.sqlite3") as db:
            db.execute("UPDATE jobs SET state='queued' WHERE state='running'")
        # Manifest describes original snapshot; a restored queue has changed.
        (root / "manifest.json").unlink(missing_ok=True)
        root.rename(destination)
    return destination
