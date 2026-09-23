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