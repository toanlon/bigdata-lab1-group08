import json, os, secrets
from pathlib import Path

root = Path("private")
root.mkdir(exist_ok=True, mode=0o700)

policies = {
    "owner": ["Admin", "Read", "Write", "List"],
    "ingestor": ["Read:research-raw", "Write:research-raw", "List:research-raw"],
    "analyst": ["Read:research-release", "List:research-release"]
}

identities = []
for name, actions in policies.items():
    key = "lab-" + secrets.token_hex(10)
    secret = secrets.token_urlsafe(32)
    identities.append({
        "name": name,
        "actions": actions,
        "credentials": [{"accessKey": key, "secretKey": secret}]
    })
    path = root / f"{name}.env"
    path.write_text(f"AWS_ACCESS_KEY_ID={key}\nAWS_SECRET_ACCESS_KEY={secret}\n")
    os.chmod(path, 0o600)

path = root / "s3.json"
path.write_text(json.dumps({"identities": identities}, indent=2))
os.chmod(path, 0o600)

Path("policies-redacted.json").write_text(json.dumps(policies, indent=2))