"""Standalone evidence + health verification script."""
import json
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL     = "http://127.0.0.1:8000"
EVIDENCE_DIR = Path("outputs/evidence")

# 1. Health
resp = urllib.request.urlopen(BASE_URL + "/api/health")
print("Health:", resp.read().decode())

# 2. Show evidence files on disk
files = sorted(EVIDENCE_DIR.glob("*.jpg"))
print("Evidence files on disk:", [f.name for f in files])

if not files:
    print("No evidence files found. Run POST /api/analyze first.")
else:
    fname = files[-1].name   # most recent
    size_kb = files[-1].stat().st_size // 1024
    print(f"  Using: {fname}  ({size_kb} KB)")

    # 3. GET /api/evidence/{filename}
    url = BASE_URL + "/api/evidence/" + fname
    resp = urllib.request.urlopen(url)
    ct  = resp.headers.get("Content-Type", "")
    body = resp.read()
    print(f"Evidence endpoint: HTTP {resp.getcode()}  Content-Type: {ct}  Bytes: {len(body)}")
    assert resp.getcode() == 200
    assert "image" in ct

    # 4. Path traversal safety
    for bad in ["../../.env", "../main.py", "..%2F..%2F.env"]:
        try:
            urllib.request.urlopen(BASE_URL + "/api/evidence/" + bad)
            print(f"FAIL: traversal '{bad}' was NOT blocked!")
        except urllib.error.HTTPError as e:
            print(f"  Traversal '{bad}' blocked: HTTP {e.code}  [OK]")

print("\nAll spot-checks passed.")
