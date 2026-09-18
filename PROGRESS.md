\# Project Progress Log



\## Phase 1 — Sysmon Installation

\- Installed Sysmon64 on Windows agent with SwiftOnSecurity config.

\- Reason: gives Wazuh visibility into process ancestry (what launched 

&#x20; what) for later MITRE ATT\&CK mapping.

\- Verified via `Get-Service Sysmon64` (status: Running) and Event Viewer 

&#x20; showing events under Microsoft-Windows-Sysmon/Operational.

\- Screenshots: docs/screenshots/phase1-sysmon/

