# Changelog

All notable changes to the **S.T.A.L.K.E.R. G.A.M.M.A. Debloater & Storage Optimizer** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.1] - 2026-10-15

### Added
- **Real-Time Debloat Telemetry Monitor**: Completely overhauled the execution modal with a live military HUD interface streaming file system migrations in real time.
- **Live Progress Percentage**: Integrated dynamic decimal progress calculation weighted across total bytes and operation phases (`0.0%` → `100.0%`).
- **HUD Telemetry Cards**:
  - `PROGRESS`: Live percentage display with real-time mod counter (`X / Y Mods Relocated`).
  - `STORAGE RECLAIMED`: Running total of storage reclaimed on the primary SSD (`X.XX / Y.YY GB`).
  - `EXECUTION PHASE`: Active protocol stage (`PHASE 1/5: PROFILES`, `PHASE 2/5: MODS`, `PHASE 3/5: DOWNLOADS`, etc.).
  - `INTEGRITY SHIELD`: Real-time byte-exact verification status indicator (`VERIFYING` → `SECURED`).
- **Live Active Target Banner**: High-contrast banner displaying the exact mod name, folder size, and file count currently in flight.
- **Embedded In-Monitor Progress Bar**: Visual progress bar located directly within the telemetry monitor dialog.
- **Live Stopwatch**: Real-time elapsed execution timer (`⏱ ELAPSED: HH:MM:SS`) tracking total debloat runtime.
- **Telemetry Controls**:
  - `📋 Copy Log`: One-click copy of the entire telemetry log to the system clipboard.
  - `✓ CLOSE MONITOR`: Illuminated completion button that activates once all operations have completed and passed verification.
- **Restoration Telemetry Monitor**: Added dedicated live telemetry streaming window for the "Restore Vault" tab, displaying real-time output from the native PowerShell restore script (`RESTORE_TO_GAMMA.ps1`).

### Changed
- **Granular Per-Mod Logging**: Debloat protocol now logs every single mod transfer, destination verification, and source deletion instead of batch logging every 10 mods.
- **Resilient Robocopy Error Handling**: Wrapped per-mod transfers in granular exception guards so an individual locked file does not abort the debloat protocol for remaining mods. Source files are strictly preserved if any verification mismatch occurs.

---

## [1.0.0] - 2026-10-15

### Added
- **Initial Release of S.T.A.L.K.E.R. G.A.M.M.A. Debloater & Storage Optimizer (AAA Edition)**.
- **Zero-Config Auto Detection**: Automatic path resolution for `C:\GAMMA`, active MO2 profiles, and secondary backup storage drives.
- **Flexible Scope Modes**:
  - *Safe Mode (All Profiles)*: Preserves any mod enabled in at least one profile.
  - *Active Profile Mode*: Cleans storage based strictly on the currently played profile.
  - *Custom Specific Profile*: Targeted profile selection via dropdown.
- **Built-in Safety Protections**:
  - *Seasons of the Zone Shield*: Guarantees texture packs for the dynamic seasonal calendar are never deleted.
  - *MO2 UI Separator Shield*: Retains all virtual category folders (`*_separator`).
  - *Load Order Preservation*: Automatic backup snapshots of `modlist.txt` before modification.
- **Atomic Robocopy Transfers**: Multi-threaded transfers with byte-level size and file-count verification before source deletion.
- **Restoration Suite**: One-click restore via GUI, standalone `RESTORE_TO_GAMMA.bat` / `.ps1`, and full drag-and-drop support.
- **Searchable Itemized Inventory**: Interactive dark green zebra table to filter, inspect, and toggle individual mods.
