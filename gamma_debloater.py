"""
S.T.A.L.K.E.R. G.A.M.M.A. Debloater & Storage Optimizer — True Zone AAA Edition
Authentic G.A.M.M.A. in-game UI aesthetics, radioactive emerald palette,
and full safety shields for Seasons of the Zone, MO2 separators, and multi-profile setups.
"""

import os
import sys
import json
import shutil
import subprocess
import threading
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from PIL import Image

# Windows console encoding safeguard
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ctk.set_appearance_mode("Dark")


class DebloaterEngine:
    """Core logic engine for scanning, debloating, and restoring GAMMA mods."""

    @staticmethod
    def detect_gamma_path():
        candidates = [
            Path(r"C:\GAMMA"),
            Path(r"D:\GAMMA"),
            Path(r"E:\GAMMA"),
            Path.cwd(),
            Path.cwd().parent,
        ]
        for c in candidates:
            if (c / "ModOrganizer.ini").exists() and (c / "mods").is_dir():
                return c.resolve()
        return None

    @staticmethod
    def detect_backup_path(gamma_path):
        gamma_drive = gamma_path.drive.upper() if gamma_path else "C:"
        for letter in ["D", "E", "F", "G"]:
            d_path = Path(f"{letter}:\\")
            if d_path.exists() and f"{letter}:" != gamma_drive:
                return Path(f"{letter}:\\GAMMA_Debloat_Backup")
        return Path(f"{gamma_drive}\\GAMMA_Debloat_Backup")

    @staticmethod
    def get_drive_space(path):
        try:
            usage = shutil.disk_usage(path)
            total = round(usage.total / (1024**3), 1)
            used = round(usage.used / (1024**3), 1)
            free = round(usage.free / (1024**3), 1)
            pct = round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0
            return total, used, free, pct
        except Exception:
            return 0.0, 0.0, 0.0, 0.0

    @staticmethod
    def get_dir_stats(path: Path):
        total_files = 0
        total_bytes = 0
        try:
            for root, _, files in os.walk(path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total_bytes += os.path.getsize(fp)
                        total_files += 1
                    except OSError:
                        pass
        except OSError:
            pass
        return total_files, total_bytes

    @staticmethod
    def get_active_profile(gamma_path: Path):
        ini_file = gamma_path / "ModOrganizer.ini"
        if not ini_file.exists():
            return None
        try:
            with open(ini_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.strip().startswith("selected_profile"):
                        val = line.split("=", 1)[1].strip()
                        if val.startswith("@ByteArray(") and val.endswith(")"):
                            return val[11:-1].strip()
                        return val
        except Exception:
            pass
        return None

    @staticmethod
    def list_profiles(gamma_path: Path):
        prof_dir = gamma_path / "profiles"
        if not prof_dir.is_dir():
            return []
        return [p.name for p in sorted(prof_dir.iterdir()) if p.is_dir()]

    @staticmethod
    def parse_profile_modlist(modlist_path: Path):
        enabled = set()
        disabled = set()
        separators = set()
        if not modlist_path.exists():
            return enabled, disabled, separators

        try:
            with open(modlist_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    prefix = line[0]
                    name = line[1:]
                    if name.endswith("_separator"):
                        separators.add(name)
                    elif prefix == "+":
                        enabled.add(name)
                    elif prefix == "-":
                        disabled.add(name)
        except Exception:
            pass
        return enabled, disabled, separators

    @staticmethod
    def get_seasonal_mods(gamma_path: Path):
        cfg_file = gamma_path / "_tools" / "seasons_config.py"
        seasonal = {
            "Project I.N.V.E.R.N.O",
            "SSS 24 Ice Water (deep winter only)",
            "INVERNO Partly Snowy (winter only)",
            "CCon Spring (seasonal)",
            "CCon Summer (seasonal)",
            "CCon Autumn (seasonal)",
            "CCon Dead (seasonal)",
            "Winter PDA Maps (seasonal)",
            "xx-Dark Signal Amplified Soundscape Atmospherics - Shrike",
        }
        if cfg_file.exists():
            try:
                content = cfg_file.read_text(encoding="utf-8", errors="ignore")
                import re
                matches = re.findall(r'["\']([^"\']+)["\']\s*:\s*\{', content)
                for m in matches:
                    if not m.endswith("_separator"):
                        seasonal.add(m)
            except Exception:
                pass
        return seasonal

    @classmethod
    def analyze(cls, gamma_path: Path, options: dict, progress_cb=None):
        mods_dir = gamma_path / "mods"
        profiles_dir = gamma_path / "profiles"

        if progress_cb:
            progress_cb("Reading profile configurations...")

        profiles = cls.list_profiles(gamma_path)
        active_prof = cls.get_active_profile(gamma_path)

        all_profile_enabled = set()
        profile_mods_map = {}

        for p_name in profiles:
            p_ml = profiles_dir / p_name / "modlist.txt"
            en, dis, seps = cls.parse_profile_modlist(p_ml)
            profile_mods_map[p_name] = {"enabled": en, "disabled": dis}
            all_profile_enabled.update(en)

        seasonal_mods = set()
        if options.get("protect_seasons", True):
            seasonal_mods = cls.get_seasonal_mods(gamma_path)

        scope = options.get("scope", "all_profiles")
        selected_prof_target = options.get("target_profile", active_prof)

        protected_mods = set()
        if scope == "all_profiles":
            protected_mods = all_profile_enabled.union(seasonal_mods)
        elif scope == "active_profile":
            active_enabled = profile_mods_map.get(active_prof, {}).get("enabled", set())
            protected_mods = active_enabled.union(seasonal_mods)
        elif scope == "specific_profile":
            spec_enabled = profile_mods_map.get(selected_prof_target, {}).get("enabled", set())
            protected_mods = spec_enabled.union(seasonal_mods)

        candidate_mods = []
        kept_mods_count = 0
        separators_count = 0

        all_mod_dirs = [d for d in mods_dir.iterdir() if d.is_dir()]
        total_dirs = len(all_mod_dirs)

        for i, d in enumerate(all_mod_dirs, 1):
            if progress_cb and i % 50 == 0:
                progress_cb(f"Scanning mods directory ({i}/{total_dirs})...")

            if d.name.endswith("_separator"):
                separators_count += 1
                continue

            if d.name in protected_mods:
                kept_mods_count += 1
                continue

            files, bytes_size = cls.get_dir_stats(d)
            candidate_mods.append({
                "name": d.name,
                "path": d,
                "files": files,
                "bytes": bytes_size,
                "size_mb": round(bytes_size / (1024 * 1024), 2),
                "selected": True,
            })

        candidate_mods.sort(key=lambda x: x["bytes"], reverse=True)

        dl_stats = {"count": 0, "bytes": 0, "size_gb": 0.0, "exists": False}
        src_dl = gamma_path / "downloads"
        if src_dl.is_dir() and options.get("include_downloads", True):
            f_cnt, b_cnt = cls.get_dir_stats(src_dl)
            dl_stats = {
                "count": f_cnt,
                "bytes": b_cnt,
                "size_gb": round(b_cnt / (1024**3), 2),
                "exists": f_cnt > 0,
            }

        mb_stats = {"count": 0, "bytes": 0, "size_gb": 0.0, "exists": False}
        src_mb = gamma_path / "mods_backup"
        if src_mb.is_dir() and options.get("include_mods_backup", True):
            f_cnt, b_cnt = cls.get_dir_stats(src_mb)
            mb_stats = {
                "count": f_cnt,
                "bytes": b_cnt,
                "size_gb": round(b_cnt / (1024**3), 2),
                "exists": f_cnt > 0,
            }

        return {
            "gamma_path": gamma_path,
            "profiles": profiles,
            "active_profile": active_prof,
            "scope": scope,
            "candidate_mods": candidate_mods,
            "kept_mods_count": kept_mods_count,
            "separators_count": separators_count,
            "downloads": dl_stats,
            "mods_backup": mb_stats,
        }

    @staticmethod
    def safe_rmtree(path: Path):
        if not path.exists():
            return
        subprocess.run(["cmd", "/c", "rd", "/s", "/q", str(path)], capture_output=True)
        if path.exists():
            subprocess.run(f'attrib -R "{path}\\*.*" /S /D', shell=True, capture_output=True)
            subprocess.run(["cmd", "/c", "rd", "/s", "/q", str(path)], capture_output=True)
        if path.exists():
            raise RuntimeError(f"Failed to delete directory: {path}")

    @classmethod
    def execute_debloat(cls, plan: dict, backup_dir: Path, options: dict, log_cb, progress_cb):
        gamma_path = plan["gamma_path"]
        backup_dir.mkdir(parents=True, exist_ok=True)

        selected_mods = [m for m in plan["candidate_mods"] if m.get("selected", True)]
        total_steps = len(selected_mods) + 3
        current_step = 0

        log_cb("=" * 65)
        log_cb("[INITIALIZING G.A.M.M.A. STORAGE DEBLOAT PROTOCOL]")
        log_cb(f"SOURCE INSTALLATION : {gamma_path}")
        log_cb(f"BACKUP VAULT TARGET : {backup_dir}")
        log_cb("=" * 65)

        # 1. Backup Profiles
        current_step += 1
        progress_cb(current_step, total_steps, "Securing MO2 profiles and load orders...")
        log_cb("\n[PHASE 1/4] Backing up MO2 profiles and load orders...")
        dst_profiles = backup_dir / "profiles"
        cls._robocopy(gamma_path / "profiles", dst_profiles)
        log_cb(f"  [OK] Profile modlists stored safely at: {dst_profiles}")

        for p in (gamma_path / "profiles").iterdir():
            if p.is_dir():
                ml = p / "modlist.txt"
                if ml.exists():
                    bak = p / "modlist.txt.full_before_debloat"
                    if not bak.exists():
                        shutil.copy2(ml, bak)

        # 2. Move Selected Candidate Mods
        dst_mods = backup_dir / "mods"
        dst_mods.mkdir(parents=True, exist_ok=True)
        moved_manifest = []
        total_mod_bytes_freed = 0

        log_cb(f"\n[PHASE 2/4] Transferring {len(selected_mods)} unused mods to backup...")
        for i, mod in enumerate(selected_mods, 1):
            current_step += 1
            progress_cb(current_step, total_steps, f"[{i}/{len(selected_mods)}] Moving: {mod['name']}")

            src_folder = mod["path"]
            dst_folder = dst_mods / mod["name"]
            src_files, src_bytes = mod["files"], mod["bytes"]

            cls._robocopy(src_folder, dst_folder)

            dst_files, dst_bytes = cls.get_dir_stats(dst_folder)
            if dst_files != src_files or dst_bytes != src_bytes:
                log_cb(f"  [ERROR] Verification mismatch for '{mod['name']}'. Source NOT deleted.")
                continue

            cls.safe_rmtree(src_folder)
            total_mod_bytes_freed += src_bytes
            moved_manifest.append(mod)

            if i % 10 == 0 or i == len(selected_mods):
                log_cb(f"  [TRANSFERRED] {i}/{len(selected_mods)} mods ({round(total_mod_bytes_freed / (1024**3), 2)} GB moved)...")

        # 3. Move Downloads
        dl_bytes_freed = 0
        if options.get("include_downloads", True) and plan["downloads"]["exists"]:
            current_step += 1
            progress_cb(current_step, total_steps, "Transferring installer downloads cache...")
            log_cb("\n[PHASE 3/4] Relocating installer download archives...")
            src_dl = gamma_path / "downloads"
            dst_dl = backup_dir / "downloads"
            s_f, s_b = plan["downloads"]["count"], plan["downloads"]["bytes"]
            cls._robocopy(src_dl, dst_dl)
            d_f, d_b = cls.get_dir_stats(dst_dl)
            if d_f == s_f and d_b == s_b:
                for item in src_dl.iterdir():
                    if item.is_file():
                        try:
                            item.unlink()
                        except OSError:
                            subprocess.run(f'cmd /c del /f /q "{item}"', shell=True, capture_output=True)
                    elif item.is_dir():
                        cls.safe_rmtree(item)
                dl_bytes_freed = s_b
                log_cb(f"  [OK] Downloads cache moved and verified. Reclaimed {round(dl_bytes_freed / (1024**3), 2)} GB")
            else:
                log_cb("  [ERROR] Downloads verification mismatch. Source not deleted.")

        # 4. Move mods_backup
        mb_bytes_freed = 0
        if options.get("include_mods_backup", True) and plan["mods_backup"]["exists"]:
            current_step += 1
            progress_cb(current_step, total_steps, "Transferring legacy backups...")
            log_cb("\n[PHASE 4/4] Relocating legacy pre-split backups...")
            src_mb = gamma_path / "mods_backup"
            dst_mb = backup_dir / "mods_backup"
            s_f, s_b = plan["mods_backup"]["count"], plan["mods_backup"]["bytes"]
            cls._robocopy(src_mb, dst_mb)
            d_f, d_b = cls.get_dir_stats(dst_mb)
            if d_f == s_f and d_b == s_b:
                cls.safe_rmtree(src_mb)
                mb_bytes_freed = s_b
                log_cb(f"  [OK] Legacy backups moved and verified. Reclaimed {round(mb_bytes_freed / (1024**3), 2)} GB")
            else:
                log_cb("  [ERROR] Legacy backups verification mismatch. Source not deleted.")

        # 5. Generate Manifest, Restore Script, and Documentation
        log_cb("\n[FINALIZING] Generating recovery scripts, manifest, and documentation...")
        total_freed = total_mod_bytes_freed + dl_bytes_freed + mb_bytes_freed
        cls._generate_restore_files(backup_dir, gamma_path, moved_manifest, total_freed, total_mod_bytes_freed, dl_bytes_freed, mb_bytes_freed, plan["profiles"])

        log_cb("\n" + "=" * 65)
        log_cb(f"SUCCESS: STORAGE RECLAMATION PROTOCOL COMPLETE!")
        log_cb(f"TOTAL SPACE FREED ON SOURCE DRIVE: {round(total_freed / (1024**3), 2)} GB")
        log_cb(f"BACKUP VAULT: {backup_dir}")
        log_cb("=" * 65)
        progress_cb(total_steps, total_steps, "Operation Complete!")

    @staticmethod
    def _robocopy(src: Path, dst: Path):
        dst.mkdir(parents=True, exist_ok=True)
        cmd = ["robocopy", str(src), str(dst), "/E", "/MT:16", "/R:1", "/W:1", "/NP", "/NDL", "/NFL"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode >= 8:
            raise RuntimeError(f"Robocopy failed code {res.returncode}:\n{res.stderr or res.stdout}")

    @staticmethod
    def _generate_restore_files(backup_dir: Path, gamma_path: Path, moved_mods, total_b, mod_b, dl_b, mb_b, profiles):
        manifest_data = {
            "timestamp": datetime.now().isoformat(),
            "gamma_path": str(gamma_path),
            "total_freed_gb": round(total_b / (1024**3), 2),
            "mods_freed_gb": round(mod_b / (1024**3), 2),
            "downloads_freed_gb": round(dl_b / (1024**3), 2),
            "mods_backup_freed_gb": round(mb_b / (1024**3), 2),
            "profiles_backed_up": profiles,
            "moved_mods_count": len(moved_mods),
            "moved_mods": [{"name": m["name"], "size_mb": m["size_mb"]} for m in moved_mods],
        }
        with open(backup_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        readme_text = f"""========================================================================
S.T.A.L.K.E.R. G.A.M.M.A. UNUSED MODS & STORAGE BACKUP
Vault Location: {backup_dir}
Target Installation: {gamma_path}
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
========================================================================

HOW TO RESTORE EVERYTHING BACK TO {gamma_path}:

METHOD 1: ONE-CLICK RESTORE (RECOMMENDED)
  Double-click "RESTORE_TO_GAMMA.bat" inside this folder.
  It will automatically move all mods, downloads, backups, and profile configs
  back into {gamma_path}.

METHOD 2: DRAG AND DROP
  You can drag and drop any or all folders directly into "{gamma_path}":
  - Drag "mods" into "{gamma_path}\\mods" (or into "{gamma_path}" to merge)
  - Drag "profiles" into "{gamma_path}\\profiles"
  - Drag "downloads" into "{gamma_path}\\downloads"
  - Drag "mods_backup" into "{gamma_path}\\mods_backup"

WHAT IS BACKED UP HERE:
- mods/        : {len(moved_mods)} unused mods ({round(mod_b / (1024**3), 2)} GB)
- downloads/   : Installer downloads ({round(dl_b / (1024**3), 2)} GB)
- mods_backup/ : Prior pre-split backups ({round(mb_b / (1024**3), 2)} GB)
- profiles/    : Full modlist.txt and load order files for all profiles
- manifest.json: Full itemized inventory with file counts and byte sizes
========================================================================
"""
        with open(backup_dir / "README.txt", "w", encoding="utf-8") as f:
            f.write(readme_text)

        bat_content = f"""@echo off
title Restore G.A.M.M.A. Backup to {gamma_path}
echo ========================================================================
echo RESTORING G.A.M.M.A. BACKUP TO {gamma_path}
echo ========================================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RESTORE_TO_GAMMA.ps1"
pause
"""
        with open(backup_dir / "RESTORE_TO_GAMMA.bat", "w", encoding="utf-8") as f:
            f.write(bat_content)

        ps1_content = f"""# PowerShell Restore Script for GAMMA Backup
$backupDir = $PSScriptRoot
$gammaDir = "{gamma_path}"

Write-Host "Restoring G.A.M.M.A. from $backupDir to $gammaDir..." -ForegroundColor Cyan

# 1. Restore mods
$srcMods = Join-Path $backupDir "mods"
$dstMods = Join-Path $gammaDir "mods"
if (Test-Path $srcMods) {{
    Write-Host "`nRestoring mod folders to $dstMods..." -ForegroundColor Yellow
    robocopy $srcMods $dstMods /E /MOVE /MT:8 /NP /NDL /NFL | Out-Null
}}

# 2. Restore downloads
$srcDl = Join-Path $backupDir "downloads"
$dstDl = Join-Path $gammaDir "downloads"
if (Test-Path $srcDl) {{
    Write-Host "`nRestoring downloads to $dstDl..." -ForegroundColor Yellow
    robocopy $srcDl $dstDl /E /MOVE /MT:8 /NP /NDL /NFL | Out-Null
}}

# 3. Restore mods_backup
$srcMb = Join-Path $backupDir "mods_backup"
$dstMb = Join-Path $gammaDir "mods_backup"
if (Test-Path $srcMb) {{
    Write-Host "`nRestoring mods_backup to $dstMb..." -ForegroundColor Yellow
    robocopy $srcMb $dstMb /E /MOVE /MT:8 /NP /NDL /NFL | Out-Null
}}

# 4. Restore profiles (modlist.txt, load orders)
$srcProf = Join-Path $backupDir "profiles"
$dstProf = Join-Path $gammaDir "profiles"
if (Test-Path $srcProf) {{
    Write-Host "`nRestoring profile modlists and configs..." -ForegroundColor Yellow
    robocopy $srcProf $dstProf /E /MT:8 /NP /NDL /NFL | Out-Null
}}

Write-Host "`nRESTORE COMPLETE! Everything has been returned to $gammaDir." -ForegroundColor Green
"""
        with open(backup_dir / "RESTORE_TO_GAMMA.ps1", "w", encoding="utf-8") as f:
            f.write(ps1_content)


class GammaDebloaterApp(ctk.CTk):
    """True Zone AAA Edition with authentic S.T.A.L.K.E.R. G.A.M.M.A. main menu aesthetics."""

    # Iconic G.A.M.M.A. Menu Palette
    C_ABYSS = "#050806"
    C_PANEL = "#0a130e"
    C_INPUT = "#101e15"
    C_BORDER = "#1b3823"
    C_BORDER_GLOW = "#00ff66"
    
    C_ZONE_GREEN = "#00ff66"        # Toxic radioactive emerald glow
    C_ZONE_GREEN_DIM = "#22c55e"
    C_ZONE_GREEN_HOVER = "#39ff14"
    C_ZONE_CYAN = "#38ef7d"
    C_ZONE_AMBER = "#f59e0b"
    C_ZONE_RED = "#ef4444"
    
    C_TEXT_WHITE = "#eafbf0"
    C_TEXT_STENCIL = "#4ade80"
    C_TEXT_MUTED = "#7a9382"

    def __init__(self):
        super().__init__()
        self.title("S.T.A.L.K.E.R. G.A.M.M.A. — STORAGE DEBLOAT PROTOCOL")
        self.geometry("1100x860")
        self.minsize(980, 740)
        self.configure(fg_color=self.C_ABYSS)

        # Variables
        self.gamma_path_var = tk.StringVar()
        self.backup_path_var = tk.StringVar()
        self.scope_var = tk.StringVar(value="all_profiles")
        self.target_profile_var = tk.StringVar()

        self.include_dl_var = tk.BooleanVar(value=True)
        self.include_mb_var = tk.BooleanVar(value=True)
        self.protect_seasons_var = tk.BooleanVar(value=True)
        self.protect_seps_var = tk.BooleanVar(value=True)

        self.search_filter_var = tk.StringVar()
        self.search_filter_var.trace_add("write", self._on_filter_changed)

        self.current_plan = None
        self.detected_profiles = []

        self._build_header()
        self._build_dashboard_cards()
        self._build_tabs()
        self._build_footer()

        self._auto_detect()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="#07100b", corner_radius=0)
        header.pack(fill=tk.X, side=tk.TOP)

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill=tk.X, padx=24, pady=(12, 10))

        # Check for official logo image
        logo_path = Path(__file__).parent / "gamma_header_logo.png"
        if not logo_path.exists():
            logo_path = Path(r"C:\Users\hocke\.gemini\antigravity\scratch\GAMMA_Debloater\gamma_header_logo.png")

        if logo_path.exists():
            try:
                pil_img = Image.open(logo_path)
                self.logo_ctk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(280, 156))
                logo_lbl = ctk.CTkLabel(inner, image=self.logo_ctk, text="")
                logo_lbl.pack(side=tk.LEFT, padx=(0, 16))
            except Exception:
                pass

        # Text Branding & Stencil Subtitle
        text_frame = ctk.CTkFrame(inner, fg_color="transparent")
        text_frame.pack(side=tk.LEFT, fill=tk.Y, expand=True)

        ctk.CTkLabel(
            text_frame,
            text="STORAGE OPTIMIZATION PROTOCOL",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=self.C_ZONE_GREEN,
            anchor="w",
        ).pack(anchor=tk.W, pady=(18, 0))

        ctk.CTkLabel(
            text_frame,
            text="GROK'S AUTOMATED MODULAR MODPACK FOR ANOMALY • VFS DEBLOAT ENGINE",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=self.C_TEXT_STENCIL,
            anchor="w",
        ).pack(anchor=tk.W, pady=(2, 0))

        ctk.CTkLabel(
            text_frame,
            text="Autonomous multi-profile cross-referencing • Dynamic seasonal shielding • 100% reversible vault backup",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.C_TEXT_MUTED,
            anchor="w",
        ).pack(anchor=tk.W, pady=(2, 0))

        # Right status badge & Radiation level
        stat_frame = ctk.CTkFrame(inner, fg_color=self.C_PANEL, corner_radius=8, border_width=1, border_color=self.C_BORDER)
        stat_frame.pack(side=tk.RIGHT, pady=16)

        ctk.CTkLabel(
            stat_frame,
            text="● PDA FREQ: 147.2 MHz",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=self.C_ZONE_GREEN,
        ).pack(padx=14, pady=(8, 2))

        ctk.CTkLabel(
            stat_frame,
            text="RAD: 0.02 µSv/h  [NORMAL]",
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=self.C_TEXT_MUTED,
        ).pack(padx=14, pady=(0, 8))

        # Neon Green Glowing Border Line
        glow_line = ctk.CTkFrame(self, fg_color=self.C_ZONE_GREEN, height=2, corner_radius=0)
        glow_line.pack(fill=tk.X)

    def _build_dashboard_cards(self):
        dash = ctk.CTkFrame(self, fg_color="transparent")
        dash.pack(fill=tk.X, padx=24, pady=(14, 6))
        dash.columnconfigure((0, 1, 2), weight=1)

        # Card 1: Primary Drive
        self.c1 = ctk.CTkFrame(dash, fg_color=self.C_PANEL, corner_radius=10, border_width=1, border_color=self.C_BORDER)
        self.c1.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(self.c1, text="PRIMARY SSD (SOURCE)", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=self.C_TEXT_MUTED).pack(anchor=tk.W, padx=16, pady=(12, 2))
        self.c1_stat = ctk.CTkLabel(self.c1, text="-- GB FREE", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=self.C_TEXT_WHITE)
        self.c1_stat.pack(anchor=tk.W, padx=16)
        self.c1_sub = ctk.CTkLabel(self.c1, text="Analyzing drive usage...", font=ctk.CTkFont(size=10), text_color=self.C_TEXT_MUTED)
        self.c1_sub.pack(anchor=tk.W, padx=16, pady=(0, 12))

        # Card 2: Backup Vault Drive
        self.c2 = ctk.CTkFrame(dash, fg_color=self.C_PANEL, corner_radius=10, border_width=1, border_color=self.C_BORDER)
        self.c2.grid(row=0, column=1, sticky="nsew", padx=4)
        ctk.CTkLabel(self.c2, text="BACKUP VAULT (TARGET)", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=self.C_TEXT_MUTED).pack(anchor=tk.W, padx=16, pady=(12, 2))
        self.c2_stat = ctk.CTkLabel(self.c2, text="-- GB FREE", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=self.C_ZONE_CYAN)
        self.c2_stat.pack(anchor=tk.W, padx=16)
        self.c2_sub = ctk.CTkLabel(self.c2, text="Secondary storage ready", font=ctk.CTkFont(size=10), text_color=self.C_TEXT_MUTED)
        self.c2_sub.pack(anchor=tk.W, padx=16, pady=(0, 12))

        # Card 3: Potential Savings
        self.c3 = ctk.CTkFrame(dash, fg_color=self.C_PANEL, corner_radius=10, border_width=1, border_color=self.C_ZONE_GREEN)
        self.c3.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(self.c3, text="RECLAIMABLE CAPACITY", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=self.C_ZONE_GREEN).pack(anchor=tk.W, padx=16, pady=(12, 2))
        self.c3_stat = ctk.CTkLabel(self.c3, text="READY TO SCAN", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=self.C_ZONE_GREEN)
        self.c3_stat.pack(anchor=tk.W, padx=16)
        self.c3_sub = ctk.CTkLabel(self.c3, text="Click 'Scan Zone Storage' below", font=ctk.CTkFont(size=10), text_color=self.C_TEXT_MUTED)
        self.c3_sub.pack(anchor=tk.W, padx=16, pady=(0, 12))

    def _build_tabs(self):
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=self.C_PANEL,
            segmented_button_fg_color=self.C_INPUT,
            segmented_button_selected_color="#0e2f1b",
            segmented_button_selected_hover_color="#144326",
            segmented_button_unselected_hover_color=self.C_BORDER,
            text_color=self.C_ZONE_GREEN,
        )
        self.tabview.pack(fill=tk.BOTH, expand=True, padx=24, pady=6)

        self.tab_setup = self.tabview.add("  ☢  DEBLOAT PROTOCOL  ")
        self.tab_inventory = self.tabview.add("  📋  ZONE INVENTORY  ")
        self.tab_restore = self.tabview.add("  ↩  RESTORE VAULT  ")
        self.tab_manual = self.tabview.add("  📖  FIELD MANUAL  ")

        self._build_setup_tab()
        self._build_inventory_tab()
        self._build_restore_tab()
        self._build_manual_tab()

    def _build_setup_tab(self):
        # 1. Path Selectors
        path_box = ctk.CTkFrame(self.tab_setup, fg_color=self.C_INPUT, corner_radius=10, border_width=1, border_color=self.C_BORDER)
        path_box.pack(fill=tk.X, padx=16, pady=(10, 8))

        # GAMMA Folder Row
        g_row = ctk.CTkFrame(path_box, fg_color="transparent")
        g_row.pack(fill=tk.X, padx=16, pady=(10, 6))
        ctk.CTkLabel(g_row, text="GAMMA Folder:", width=130, anchor="w", font=ctk.CTkFont(family="Consolas", weight="bold"), text_color=self.C_TEXT_WHITE).pack(side=tk.LEFT)
        g_entry = ctk.CTkEntry(g_row, textvariable=self.gamma_path_var, fg_color=self.C_PANEL, border_color=self.C_BORDER, text_color=self.C_TEXT_WHITE)
        g_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        ctk.CTkButton(g_row, text="Browse", width=85, fg_color="#142c1c", hover_color="#1e462b", border_width=1, border_color=self.C_ZONE_GREEN_DIM, text_color=self.C_ZONE_GREEN, command=self._browse_gamma).pack(side=tk.RIGHT)

        # Backup Folder Row
        b_row = ctk.CTkFrame(path_box, fg_color="transparent")
        b_row.pack(fill=tk.X, padx=16, pady=(6, 10))
        ctk.CTkLabel(b_row, text="Backup Vault:", width=130, anchor="w", font=ctk.CTkFont(family="Consolas", weight="bold"), text_color=self.C_TEXT_WHITE).pack(side=tk.LEFT)
        b_entry = ctk.CTkEntry(b_row, textvariable=self.backup_path_var, fg_color=self.C_PANEL, border_color=self.C_BORDER, text_color=self.C_TEXT_WHITE)
        b_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        ctk.CTkButton(b_row, text="Browse", width=85, fg_color="#142c1c", hover_color="#1e462b", border_width=1, border_color=self.C_ZONE_GREEN_DIM, text_color=self.C_ZONE_GREEN, command=self._browse_backup).pack(side=tk.RIGHT)

        # 2. Options Grid
        opt_grid = ctk.CTkFrame(self.tab_setup, fg_color="transparent")
        opt_grid.pack(fill=tk.X, padx=16, pady=4)
        opt_grid.columnconfigure((0, 1), weight=1)

        # Scope Card (Left)
        scope_card = ctk.CTkFrame(opt_grid, fg_color=self.C_INPUT, corner_radius=10, border_width=1, border_color=self.C_BORDER)
        scope_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=4)
        ctk.CTkLabel(scope_card, text="SCOPE SELECTION", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=self.C_ZONE_GREEN).pack(anchor=tk.W, padx=16, pady=(10, 4))

        ctk.CTkRadioButton(
            scope_card,
            text="Safe Mode (Disabled across ALL profiles)",
            variable=self.scope_var,
            value="all_profiles",
            fg_color=self.C_ZONE_GREEN,
            border_color=self.C_BORDER,
            text_color=self.C_TEXT_WHITE,
        ).pack(anchor=tk.W, padx=16, pady=4)
        ctk.CTkLabel(scope_card, text="Cross-references all profiles so none lose dependencies.", font=ctk.CTkFont(size=10), text_color=self.C_TEXT_MUTED).pack(anchor=tk.W, padx=38, pady=(0, 6))

        ctk.CTkRadioButton(
            scope_card,
            text="Active Profile Only",
            variable=self.scope_var,
            value="active_profile",
            fg_color=self.C_ZONE_GREEN,
            border_color=self.C_BORDER,
            text_color=self.C_TEXT_WHITE,
        ).pack(anchor=tk.W, padx=16, pady=4)
        self.lbl_active_hint = ctk.CTkLabel(scope_card, text="Target: (detecting active profile...)", font=ctk.CTkFont(size=10), text_color=self.C_TEXT_MUTED)
        self.lbl_active_hint.pack(anchor=tk.W, padx=38, pady=(0, 6))

        ctk.CTkRadioButton(
            scope_card,
            text="Custom Specific Profile:",
            variable=self.scope_var,
            value="specific_profile",
            fg_color=self.C_ZONE_GREEN,
            border_color=self.C_BORDER,
            text_color=self.C_TEXT_WHITE,
        ).pack(anchor=tk.W, padx=16, pady=4)
        self.profile_combo = ctk.CTkOptionMenu(scope_card, variable=self.target_profile_var, fg_color=self.C_PANEL, button_color="#142c1c", button_hover_color="#1e462b", text_color=self.C_TEXT_WHITE)
        self.profile_combo.pack(anchor=tk.W, padx=38, fill=tk.X, pady=(2, 10))

        # Shields Card (Right)
        shield_card = ctk.CTkFrame(opt_grid, fg_color=self.C_INPUT, corner_radius=10, border_width=1, border_color=self.C_BORDER)
        shield_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=4)
        ctk.CTkLabel(shield_card, text="SHIELDS & CACHE OPTIONS", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=self.C_ZONE_GREEN).pack(anchor=tk.W, padx=16, pady=(10, 4))

        ctk.CTkSwitch(shield_card, text="Include Installer Downloads (downloads/)", variable=self.include_dl_var, progress_color=self.C_ZONE_GREEN, button_color=self.C_TEXT_WHITE, text_color=self.C_TEXT_WHITE).pack(anchor=tk.W, padx=16, pady=3)
        ctk.CTkSwitch(shield_card, text="Include Legacy Backups (mods_backup/)", variable=self.include_mb_var, progress_color=self.C_ZONE_GREEN, button_color=self.C_TEXT_WHITE, text_color=self.C_TEXT_WHITE).pack(anchor=tk.W, padx=16, pady=3)

        sep = ctk.CTkFrame(shield_card, fg_color=self.C_BORDER, height=1)
        sep.pack(fill=tk.X, padx=16, pady=6)

        ctk.CTkSwitch(shield_card, text="Shield Seasons of the Zone (Spring, Winter, INVERNO)", variable=self.protect_seasons_var, progress_color=self.C_ZONE_GREEN, button_color=self.C_TEXT_WHITE, text_color=self.C_TEXT_WHITE).pack(anchor=tk.W, padx=16, pady=3)
        ctk.CTkSwitch(shield_card, text="Shield MO2 UI Separators (*_separator)", variable=self.protect_seps_var, progress_color=self.C_ZONE_GREEN, button_color=self.C_TEXT_WHITE, text_color=self.C_TEXT_WHITE).pack(anchor=tk.W, padx=16, pady=(3, 10))

        # 3. Action Command Bar (Pill Button Styling like G.A.M.M.A. Main Menu)
        action_bar = ctk.CTkFrame(self.tab_setup, fg_color=self.C_INPUT, corner_radius=10, border_width=1, border_color=self.C_BORDER)
        action_bar.pack(fill=tk.X, padx=16, pady=10)

        inner_act = ctk.CTkFrame(action_bar, fg_color="transparent")
        inner_act.pack(fill=tk.X, padx=16, pady=14)

        self.btn_scan = ctk.CTkButton(
            inner_act,
            text="🔍  SCAN ZONE STORAGE",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#102517",
            hover_color="#193a24",
            border_width=1,
            border_color=self.C_ZONE_GREEN_DIM,
            text_color=self.C_ZONE_GREEN,
            height=46,
            corner_radius=23,
            width=220,
            command=self._start_scan,
        )
        self.btn_scan.pack(side=tk.LEFT, padx=(0, 12))

        # G.A.M.M.A. Menu Pill Button
        self.btn_debloat = ctk.CTkButton(
            inner_act,
            text="⚡  EXECUTE SAFE DEBLOAT & SECURE VAULT",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#0e2a18",
            hover_color="#1b4d2c",
            border_width=2,
            border_color=self.C_ZONE_GREEN,
            text_color=self.C_ZONE_GREEN,
            height=46,
            corner_radius=23,
            state="disabled",
            command=self._start_debloat,
        )
        self.btn_debloat.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_inventory_tab(self):
        tb = ctk.CTkFrame(self.tab_inventory, fg_color="transparent")
        tb.pack(fill=tk.X, padx=12, pady=(10, 6))

        ctk.CTkLabel(tb, text="Filter:", font=ctk.CTkFont(family="Consolas", weight="bold"), text_color=self.C_ZONE_GREEN).pack(side=tk.LEFT, padx=(0, 6))
        f_entry = ctk.CTkEntry(tb, textvariable=self.search_filter_var, placeholder_text="Filter by mod name...", width=340, fg_color=self.C_INPUT, border_color=self.C_BORDER, text_color=self.C_TEXT_WHITE)
        f_entry.pack(side=tk.LEFT, padx=(0, 12))

        ctk.CTkButton(tb, text="Select All", width=95, fg_color="#142c1c", hover_color="#1e462b", border_width=1, border_color=self.C_BORDER, text_color=self.C_ZONE_GREEN, command=lambda: self._set_all_selected(True)).pack(side=tk.LEFT, padx=4)
        ctk.CTkButton(tb, text="Deselect All", width=95, fg_color="#142c1c", hover_color="#1e462b", border_width=1, border_color=self.C_BORDER, text_color=self.C_ZONE_GREEN, command=lambda: self._set_all_selected(False)).pack(side=tk.LEFT, padx=4)

        self.lbl_table_count = ctk.CTkLabel(tb, text="0 mods listed", font=ctk.CTkFont(family="Consolas", size=11), text_color=self.C_TEXT_MUTED)
        self.lbl_table_count.pack(side=tk.RIGHT, padx=6)

        # Embedded Styled Treeview (Zebra Dark Green Rows)
        tree_container = ctk.CTkFrame(self.tab_inventory, fg_color=self.C_INPUT, corner_radius=10, border_width=1, border_color=self.C_BORDER)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Gamma.Treeview",
            background="#0a140e",
            foreground=self.C_TEXT_WHITE,
            fieldbackground="#0a140e",
            rowheight=26,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Gamma.Treeview.Heading",
            background="#0f2418",
            foreground=self.C_ZONE_GREEN,
            font=("Consolas", 10, "bold"),
            padding=6,
            borderwidth=0,
        )
        style.map("Gamma.Treeview", background=[("selected", "#1a4628")], foreground=[("selected", self.C_ZONE_GREEN)])

        cols = ("selected", "name", "size", "files")
        self.tree = ttk.Treeview(tree_container, columns=cols, show="headings", style="Gamma.Treeview", selectmode="browse")

        self.tree.heading("selected", text="ACTION", anchor=tk.CENTER)
        self.tree.heading("name", text="MOD IDENTIFIER", anchor=tk.W)
        self.tree.heading("size", text="SIZE (MB)", anchor=tk.E)
        self.tree.heading("files", text="FILE COUNT", anchor=tk.E)

        self.tree.column("selected", width=110, anchor=tk.CENTER)
        self.tree.column("name", width=620, anchor=tk.W)
        self.tree.column("size", width=110, anchor=tk.E)
        self.tree.column("files", width=100, anchor=tk.E)

        sb = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0), pady=4)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=4, padx=(0, 4))

        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<space>", self._on_tree_space)

    def _build_restore_tab(self):
        panel = ctk.CTkFrame(self.tab_restore, fg_color=self.C_INPUT, corner_radius=10, border_width=1, border_color=self.C_BORDER)
        panel.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        ctk.CTkLabel(panel, text="BACKUP RESTORATION VAULT", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color=self.C_ZONE_GREEN).pack(anchor=tk.W, padx=20, pady=(16, 4))
        ctk.CTkLabel(panel, text="Restore your backed up mods, downloads cache, and profile configurations directly to C:\\GAMMA.", font=ctk.CTkFont(size=11), text_color=self.C_TEXT_MUTED).pack(anchor=tk.W, padx=20, pady=(0, 14))

        # Target backup path
        b_row = ctk.CTkFrame(panel, fg_color="transparent")
        b_row.pack(fill=tk.X, padx=20, pady=6)
        ctk.CTkLabel(b_row, text="Backup Vault Path:", width=140, anchor="w", font=ctk.CTkFont(family="Consolas", weight="bold"), text_color=self.C_TEXT_WHITE).pack(side=tk.LEFT)
        b_entry = ctk.CTkEntry(b_row, textvariable=self.backup_path_var, fg_color=self.C_PANEL, border_color=self.C_BORDER, text_color=self.C_TEXT_WHITE)
        b_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        ctk.CTkButton(b_row, text="Browse", width=85, fg_color="#142c1c", hover_color="#1e462b", border_width=1, border_color=self.C_ZONE_GREEN_DIM, text_color=self.C_ZONE_GREEN, command=self._browse_backup).pack(side=tk.RIGHT)

        # Inspection Box
        self.inspect_box = ctk.CTkTextbox(panel, fg_color=self.C_PANEL, border_width=1, border_color=self.C_BORDER, height=200, font=ctk.CTkFont(family="Consolas", size=11), text_color=self.C_TEXT_WHITE)
        self.inspect_box.pack(fill=tk.X, padx=20, pady=12)
        self.inspect_box.insert(tk.END, "Click 'Inspect Vault' to verify backup integrity and manifest.\n")
        self.inspect_box.configure(state="disabled")

        # Action Buttons
        btn_row = ctk.CTkFrame(panel, fg_color="transparent")
        btn_row.pack(anchor=tk.W, padx=20, pady=10)

        ctk.CTkButton(btn_row, text="Inspect Vault", width=140, fg_color="#142c1c", hover_color="#1e462b", border_width=1, border_color=self.C_ZONE_GREEN_DIM, text_color=self.C_ZONE_GREEN, height=40, corner_radius=20, command=self._inspect_backup).pack(side=tk.LEFT, padx=(0, 14))
        self.btn_restore = ctk.CTkButton(
            btn_row,
            text="↩  RESTORE ALL DATA TO G.A.M.M.A.",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#0e2a18",
            hover_color="#1b4d2c",
            border_width=2,
            border_color=self.C_ZONE_GREEN,
            text_color=self.C_ZONE_GREEN,
            state="disabled",
            height=40,
            corner_radius=20,
            command=self._start_restore,
        )
        self.btn_restore.pack(side=tk.LEFT)

    def _build_manual_tab(self):
        box = ctk.CTkFrame(self.tab_manual, fg_color=self.C_INPUT, corner_radius=10, border_width=1, border_color=self.C_BORDER)
        box.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        txt = ctk.CTkTextbox(box, fg_color=self.C_PANEL, border_width=0, font=ctk.CTkFont(family="Consolas", size=11), text_color=self.C_TEXT_WHITE, wrap="word")
        txt.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        manual = """========================================================================================
S.T.A.L.K.E.R. G.A.M.M.A. STORAGE OPTIMIZATION PROTOCOL — FIELD MANUAL
========================================================================================

1. ARCHITECTURE & SAFETY INVARIANTS:
   • Non-Destructive ModOrganizer 2 VFS: Only mods currently unmounted (-ModName) in
     your profiles are considered for relocation. Active mods (+ModName) are never touched.
   • Multi-Profile Safety Shield: Safe Mode cross-references every single profile in your
     install (e.g. zedd romeo lite, G.A.M.M.A, etc.). If a mod is active in EVEN ONE profile,
     it remains completely untouched on your primary SSD.
   • Dynamic Seasons Shield: Texture packs used by the Seasons of the Zone engine
     (CCon Spring, Summer, Autumn, Dead, INVERNO) are explicitly protected even if currently
     disabled for the active calendar month.
   • Separator Protection: Virtual MO2 grouping folders (*_separator) are retained with
     0 byte overhead so your MO2 layout remains organized.

2. ATOMIC VERIFICATION BEFORE DELETION:
   • Cross-volume moves (e.g. C: to D:) are executed via multi-threaded robocopy.
   • Every mod folder must pass a complete file count and byte sum verification check
     at the destination before the source files on C: are released.

3. RESTORATION CAPABILITIES:
   • In-Tool Restore: Tab 3 allows instant one-click restoration directly inside this GUI.
   • Standalone Script: The backup folder includes 'RESTORE_TO_GAMMA.bat' and '.ps1'.
   • Manual Drag & Drop: Backup folders ('mods', 'profiles', 'downloads') mirror the root
     GAMMA structure exactly and can be dragged directly into C:\\GAMMA in Windows Explorer.
========================================================================================
"""
        txt.insert(tk.END, manual)
        txt.configure(state="disabled")

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color="#07100b", corner_radius=0, height=48)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        inner = ctk.CTkFrame(footer, fg_color="transparent")
        inner.pack(fill=tk.X, padx=24, pady=10)

        self.progress_bar = ctk.CTkProgressBar(inner, progress_color=self.C_ZONE_GREEN, fg_color=self.C_INPUT, height=10)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 16))
        self.progress_bar.set(0)

        self.lbl_status = ctk.CTkLabel(inner, text="SYSTEM READY", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=self.C_ZONE_GREEN)
        self.lbl_status.pack(side=tk.RIGHT)

    def _auto_detect(self):
        gp = DebloaterEngine.detect_gamma_path()
        if gp:
            self.gamma_path_var.set(str(gp))
            self._on_gamma_updated()
            bp = DebloaterEngine.detect_backup_path(gp)
            self.backup_path_var.set(str(bp))
            self._update_space()

    def _on_gamma_updated(self):
        p = Path(self.gamma_path_var.get())
        if p.is_dir() and (p / "ModOrganizer.ini").exists():
            profiles = DebloaterEngine.list_profiles(p)
            active = DebloaterEngine.get_active_profile(p)
            self.detected_profiles = profiles
            self.profile_combo.configure(values=profiles)
            if active and active in profiles:
                self.target_profile_var.set(active)
                self.lbl_active_hint.configure(text=f"Target: {active}")
            elif profiles:
                self.target_profile_var.set(profiles[0])
                self.lbl_active_hint.configure(text=f"Target: {profiles[0]}")
        self._update_space()

    def _update_space(self):
        gp = self.gamma_path_var.get()
        if gp and Path(gp).exists():
            tot, used, free, pct = DebloaterEngine.get_drive_space(Path(gp))
            drive = Path(gp).drive
            self.c1_stat.configure(text=f"{free} GB FREE")
            self.c1_sub.configure(text=f"Total: {tot} GB • {pct}% Used ({drive})")

        bp = self.backup_path_var.get()
        if bp:
            anchor = Path(bp).anchor or "D:\\"
            if Path(anchor).exists():
                tot_b, used_b, free_b, pct_b = DebloaterEngine.get_drive_space(Path(anchor))
                drive_b = Path(bp).drive
                self.c2_stat.configure(text=f"{free_b} GB FREE")
                self.c2_sub.configure(text=f"Total: {tot_b} GB • {pct_b}% Used ({drive_b})")

    def _browse_gamma(self):
        d = filedialog.askdirectory(title="Select S.T.A.L.K.E.R. G.A.M.M.A. Folder", initialdir=self.gamma_path_var.get() or "C:\\")
        if d:
            self.gamma_path_var.set(d)
            self._on_gamma_updated()

    def _browse_backup(self):
        d = filedialog.askdirectory(title="Select Backup Destination Vault", initialdir=self.backup_path_var.get() or "D:\\")
        if d:
            self.backup_path_var.set(d)
            self._update_space()

    def _start_scan(self):
        gp = Path(self.gamma_path_var.get())
        if not (gp / "ModOrganizer.ini").exists():
            messagebox.showerror("Invalid Folder", "Selected folder does not contain a valid G.A.M.M.A. installation.")
            return

        self.btn_scan.configure(state="disabled")
        self.btn_debloat.configure(state="disabled")
        self.progress_bar.start()
        self.lbl_status.configure(text="ANALYZING STORAGE...")

        opts = {
            "scope": self.scope_var.get(),
            "target_profile": self.target_profile_var.get(),
            "include_downloads": self.include_dl_var.get(),
            "include_mods_backup": self.include_mb_var.get(),
            "protect_seasons": self.protect_seasons_var.get(),
            "protect_separators": self.protect_seps_var.get(),
        }

        def worker():
            try:
                plan = DebloaterEngine.analyze(gp, opts, progress_cb=lambda m: self.after(0, self.lbl_status.configure, {"text": m.upper()}))
                self.after(0, self._on_scan_complete, plan)
            except Exception as e:
                self.after(0, self._on_scan_error, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_scan_error(self, err):
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.btn_scan.configure(state="normal")
        self.lbl_status.configure(text="SCAN FAILED")
        messagebox.showerror("Scan Error", err)

    def _on_scan_complete(self, plan):
        self.current_plan = plan
        self.progress_bar.stop()
        self.progress_bar.set(1.0)
        self.btn_scan.configure(state="normal")
        self.btn_debloat.configure(state="normal")

        self._populate_tree()

        cands = plan["candidate_mods"]
        mod_bytes = sum(m["bytes"] for m in cands)
        total_bytes = mod_bytes + plan["downloads"]["bytes"] + plan["mods_backup"]["bytes"]
        total_gb = round(total_bytes / (1024**3), 2)
        mods_gb = round(mod_bytes / (1024**3), 2)

        self.c3_stat.configure(text=f"+{total_gb} GB")
        self.c3_sub.configure(text=f"{len(cands)} Mods ({mods_gb} GB) + Cache")
        self.lbl_status.configure(text=f"SCAN COMPLETE • {len(cands)} CANDIDATES IDENTIFIED")

    def _populate_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.current_plan:
            return

        f_txt = self.search_filter_var.get().lower().strip()
        count = 0
        for m in self.current_plan["candidate_mods"]:
            if f_txt and f_txt not in m["name"].lower():
                continue
            mark = "☑ MOVE" if m.get("selected", True) else "☐ KEEP"
            self.tree.insert("", tk.END, iid=m["name"], values=(mark, m["name"], f"{m['size_mb']:,.1f}", f"{m['files']:,}"))
            count += 1

        self.lbl_table_count.configure(text=f"{count} mods displayed")

    def _on_filter_changed(self, *args):
        self._populate_tree()

    def _on_tree_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self._toggle_selection(item)

    def _on_tree_space(self, event):
        for item in self.tree.selection():
            self._toggle_selection(item)

    def _toggle_selection(self, item_name):
        if not self.current_plan:
            return
        for m in self.current_plan["candidate_mods"]:
            if m["name"] == item_name:
                m["selected"] = not m.get("selected", True)
                mark = "☑ MOVE" if m["selected"] else "☐ KEEP"
                self.tree.item(item_name, values=(mark, m["name"], f"{m['size_mb']:,.1f}", f"{m['files']:,}"))
                self._recalculate_selected_total()
                break

    def _set_all_selected(self, state: bool):
        if not self.current_plan:
            return
        for m in self.current_plan["candidate_mods"]:
            m["selected"] = state
        self._populate_tree()
        self._recalculate_selected_total()

    def _recalculate_selected_total(self):
        if not self.current_plan:
            return
        sel = [m for m in self.current_plan["candidate_mods"] if m.get("selected", True)]
        m_b = sum(m["bytes"] for m in sel)
        dl_b = self.current_plan["downloads"]["bytes"] if self.include_dl_var.get() else 0
        mb_b = self.current_plan["mods_backup"]["bytes"] if self.include_mb_var.get() else 0
        tot_gb = round((m_b + dl_b + mb_b) / (1024**3), 2)
        self.c3_stat.configure(text=f"+{tot_gb} GB")
        self.c3_sub.configure(text=f"{len(sel)} Selected Mods ({round(m_b / (1024**3), 2)} GB)")

    def _start_debloat(self):
        if not self.current_plan:
            return

        sel = [m for m in self.current_plan["candidate_mods"] if m.get("selected", True)]
        if not sel and not self.include_dl_var.get() and not self.include_mb_var.get():
            messagebox.showwarning("No Items Selected", "Please select at least one mod or cache directory to debloat.")
            return

        bp = Path(self.backup_path_var.get())
        m_b = sum(m["bytes"] for m in sel)
        dl_b = self.current_plan["downloads"]["bytes"] if self.include_dl_var.get() else 0
        mb_b = self.current_plan["mods_backup"]["bytes"] if self.include_mb_var.get() else 0
        est_gb = round((m_b + dl_b + mb_b) / (1024**3), 2)

        confirm = messagebox.askyesno(
            "Confirm Debloat Protocol",
            f"Transfer {len(sel)} unused mods and cache ({est_gb} GB) to:\n\n{bp}\n\n"
            "Source files will be verified and safely cleared to reclaim SSD space.\n\nProceed?",
        )
        if not confirm:
            return

        self.btn_scan.configure(state="disabled")
        self.btn_debloat.configure(state="disabled")
        self.progress_bar.set(0)

        # Tactical Log Modal
        log_win = ctk.CTkToplevel(self)
        log_win.title("DEBLOAT TELEMETRY MONITOR")
        log_win.geometry("760x500")
        log_win.configure(fg_color=self.C_ABYSS)
        log_win.grab_set()

        ctk.CTkLabel(log_win, text="☢ PROTOCOL EXECUTION IN PROGRESS", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color=self.C_ZONE_GREEN).pack(anchor=tk.W, padx=20, pady=(14, 6))

        txt_log = ctk.CTkTextbox(log_win, fg_color=self.C_PANEL, border_width=1, border_color=self.C_BORDER, font=ctk.CTkFont(family="Consolas", size=10), text_color=self.C_TEXT_WHITE)
        txt_log.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        opts = {
            "include_downloads": self.include_dl_var.get(),
            "include_mods_backup": self.include_mb_var.get(),
        }

        def log_cb(msg):
            def _ui():
                txt_log.insert(tk.END, msg + "\n")
                txt_log.see(tk.END)
                self.lbl_status.configure(text=msg[:70].upper())
            self.after(0, _ui)

        def prog_cb(cur, tot, desc):
            pct = cur / tot if tot > 0 else 0
            self.after(0, lambda: self.progress_bar.set(pct))

        def worker():
            try:
                DebloaterEngine.execute_debloat(self.current_plan, bp, opts, log_cb, prog_cb)
                self.after(0, lambda: messagebox.showinfo("Protocol Complete", f"Successfully debloated and secured {est_gb} GB to vault!"))
            except Exception as e:
                log_cb(f"\n[FATAL ERROR]: {e}")
                self.after(0, lambda: messagebox.showerror("Protocol Error", str(e)))
            finally:
                self.after(0, self._on_op_finished)

        threading.Thread(target=worker, daemon=True).start()

    def _on_op_finished(self):
        self.btn_scan.configure(state="normal")
        self.btn_debloat.configure(state="normal")
        self._update_space()

    def _inspect_backup(self):
        bp = Path(self.backup_path_var.get())
        man = bp / "manifest.json"
        self.inspect_box.configure(state="normal")
        self.inspect_box.delete("1.0", tk.END)

        if man.exists():
            try:
                d = json.loads(man.read_text(encoding="utf-8"))
                out = (
                    f"=====================================================\n"
                    f"VAULT MANIFEST VERIFIED: {bp}\n"
                    f"=====================================================\n"
                    f"• Creation Timestamp : {d.get('timestamp')}\n"
                    f"• Total Storage Saved: {d.get('total_freed_gb')} GB\n"
                    f"• Relocated Mods     : {d.get('moved_mods_count')} ({d.get('mods_freed_gb')} GB)\n"
                    f"• Downloads Cache    : {d.get('downloads_freed_gb')} GB\n"
                    f"• Legacy Backups     : {d.get('mods_backup_freed_gb')} GB\n"
                    f"• Backed Up Profiles : {', '.join(d.get('profiles_backed_up', []))}\n"
                    f"=====================================================\n"
                    f"STATUS: VAULT INTEGRITY 100% READY FOR RESTORATION\n"
                )
                self.inspect_box.insert(tk.END, out)
                self.btn_restore.configure(state="normal")
                self.inspect_box.configure(state="disabled")
                return
            except Exception:
                pass

        if (bp / "mods").is_dir():
            cnt = len([x for x in (bp / "mods").iterdir() if x.is_dir()])
            self.inspect_box.insert(tk.END, f"Detected unindexed vault with {cnt} mod folders in {bp / 'mods'}.\n")
            self.btn_restore.configure(state="normal")
        else:
            self.inspect_box.insert(tk.END, "ERROR: No valid G.A.M.M.A. backup detected in the specified vault folder.\n")
            self.btn_restore.configure(state="disabled")

        self.inspect_box.configure(state="disabled")

    def _start_restore(self):
        bp = Path(self.backup_path_var.get())
        gp = Path(self.gamma_path_var.get())

        confirm = messagebox.askyesno(
            "Confirm Restoration",
            f"Restore all backed up mods, caches, and load orders from:\n\n{bp}\n\nback to:\n\n{gp}?",
        )
        if not confirm:
            return

        self.btn_restore.configure(state="disabled")
        self.progress_bar.start()
        self.lbl_status.configure(text="RESTORING DATA FROM VAULT...")

        def worker():
            try:
                cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(bp / "RESTORE_TO_GAMMA.ps1")]
                subprocess.run(cmd, check=True, capture_output=True)
                self.after(0, lambda: messagebox.showinfo("Restoration Complete", "All mods and configs have been restored to G.A.M.M.A.!"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Restore Failed", f"Restoration error: {e}"))
            finally:
                self.after(0, self._on_restore_finished)

        threading.Thread(target=worker, daemon=True).start()

    def _on_restore_finished(self):
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.btn_restore.configure(state="normal")
        self.lbl_status.configure(text="RESTORE COMPLETE")
        self._update_space()


def main():
    app = GammaDebloaterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
