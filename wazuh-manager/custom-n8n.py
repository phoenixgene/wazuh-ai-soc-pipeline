#!/var/ossec/framework/python/bin/python3
import json
import sys
import requests

alert_file = sys.argv[1]
hook_url = sys.argv[3]
LOG = "/var/ossec/logs/integrations.log"


def log(msg):
    try:
        with open(LOG, "a") as f:
            f.write(f"custom-n8n: {msg}\n")
    except Exception:
        pass


try:
    with open(alert_file) as f:
        alert = json.load(f)
    r = requests.post(hook_url, json=alert, timeout=10)
    log(f"forwarded alert {alert.get('id')} to n8n, HTTP {r.status_code}")
except Exception as e:
    log(f"FAILED to forward alert: {e}")