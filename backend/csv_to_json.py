#!/usr/bin/env python3
import pandas as pd
import json
from pathlib import Path

# ─── Compute paths ───────────────────────────────────────────────────────────
THIS_FILE   = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parent           # <project-root>/backend
CSV_PATH    = BACKEND_DIR / "data" / "generated_prompts.csv"
OUT_PATH    = BACKEND_DIR / "app" / "prompts" / "tutor_examples.json"

# ─── Load CSV ────────────────────────────────────────────────────────────────
if not CSV_PATH.exists():
    print(f"❌ CSV not found at {CSV_PATH}")
    exit(1)

df = pd.read_csv(CSV_PATH)
if "question" not in df.columns or "answer" not in df.columns:
    print("❌ CSV must have 'question' and 'answer' columns. Found:", df.columns.tolist())
    exit(1)

records = df[["question", "answer"]].to_dict(orient="records")

# ─── Write JSON ─────────────────────────────────────────────────────────────
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_PATH, "w") as f:
    json.dump(records, f, indent=2)

print(f"✅ Wrote {len(records)} examples to {OUT_PATH}")