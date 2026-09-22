import json
import os
import sys
import hashlib
import shutil
import subprocess
from datetime import datetime

LOG_FILE = r"C:\Program Files (x86)\ossec-agent\active-response\active-responses.log"
QUARANTINE_DIR = r"C:\ProgramData\WazuhQuarantine"

def write_log(msg):
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"{now} active-response/bin/quarantine-threat.exe: {msg}\n")

def get_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    try:
        input_str = sys.stdin.readline()
        if not input_str:
            sys.exit(0)

        data = json.loads(input_str)
        command = data.get("command")

        if command == "check_keys":
            print('{"version":1,"origin":{"name":"quarantine-threat","module":"active-response"},"command":"check_keys","parameters":{"keys":[]}}')
            sys.stdout.flush()
            return

        file_path = data["parameters"]["alert"]["data"]["virustotal"]["source"]["file"]

        if not os.path.exists(file_path):
            write_log(f"Artifact not found on disk: {file_path}")
            return

        os.makedirs(QUARANTINE_DIR, exist_ok=True)
        file_hash = get_sha256(file_path)
        dest_filename = f"{file_hash}.locked"
        dest_path = os.path.join(QUARANTINE_DIR, dest_filename)

        shutil.move(file_path, dest_path)

        subprocess.run(
            f'icacls "{dest_path}" /inheritance:r /grant:r Administrators:F /grant:r SYSTEM:F',
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        write_log(f"SUCCESS: Quarantined '{file_path}' to '{dest_path}' [SHA256: {file_hash}]")

    except Exception as e:
        write_log(f"ERROR: Failed quarantine procedure: {str(e)}")

if __name__ == "__main__":
    main()