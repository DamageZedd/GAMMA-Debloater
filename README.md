# S.T.A.L.K.E.R. G.A.M.M.A. Debloater & Storage Optimizer

A standalone GUI utility for the S.T.A.L.K.E.R. G.A.M.M.A. community to safely analyze, back up, and remove unused/disabled mods, installer download archives, and temporary backups to reclaim tens of gigabytes of SSD space.

---

## 💾 Download

No Python installation required:

- **[Latest GitHub Release (v1.0.2)](https://github.com/DamageZedd/GAMMA-Debloater/releases/latest)**:
  - 📦 **[GAMMA_Debloater.exe](https://github.com/DamageZedd/GAMMA-Debloater/releases/download/v1.0.2/GAMMA_Debloater.exe)** (Standalone single-file executable)
  - 🗜️ **[GAMMA_Debloater_v1.0.2.7z](https://github.com/DamageZedd/GAMMA-Debloater/releases/download/v1.0.2/GAMMA_Debloater_v1.0.2.7z)** (Compressed 7-Zip package)
- **Repository Binary**: Also available directly in the [`bin/`](bin/GAMMA_Debloater.exe) folder of this repository.
- **Changelog**: See [`CHANGELOG.md`](CHANGELOG.md) for full version release notes.

---

## Key Features

- **Zero-Config Auto Detection**: Automatically locates your G.A.M.M.A. folder (`C:\GAMMA`), detects installed profiles, and finds secondary drives for backup (e.g. `D:\GAMMA_Debloat_Backup`).
- **Flexible Removal Scopes**:
  - **Safe Mode (Multi-Profile)**: Only removes mods that are disabled across *all* profiles, guaranteeing that every single MO2 profile remains 100% playable.
  - **Active Profile Mode**: Focuses specifically on the profile you are actively playing to maximize freed space.
  - **Custom Profile**: Pick any specific profile from a dropdown list.
- **Cache Clean-Up**:
  - Installer download archives (`C:\GAMMA\downloads`)
  - Legacy/pre-split backups (`C:\GAMMA\mods_backup`)
- **Built-in Safety Protections**:
  - **Seasons of the Zone Protection**: Preserves all dynamic season texture packs (`CCon Spring`, `Summer`, `Autumn`, `Dead`, `INVERNO`, etc.) so the dynamic calendar switcher never crashes or loses textures.
  - **MO2 Separator Protection**: Keeps all `*_separator` directories in place so Mod Organizer UI category headers remain intact.
  - **Profile Load Order Backups**: Automatically backs up full `modlist.txt`, `lockedorder.txt`, and profile configurations.
  - **Byte & File-Count Verification**: Verifies every file copy before deleting the source on C:.
- **Drag-and-Drop Restorable**: The generated backup folder can be restored either through the built-in "Restore" GUI tab, a one-click `RESTORE_TO_GAMMA.bat` script, or by dragging and dropping folders back into `C:\GAMMA`.
- **Searchable Itemized Preview**: Search, inspect, and toggle individual mods on or off before executing removal.

---

## How to Run

### Option 1: Double-Click the Launcher
Simply double-click `run_debloater.bat` or `gamma_debloater.pyw`.

### Option 2: Run via Terminal
```bash
python gamma_debloater.py
```

---

## How to Build a Standalone `.exe` for Distribution

If you want to compile the standalone binary from source:

```bash
pip install customtkinter pyinstaller
pyinstaller --noconfirm --onefile --noconsole --name "GAMMA_Debloater" --collect-all customtkinter gamma_debloater.py
```

The resulting `GAMMA_Debloater.exe` is completely self-contained in `dist/` and runs on any 64-bit Windows PC without requiring Python.
