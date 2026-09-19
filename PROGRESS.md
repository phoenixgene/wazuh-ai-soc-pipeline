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