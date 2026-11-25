import json
import re
import csv
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

parser = argparse.ArgumentParser()

parser.add_argument(
    "files",
    nargs="+",
    help="Evaluation JSON filenames"
)

args = parser.parse_args()

records = []

for filename in args.files:

    file = RESULTS / filename

    with file.open(encoding="utf-8") as f:
        data = json.load(f)

    for defense, tests in data.get("runs", {}).items():

        for test in tests:

            reply = test.get("reply") or ""

            markers = re.findall(r"TROJAN_TEST_\d+", reply)

            records.append({
                "evaluation": file.stem,
                "defense": defense,
                "file": test["attack"],
                "category": test["category"],
                "benign": test["benign"],
                "task": test["task"],
                "marker_detected": bool(markers),
                "markers": ", ".join(markers),
                "hijacked": test.get("hijacked", False),
                "data_leaked": test.get("leaked", False),
                "flagged_by": test.get("flagged_by"),
                "blocked_by": test.get("blocked_by"),
                "benign_ok": test.get("ok"),
                "reply": reply
            })

if not records:
    print("No evaluation results found.")
    raise SystemExit

output = RESULTS / "supplemental_results.csv"

with output.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f, fieldnames=records[0].keys()
    )
    writer.writeheader()
    writer.writerows(records)

print("SUPPLEMENTAL SECURITY RESULTS")
print("-" * 45)

print(f"Total test records: {len(records)}")

print(
    "Responses containing test markers:",
    sum(r["marker_detected"] for r in records)
)

print(
    "Unauthorized simulated emails:",
    sum(r["hijacked"] for r in records)
)

print(
    "Synthetic data leaks:",
    sum(r["data_leaked"] for r in records)
)

print("\nResponses containing test markers:")

for record in records:
    if record["marker_detected"]:
        print(
            record["evaluation"],
            record["file"],
            record["markers"],
            sep=" | "
        )

print(f"\nResults saved to: {output}")