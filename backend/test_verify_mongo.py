"""
POST /api/analyze verification script.
Returns: analysis_id, detection class, confidence, risk, evidence_image.
Does NOT print credentials.
"""
import json, urllib.request, urllib.error
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
IMG_PATH = Path("test_data/sample_sonar.jpg")
boundary = "SONARISverify1234"

with open(IMG_PATH, "rb") as f:
    img_data = f.read()

part_hdr = (
    "--" + boundary + "\r\n"
    'Content-Disposition: form-data; name="file"; filename="sample_sonar.jpg"\r\n'
    "Content-Type: image/jpeg\r\n\r\n"
).encode("utf-8")
part_end = ("\r\n--" + boundary + "--\r\n").encode("utf-8")
body = part_hdr + img_data + part_end

req = urllib.request.Request(
    BASE_URL + "/api/analyze",
    data=body,
    method="POST",
    headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
)

try:
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read().decode("utf-8"))
    print("HTTP STATUS : 200 OK")
    print("RESPONSE:")
    print(json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    body_text = e.read().decode("utf-8")
    print(f"HTTP STATUS : {e.code} {e.reason}")
    print("BODY:", body_text)
