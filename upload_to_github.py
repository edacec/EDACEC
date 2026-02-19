import os
import sys
import json
import base64
import urllib.parse
from pathlib import Path
import subprocess

OWNER = os.environ.get("GH_OWNER", "edacec")
REPO = os.environ.get("GH_REPO", "edacec")
BRANCH = os.environ.get("GH_BRANCH", "main")
TOKEN = os.environ.get("GITHUB_TOKEN")

if not TOKEN:
    print("ERROR: GITHUB_TOKEN not set in environment.")
    print("Run: read -s GITHUB_TOKEN; export GITHUB_TOKEN")
    sys.exit(1)

API = "https://api.github.com"
HEADERS = [
    f"Authorization: Bearer {TOKEN}",
    "Accept: application/vnd.github+json",
    "X-GitHub-Api-Version: 2022-11-28",
]

EXCLUDE = [
    "measurement_locked/runs/outputs/",
]
EXCLUDE_SUFFIXES = [".pyc", ".DS_Store"]
EXCLUDE_PARTS = ["__pycache__"]
EXCLUDE_EXACT = {"upload_to_github.sh"}

def run_curl(args):
    cmd = ["curl", "-sS"]
    for h in HEADERS:
        cmd += ["-H", h]
    cmd += args
    return subprocess.run(cmd, capture_output=True, text=True)

def should_exclude(rel: str) -> bool:
    if rel in EXCLUDE_EXACT:
        return True
    if any(part in rel for part in EXCLUDE_PARTS):
        return True
    if any(rel.endswith(suf) for suf in EXCLUDE_SUFFIXES):
        return True
    # Exclude JSONL outputs (we do NOT publish runtime data)
    if rel.startswith("measurement_locked/runs/outputs/") and rel.endswith(".jsonl"):
        return True
    if rel.startswith("measurement_locked/runs/outputs/_legacy/") and rel.endswith(".jsonl"):
        return True
    return False

def get_sha(rel: str) -> str | None:
    enc = urllib.parse.quote(rel, safe="")
    url = f"{API}/repos/{OWNER}/{REPO}/contents/{enc}?ref={BRANCH}"
    r = run_curl([url])
    if r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout)
        if isinstance(data, dict) and "sha" in data:
            return data["sha"]
    except Exception:
        return None
    return None

def put_file(path: Path, rel: str):
    content_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    sha = get_sha(rel)
    payload = {
        "message": f"Publish {rel}",
        "content": content_b64,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha

    enc = urllib.parse.quote(rel, safe="")
    url = f"{API}/repos/{OWNER}/{REPO}/contents/{enc}"

    r = run_curl(["-X", "PUT", url, "-d", json.dumps(payload)])
    if r.returncode != 0:
        print(f"ERROR uploading {rel}: curl failed")
        print(r.stderr)
        sys.exit(1)

    try:
        resp = json.loads(r.stdout)
        if "content" in resp and resp["content"] and "path" in resp["content"]:
            print(f"Uploaded: {resp['content']['path']}")
            return
        # Sometimes errors come back in JSON
        if "message" in resp and resp.get("message") != "OK":
            print(f"ERROR uploading {rel}: {resp.get('message')}")
            print(r.stdout)
            sys.exit(1)
    except Exception:
        pass

    print(f"Uploaded: {rel}")

def main():
    root = Path(".").resolve()
    files = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        if should_exclude(rel):
            continue
        files.append((p, rel))

    print(f"Files to upload: {len(files)}")
    for _, rel in files[:25]:
        print(" -", rel)
    print()

    for p, rel in files:
        put_file(p, rel)

    print("Done.")

if __name__ == "__main__":
    main()
