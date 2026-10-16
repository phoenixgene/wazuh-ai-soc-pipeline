\# Project Progress Log


## Phase 1 — Sysmon Installation
- Installed Sysmon64 on the Windows agent with the SwiftOnSecurity 
  config.
- Reason: gives Wazuh visibility into process ancestry (what launched 
  what), needed later for MITRE ATT&CK mapping.
- Verified via Get-Service (status: Running) and Event Viewer, which 
  showed events logging under Microsoft-Windows-Sysmon/Operational.
- Screenshots: docs/screenshots/phase1-sysmon/


## Phase 2 — Wazuh FIM + Sysmon Ingestion
- Added config to watch C:\Users\Public\Downloads for new files in 
  real time, and forward Sysmon logs to Wazuh.
- Found the Wazuh agent service was stopped — started it manually.
- Tested FIM by dropping a file in Downloads. First try showed nothing 
  (Wazuh runs a baseline scan on startup before real-time detection 
  kicks in) — second test triggered a proper alert.
- Sysmon ingestion looked empty at first, but I was checking the wrong 
  field. Once I filtered on the correct one, 215 Sysmon events showed 
  up — confirmed working.
- Spotted a recurring "DLL search order hijack" alert tied to Windows 
  Update files — likely a false positive, but good practice spotting 
  and triaging it like a real analyst would.
- Screenshots: docs/screenshots/phase2-wazuh-fim/

## Phase 3 — Forensic Quarantine Script
- Installed Python 3.14 and PyInstaller on the Windows agent (hit a 
  pip metadata-generation error from a flaky connection — fixed with 
  pip cache purge before reinstalling).
- Wrote quarantine-threat.py: reads a JSON alert piped in via stdin, 
  extracts the malicious file's path, calculates its SHA256 hash, 
  moves it to C:\ProgramData\WazuhQuarantine renamed as <hash>.locked, 
  then uses icacls to restrict access to SYSTEM/Administrators only. 
  Deletion is avoided on purpose to preserve forensic evidence.
- Compiled it to quarantine-threat.exe with PyInstaller and deployed 
  it to Wazuh's active-response\bin folder.
- Manually tested by piping a fake alert JSON into the .exe: confirmed 
  the file was hashed, moved, and renamed correctly; confirmed the 
  original was gone from its source location; confirmed via Get-Acl 
  that only SYSTEM and Administrators have access to the quarantined 
  file.
- Screenshots: docs/screenshots/phase3-quarantine/

Note: quarantine script does not currently capture original file 
timestamps/owner metadata before moving. Chain of custody is preserved 
via SHA256 hash and full logging, but richer forensic metadata capture 
is a known area for future improvement.

## Phase 4 — VirusTotal Integration + Automatic Active Response
- Added VirusTotal integration, a quarantine-threat-win command 
  definition, and an active-response rule to ossec.conf on the Wazuh 
  manager. Backed up the original config first.
- Restarted wazuh-manager and confirmed the integration loaded via 
  ossec.log ("Enabling integration for: virustotal").
- First EICAR test failed to trigger quarantine — investigated and 
  found Windows Defender deleted the test file before Wazuh's 
  pipeline could react. Fixed with a Defender exclusion on the 
  monitored Downloads folders. This mirrors a real practice in 
  production SOC environments, where the security monitoring platform 
  needs priority access over consumer AV on watched paths.
- Second EICAR test succeeded end-to-end, fully automatically: FIM 
  detected the file (rule 554) -> VirusTotal flagged it, 63/70+ 
  engines (rule 87105) -> active-response fired -> quarantine script 
  ran automatically, hashing, moving, and locking the file with no 
  manual trigger. Confirmed via active-responses.log and a new hash 
  in the quarantine folder.
- Also noticed Sysmon logging the quarantine script's own actions 
  (icacls call flagged as "suspicious cmd shell execution") — a 
  good example of expected noise from legitimate defensive tooling.
- Screenshots: docs/screenshots/phase4-virustotal/


## Phase 5 — n8n Setup + Webhook Trigger
- Ran n8n as a Docker container on the Wazuh manager VM (image: 
  n8nio/n8n), with a persistent volume so workflows survive container 
  restarts.
- Hit a container-permissions issue running Docker without sudo (group 
  membership hadn't taken effect in the terminal session) - worked 
  around it by using sudo consistently for Docker commands.
- Noticed the container doesn't auto-start after being idle/stopped - 
  needs a manual `docker start n8n` each session for now.
- Completed n8n's first-time setup and created an owner account.
- Built the first workflow node: a Webhook trigger, configured as 
  POST on path /wazuh-alerts. This will be the entry point Wazuh's 
  alert forwarder sends data to.
- Verified it works with a manual curl POST request - the webhook 
  correctly captured the full JSON payload and headers.
- Screenshots: docs/screenshots/phase5-n8n/

## Phase 5 (cont.) — PII Redaction Code Node
- Added a second n8n node (Code, JavaScript) that takes the raw Wazuh 
  alert and extracts only the fields needed downstream (alert ID, 
  agent info, file path, hash, VirusTotal results), discarding the 
  rest.
- Implemented regex-based redaction: internal IP addresses (RFC 1918 
  ranges) get replaced with [INTERNAL_IP_MASKED], and Windows 
  usernames in file paths get replaced with [CORP_USER_REDACTED] - so 
  no internal network/user details reach the external Gemini API 
  later in the pipeline.
- Hit a JSON escaping bug on first attempt (single vs double 
  backslashes broke JSON.parse) - fixed and re-tested.
- Verified with a fake Wazuh-shaped alert via curl containing a real 
  internal IP and username: both correctly redacted in the output, 
  all other fields passed through intact.
- Screenshots: docs/screenshots/phase5-n8n/



Note: the hash-cache node's logic was verified correct by inspection, 
but n8n's static data feature only persists when a workflow is active 
and triggered for real (not during manual "Execute step" testing, per 
n8n's own docs). Full cache-hit behavior will be verified once the 
complete pipeline is built and activated.



## Phase 5 (cont.) — Google Gemini Triage Node
- Added a Google Gemini node (model: gemini-3.5-flash after gemini-2.5-flash 
  was deprecated for new API users - model names have moved on since the 
  project's original architecture was written).
- Structured the prompt using n8n's separate "System Message" option 
  (found under the node's Options menu) for the analyst persona/
  instructions, and a User-role message for the actual telemetry data.
- Hit two real API errors along the way: a deprecated model ID, and a 
  temporary "model overloaded" error on a very new preview model - 
  switched to a more available, stable flash model to resolve both.
- First test run revealed a subtler bug: the Prompt field defaulted to 
  "Fixed" mode, so n8n treated {{ }} template syntax as literal text 
  instead of evaluating it - Gemini wrote a well-structured briefing 
  around literal placeholder strings instead of real data. Fixed by 
  switching the field to "Expression" mode.
- Second test succeeded fully: Gemini generated a complete, accurate 
  incident briefing with correct MITRE ATT&CK mapping, properly 
  redacted IP/username, accurate VirusTotal stats, correct cache 
  status, and three specific SOC recommendations - matching every 
  requirement in the system prompt.
- Screenshots: docs/screenshots/phase5-n8n/


## Phase 5 (cont.) — Discord Posting Node, End-to-End Success
- Added an HTTP Request node to POST Gemini's briefing to Discord's 
  API, with Authorization header (Bot token) and three interactive 
  buttons (Isolate Host, Review Quarantined Artifact, Close Incident).
- Hit a JSON Body "Fixed vs Expression" bug again (same root cause as 
  the Gemini prompt issue) - fixed by moving payload construction into 
  a dedicated Code node using JSON.stringify(), eliminating manual 
  JSON-in-a-text-field errors entirely.
- Hit a double-encoding bug (stringifying twice) causing a Discord 
  "Bad Request" - fixed by returning a real object from the Code node 
  and letting the HTTP node's own expression stringify it once.
- Hit a second Bad Request once that was fixed - diagnosed as Discord's 
  2000-character message limit being exceeded by Gemini's full 
  briefing. Added a truncation safeguard in the Code node.
- CONFIRMED FULL END-TO-END PIPELINE SUCCESS: a simulated Wazuh alert 
  flows through Webhook -> PII/IP redaction -> hash cache check -> 
  Gemini AI triage generation -> posted live to Discord with working 
  interactive buttons. This is the complete core architecture of the 
  project, verified working.
- Screenshots: docs/screenshots/phase5-n8n/

- Exported the complete n8n workflow as soc-triage-pipeline.json and 
  added it to n8n-workflows/. Manually redacted the Discord bot token 
  (which had been typed directly into an HTTP header rather than 
  stored via n8n's credential system, unlike the Gemini key) before 
  committing - real token replaced with a placeholder.



## Phase 6 — Human-in-the-Loop Discord Interactions (scoped out)
- Went on to build the "Isolate Host" action. Found that Wazuh's
  built-in netsh script only blocks a single IP address, not a whole
  machine, so I started writing my own isolation program (Windows
  firewall rules blocking everything except the Wazuh manager). Its
  first tests failed with no clear error, and it was tangled up with
  unrelated problems (the Wazuh manager failing to start after boots,
  the Windows VM losing its network).
- Decided to scope out host isolation and all Discord buttons. The
  automated part of the project already contains the threat and
  informs the analyst; isolation is listed as future work that would
  need an approval step. Stopped ngrok and removed the isolation
  rules and program.



## Phases 7 & 9 — Real Alerts to n8n and End-to-End Test
- Wrote a forwarder script on the Wazuh manager (custom-n8n.py) that
  sends each VirusTotal alert to n8n's webhook. Checked Wazuh's rules
  for custom integrations first (argument order, file name,
  permissions) instead of copying a script blindly.
- Looked at a real VirusTotal alert: it only carries md5 and sha1,
  not sha256. Updated the redaction node to take the SHA256 from the
  permalink URL, so the hash cache works on a real hash instead of
  "UNKNOWN" for every alert.
- Tested the redaction node and the forwarder by hand with a
  real-format alert before changing Wazuh's config.
- Added the integration block to ossec.conf (backed up the file first)
  and restarted the manager.
- Gemini hit "high demand" errors on real runs; switching to a lighter
  Flash model fixed it. A production version would need retry logic,
  since shared AI APIs get overloaded.
- Real end-to-end test: a new EICAR file on the Windows VM was
  quarantined, flagged by VirusTotal, forwarded by Wazuh, redacted,
  summarised by Gemini and posted to Discord with no manual steps. An
  earlier attempt failed because the Windows agent had disconnected
  from the manager - found by checking the agent status, not guessing.
- Reviewed what data leaves the network: only the file hash goes to
  VirusTotal, the file itself never leaves the endpoint, and Gemini
  receives a redacted alert. Limits noted: free-tier Gemini data
  terms, Discord as a consumer chat app, Defender exclusions on the
  monitored folders, no authentication on the webhook, IPv4 only.
- Confirmed the hash cache works on a published workflow: a repeat of 
  the same alert was reported as served from the local cache.
- Screenshots: docs/screenshots/phase7-discord/ and phase9-testing/

