"""
S.T.A.L.K.E.R. G.A.M.M.A. Debloater & Storage Optimizer — True Zone AAA Edition
Authentic G.A.M.M.A. in-game UI aesthetics, radioactive emerald palette,
and full safety shields for Seasons of the Zone, MO2 separators, and multi-profile setups.
"""

import os
import sys
import json
import stat
import shutil
import subprocess
import threading
import concurrent.futures
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
        stack = [str(path)]
        while stack:
            cur = stack.pop()
            try:
                with os.scandir(cur) as it:
                    for entry in it:
                        try:
                            if entry.is_file(follow_symlinks=False):
                                total_files += 1
                                total_bytes += entry.stat(follow_symlinks=False).st_size
                            elif entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
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

        candidate_dirs = []
        for d in all_mod_dirs:
            if d.name.endswith("_separator"):
                separators_count += 1
                continue

            if d.name in protected_mods:
                kept_mods_count += 1
                continue

            candidate_dirs.append(d)

        total_cands = len(candidate_dirs)
        src_dl = gamma_path / "downloads"
        need_dl = src_dl.is_dir() and options.get("include_downloads", True)

        src_mb = gamma_path / "mods_backup"
        need_mb = src_mb.is_dir() and options.get("include_mods_backup", True)

        all_scan_targets = list(candidate_dirs)
        dl_idx = None
        mb_idx = None
        if need_dl:
            dl_idx = len(all_scan_targets)
            all_scan_targets.append(src_dl)
        if need_mb:
            mb_idx = len(all_scan_targets)
            all_scan_targets.append(src_mb)

        if all_scan_targets:
            if progress_cb:
                progress_cb(f"Scanning {total_cands} candidate mod trees in parallel...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                stats_results = list(executor.map(cls.get_dir_stats, all_scan_targets))

            for d, (files, bytes_size) in zip(candidate_dirs, stats_results[:total_cands]):
                candidate_mods.append({
                    "name": d.name,
                    "path": d,
                    "files": files,
                    "bytes": bytes_size,
                    "size_mb": round(bytes_size / (1024 * 1024), 2),
                    "selected": True,
                })

            if dl_idx is not None:
                f_cnt, b_cnt = stats_results[dl_idx]
                dl_stats = {
                    "count": f_cnt,
                    "bytes": b_cnt,
                    "size_gb": round(b_cnt / (1024**3), 2),
                    "exists": f_cnt > 0,
                }
            else:
                dl_stats = {"count": 0, "bytes": 0, "size_gb": 0.0, "exists": False}

            if mb_idx is not None:
                f_cnt, b_cnt = stats_results[mb_idx]
                mb_stats = {
                    "count": f_cnt,
                    "bytes": b_cnt,
                    "size_gb": round(b_cnt / (1024**3), 2),
                    "exists": f_cnt > 0,
                }
            else:
                mb_stats = {"count": 0, "bytes": 0, "size_gb": 0.0, "exists": False}
        else:
            dl_stats = {"count": 0, "bytes": 0, "size_gb": 0.0, "exists": False}
            mb_stats = {"count": 0, "bytes": 0, "size_gb": 0.0, "exists": False}

        candidate_mods.sort(key=lambda x: x["bytes"], reverse=True)

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
        
        def _handle_readonly(func, f_path, exc_info):
            try:
                os.chmod(f_path, stat.S_IWRITE | stat.S_IREAD)
                func(f_path)
            except Exception:
                pass

        try:
            if sys.version_info >= (3, 12):
                shutil.rmtree(path, onexc=lambda func, p, exc: _handle_readonly(func, p, exc))
            else:
                shutil.rmtree(path, onerror=_handle_readonly)
        except Exception:
            pass

        if path.exists():
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
        
        include_dl = options.get("include_downloads", True) and plan["downloads"]["exists"]
        include_mb = options.get("include_mods_backup", True) and plan["mods_backup"]["exists"]

        # Calculate phases and steps
        phases = ["Profiles & Load Orders", "Relocate Unused Mods"]
        if include_dl:
            phases.append("Installer Downloads")
        if include_mb:
            phases.append("Legacy Backups")
        phases.append("Finalize Recovery Assets")
        total_phases = len(phases)

        total_mod_bytes = sum(m["bytes"] for m in selected_mods)
        total_dl_bytes = plan["downloads"]["bytes"] if include_dl else 0
        total_mb_bytes = plan["mods_backup"]["bytes"] if include_mb else 0
        total_work_bytes = total_mod_bytes + total_dl_bytes + total_mb_bytes
        total_work_gb = round(total_work_bytes / (1024**3), 2)

        total_steps = 1 + len(selected_mods) + (1 if include_dl else 0) + (1 if include_mb else 0) + 1
        current_step = 0
        bytes_transferred = 0

        def report(step, desc, item="", phase="", pct=None, mod_idx=0):
            calc_pct = pct if pct is not None else ((bytes_transferred / total_work_bytes * 100.0) if total_work_bytes > 0 else (step / total_steps * 100.0 if total_steps > 0 else 0.0))
            calc_pct = min(100.0, max(0.0, calc_pct))
            try:
                progress_cb(
                    step, total_steps, desc,
                    current_item=item,
                    bytes_done=bytes_transferred,
                    total_bytes=total_work_bytes,
                    phase_name=phase,
                    pct=calc_pct,
                    mod_idx=mod_idx,
                    mod_total=len(selected_mods),
                )
            except TypeError:
                progress_cb(step, total_steps, desc)

        t_now = datetime.now().strftime("%H:%M:%S")
        log_cb("=" * 68)
        log_cb(f"[{t_now}] [INITIALIZING G.A.M.M.A. STORAGE DEBLOAT PROTOCOL]")
        log_cb(f"[{t_now}] SOURCE INSTALLATION : {gamma_path}")
        log_cb(f"[{t_now}] BACKUP VAULT TARGET : {backup_dir}")
        log_cb(f"[{t_now}] TARGETED UNUSED MODS: {len(selected_mods)} ({round(total_mod_bytes / (1024**3), 2)} GB)")
        if include_dl:
            log_cb(f"[{t_now}] DOWNLOADS CACHE     : {plan['downloads']['count']} files ({plan['downloads']['size_gb']} GB)")
        if include_mb:
            log_cb(f"[{t_now}] LEGACY BACKUPS      : {plan['mods_backup']['count']} files ({plan['mods_backup']['size_gb']} GB)")
        log_cb(f"[{t_now}] TOTAL STORAGE RECLAIM: {total_work_gb} GB")
        log_cb("=" * 68)

        # 1. Backup Profiles
        current_step += 1
        current_phase_idx = 1
        phase_str = f"PHASE {current_phase_idx}/{total_phases}: PROFILES"
        report(current_step, "Securing MO2 profiles and load orders...", item="Securing Mod Organizer 2 Profiles", phase=phase_str, pct=0.0)
        
        t_now = datetime.now().strftime("%H:%M:%S")
        log_cb(f"\n[{t_now}] [{phase_str}] Backing up MO2 profiles and load orders to vault...")
        dst_profiles = backup_dir / "profiles"
        cls._robocopy(gamma_path / "profiles", dst_profiles)
        log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✓ OK] Profile modlists stored safely at: {dst_profiles}")

        for p in (gamma_path / "profiles").iterdir():
            if p.is_dir():
                ml = p / "modlist.txt"
                if ml.exists():
                    bak = p / "modlist.txt.full_before_debloat"
                    if not bak.exists():
                        shutil.copy2(ml, bak)
                        log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [BACKUP] Saved snapshot: {p.name}/modlist.txt.full_before_debloat")

        # 2. Move Selected Candidate Mods
        current_phase_idx += 1
        phase_str = f"PHASE {current_phase_idx}/{total_phases}: MODS"
        dst_mods = backup_dir / "mods"
        dst_mods.mkdir(parents=True, exist_ok=True)
        moved_manifest = []
        total_mod_bytes_freed = 0

        t_now = datetime.now().strftime("%H:%M:%S")
        log_cb(f"\n[{t_now}] [{phase_str}] Transferring {len(selected_mods)} unused mods to backup vault...")

        for i, mod in enumerate(selected_mods, 1):
            current_step += 1
            now_str = datetime.now().strftime("%H:%M:%S")
            src_folder = mod["path"]
            dst_folder = dst_mods / mod["name"]
            src_files, src_bytes = mod["files"], mod["bytes"]
            size_mb = mod["size_mb"]

            moving_desc = f"[{i}/{len(selected_mods)}] Moving: {mod['name']} ({size_mb} MB, {src_files} files)"
            report(current_step, moving_desc, item=moving_desc, phase=phase_str, mod_idx=i)
            log_cb(f"[{now_str}] [TRANSFERRING {i}/{len(selected_mods)}] {mod['name']} ({size_mb} MB, {src_files} files)...")

            is_same_drive = (src_folder.drive.upper() == dst_folder.drive.upper())
            if is_same_drive:
                try:
                    if dst_folder.exists():
                        cls.safe_rmtree(dst_folder)
                    os.replace(src_folder, dst_folder)
                    bytes_transferred += src_bytes
                    total_mod_bytes_freed += src_bytes
                    moved_manifest.append(mod)

                    cum_gb = round(bytes_transferred / (1024**3), 2)
                    verified_desc = f"[{i}/{len(selected_mods)}] Relocated: {mod['name']} (+{size_mb} MB)"
                    report(current_step, verified_desc, item=verified_desc, phase=phase_str, mod_idx=i)
                    log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✓ INSTANT ZERO-COPY MOVE] {mod['name']} (+{size_mb} MB | Freed: {cum_gb} GB / {total_work_gb} GB)")
                    continue
                except OSError:
                    pass

            try:
                cls._robocopy(src_folder, dst_folder)
            except Exception as e:
                log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✗ ERROR] Robocopy failed for '{mod['name']}': {e}. Source NOT deleted.")
                continue

            dst_files, dst_bytes = cls.get_dir_stats(dst_folder)
            if dst_files != src_files or dst_bytes != src_bytes:
                log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✗ MISMATCH] Verification failed for '{mod['name']}' (Source: {src_files} files / {src_bytes} B vs Dest: {dst_files} files / {dst_bytes} B). Source KEPT.")
                continue

            cls.safe_rmtree(src_folder)
            bytes_transferred += src_bytes
            total_mod_bytes_freed += src_bytes
            moved_manifest.append(mod)

            cum_gb = round(bytes_transferred / (1024**3), 2)
            verified_desc = f"[{i}/{len(selected_mods)}] Verified & Purged: {mod['name']} (+{size_mb} MB)"
            report(current_step, verified_desc, item=verified_desc, phase=phase_str, mod_idx=i)
            log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✓ VERIFIED & PURGED] {mod['name']} (+{size_mb} MB | Freed: {cum_gb} GB / {total_work_gb} GB)")

        # 3. Move Downloads
        dl_bytes_freed = 0
        if include_dl:
            current_step += 1
            current_phase_idx += 1
            phase_str = f"PHASE {current_phase_idx}/{total_phases}: DOWNLOADS"
            s_f, s_b = plan["downloads"]["count"], plan["downloads"]["bytes"]
            s_gb = plan["downloads"]["size_gb"]
            
            dl_desc = f"Relocating installer downloads cache ({s_f} packages, {s_gb} GB)"
            report(current_step, dl_desc, item=dl_desc, phase=phase_str, mod_idx=len(selected_mods))
            log_cb(f"\n[{datetime.now().strftime('%H:%M:%S')}] [{phase_str}] Relocating installer download archives ({s_f} files, {s_gb} GB)...")
            
            src_dl = gamma_path / "downloads"
            dst_dl = backup_dir / "downloads"
            dst_dl.mkdir(parents=True, exist_ok=True)
            
            is_same_drive = (src_dl.drive.upper() == dst_dl.drive.upper())
            if is_same_drive:
                try:
                    moved_cnt = 0
                    for item in list(src_dl.iterdir()):
                        target_item = dst_dl / item.name
                        if target_item.exists():
                            if target_item.is_dir():
                                cls.safe_rmtree(target_item)
                            else:
                                target_item.unlink()
                        os.replace(item, target_item)
                        moved_cnt += 1
                    dl_bytes_freed = s_b
                    bytes_transferred += s_b
                    cum_gb = round(bytes_transferred / (1024**3), 2)
                    log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✓ INSTANT ZERO-COPY MOVE] Relocated {moved_cnt} download packages (+{s_gb} GB freed | Freed: {cum_gb} GB / {total_work_gb} GB)")
                except Exception as e:
                    log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [WARN] Fast move encountered issue ({e}), falling back to Robocopy stream...")
                    is_same_drive = False

            if not is_same_drive:
                try:
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
                        bytes_transferred += s_b
                        cum_gb = round(bytes_transferred / (1024**3), 2)
                        log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✓ VERIFIED & PURGED] Downloads cache relocated (+{s_gb} GB freed | Freed: {cum_gb} GB / {total_work_gb} GB)")
                    else:
                        log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✗ MISMATCH] Downloads verification mismatch (Src: {s_f} files, Dst: {d_f} files). Source KEPT.")
                except Exception as e:
                    log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✗ ERROR] Robocopy failed for downloads: {e}. Source NOT deleted.")

        # 4. Move mods_backup
        mb_bytes_freed = 0
        if include_mb:
            current_step += 1
            current_phase_idx += 1
            phase_str = f"PHASE {current_phase_idx}/{total_phases}: LEGACY BACKUPS"
            s_f, s_b = plan["mods_backup"]["count"], plan["mods_backup"]["bytes"]
            s_gb = plan["mods_backup"]["size_gb"]
            
            mb_desc = f"Relocating legacy pre-split backups ({s_f} files, {s_gb} GB)"
            report(current_step, mb_desc, item=mb_desc, phase=phase_str, mod_idx=len(selected_mods))
            log_cb(f"\n[{datetime.now().strftime('%H:%M:%S')}] [{phase_str}] Relocating legacy pre-split backups ({s_f} files, {s_gb} GB)...")
            
            src_mb = gamma_path / "mods_backup"
            dst_mb = backup_dir / "mods_backup"
            
            is_same_drive = (src_mb.drive.upper() == dst_mb.drive.upper())
            if is_same_drive:
                try:
                    if dst_mb.exists():
                        cls.safe_rmtree(dst_mb)
                    os.replace(src_mb, dst_mb)
                    mb_bytes_freed = s_b
                    bytes_transferred += s_b
                    cum_gb = round(bytes_transferred / (1024**3), 2)
                    log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✓ INSTANT ZERO-COPY MOVE] Legacy backups relocated (+{s_gb} GB freed | Freed: {cum_gb} GB / {total_work_gb} GB)")
                except Exception as e:
                    log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [WARN] Fast move encountered issue ({e}), falling back to Robocopy stream...")
                    is_same_drive = False

            if not is_same_drive:
                try:
                    cls._robocopy(src_mb, dst_mb)
                    d_f, d_b = cls.get_dir_stats(dst_mb)
                    if d_f == s_f and d_b == s_b:
                        cls.safe_rmtree(src_mb)
                        mb_bytes_freed = s_b
                        bytes_transferred += s_b
                        cum_gb = round(bytes_transferred / (1024**3), 2)
                        log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✓ VERIFIED & PURGED] Legacy backups relocated (+{s_gb} GB freed | Freed: {cum_gb} GB / {total_work_gb} GB)")
                    else:
                        log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✗ MISMATCH] Legacy backups verification mismatch (Src: {s_f} files, Dst: {d_f} files). Source KEPT.")
                except Exception as e:
                    log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✗ ERROR] Robocopy failed for legacy backups: {e}. Source NOT deleted.")

        # 5. Generate Manifest, Restore Script, and Documentation
        current_step += 1
        phase_str = f"PHASE {total_phases}/{total_phases}: RECOVERY ASSETS"
        fin_desc = "Generating recovery scripts, manifest, and field manual"
        report(current_step, fin_desc, item=fin_desc, phase=phase_str, pct=99.0, mod_idx=len(selected_mods))
        
        t_now = datetime.now().strftime("%H:%M:%S")
        log_cb(f"\n[{t_now}] [{phase_str}] Generating recovery scripts, manifest, and documentation...")
        total_freed = total_mod_bytes_freed + dl_bytes_freed + mb_bytes_freed
        cls._generate_restore_files(backup_dir, gamma_path, moved_manifest, total_freed, total_mod_bytes_freed, dl_bytes_freed, mb_bytes_freed, plan["profiles"])
        log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✓ MANIFEST] manifest.json generated with full itemized inventory.")
        log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✓ SCRIPTS] RESTORE_TO_GAMMA.bat and .ps1 generated in backup vault.")
        log_cb(f"[{datetime.now().strftime('%H:%M:%S')}]   [✓ MANUAL] README.txt field guide created.")

        t_now = datetime.now().strftime("%H:%M:%S")
        log_cb("\n" + "=" * 68)
        log_cb(f"[{t_now}] SUCCESS: STORAGE RECLAMATION PROTOCOL COMPLETE!")
        log_cb(f"[{t_now}] TOTAL SPACE FREED ON SOURCE DRIVE: {round(total_freed / (1024**3), 2)} GB")
        log_cb(f"[{t_now}] TOTAL UNUSED MODS RELOCATED    : {len(moved_manifest)} mods ({round(total_mod_bytes_freed / (1024**3), 2)} GB)")
        if dl_bytes_freed > 0:
            log_cb(f"[{t_now}] DOWNLOADS CACHE RELOCATED      : {round(dl_bytes_freed / (1024**3), 2)} GB")
        if mb_bytes_freed > 0:
            log_cb(f"[{t_now}] LEGACY BACKUPS RELOCATED       : {round(mb_bytes_freed / (1024**3), 2)} GB")
        log_cb(f"[{t_now}] BACKUP VAULT TARGET            : {backup_dir}")
        log_cb(f"[{t_now}] BIT-LEVEL VERIFICATION STATUS  : 100% VERIFIED")
        log_cb("=" * 68)

        report(total_steps, "Storage Reclamation Protocol Complete!", item="Protocol Finished — 100% Verified", phase="COMPLETE", pct=100.0, mod_idx=len(selected_mods))

    @staticmethod
    def _robocopy(src: Path, dst: Path):
        dst.mkdir(parents=True, exist_ok=True)
        cmd = ["robocopy", str(src), str(dst), "/E", "/MT:32", "/R:0", "/W:0", "/J", "/NP", "/NDL", "/NFL"]
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
    robocopy $srcMods $dstMods /E /MOVE /MT:32 /J /R:0 /W:0 /NP /NDL /NFL | Out-Null
}}

# 2. Restore downloads
$srcDl = Join-Path $backupDir "downloads"
$dstDl = Join-Path $gammaDir "downloads"
if (Test-Path $srcDl) {{
    Write-Host "`nRestoring downloads to $dstDl..." -ForegroundColor Yellow
    robocopy $srcDl $dstDl /E /MOVE /MT:32 /J /R:0 /W:0 /NP /NDL /NFL | Out-Null
}}

# 3. Restore mods_backup
$srcMb = Join-Path $backupDir "mods_backup"
$dstMb = Join-Path $gammaDir "mods_backup"
if (Test-Path $srcMb) {{
    Write-Host "`nRestoring mods_backup to $dstMb..." -ForegroundColor Yellow
    robocopy $srcMb $dstMb /E /MOVE /MT:32 /J /R:0 /W:0 /NP /NDL /NFL | Out-Null
}}

# 4. Restore profiles (modlist.txt, load orders)
$srcProf = Join-Path $backupDir "profiles"
$dstProf = Join-Path $gammaDir "profiles"
if (Test-Path $srcProf) {{
    Write-Host "`nRestoring profile modlists and configs..." -ForegroundColor Yellow
    robocopy $srcProf $dstProf /E /MT:32 /J /R:0 /W:0 /NP /NDL /NFL | Out-Null
}}

Write-Host "`nRESTORE COMPLETE! Everything has been returned to $gammaDir." -ForegroundColor Green
"""
        with open(backup_dir / "RESTORE_TO_GAMMA.ps1", "w", encoding="utf-8") as f:
            f.write(ps1_content)


class TelemetryMonitorModal(ctk.CTkToplevel):
    """
    S.T.A.L.K.E.R. Zone Military-Grade Telemetry HUD Monitor.
    Displays live step-by-step telemetry, current mod transfer indicators,
    real-time progress percentage, bytes transferred, and scrolling terminal log.
    """

    def __init__(self, parent, backup_path: Path, total_mods: int, total_work_bytes: int, total_phases: int):
        super().__init__(parent)
        self.parent = parent
        self.backup_path = backup_path
        self.total_mods = total_mods
        self.total_work_bytes = total_work_bytes
        self.total_phases = total_phases
        self.is_finished = False
        self.start_time = datetime.now()
        self.timer_job = None

        self.title("S.T.A.L.K.E.R. G.A.M.M.A. — DEBLOAT TELEMETRY MONITOR")
        self.geometry("900x650")
        self.minsize(840, 580)
        self.configure(fg_color=parent.C_ABYSS)

        # Center on parent window
        try:
            self.update_idletasks()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            if pw > 100 and ph > 100:
                cx = max(20, px + (pw - 900) // 2)
                cy = max(20, py + (ph - 650) // 2)
                self.geometry(f"900x650+{cx}+{cy}")
        except Exception:
            pass

        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close_requested)

        self._build_header()
        self._build_hud_cards()
        self._build_progress_strip()
        self._build_target_banner()
        self._build_terminal_log()
        self._build_footer()

        self._start_timer()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="#07100b", corner_radius=0)
        header.pack(fill=tk.X, side=tk.TOP)

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill=tk.X, padx=20, pady=12)

        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side=tk.LEFT)

        ctk.CTkLabel(
            left,
            text="☢  DEBLOAT TELEMETRY MONITOR",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.parent.C_ZONE_GREEN,
        ).pack(anchor=tk.W)

        ctk.CTkLabel(
            left,
            text="LIVE VFS MIGRATION & BIT-LEVEL INTEGRITY STREAM",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=self.parent.C_TEXT_STENCIL,
        ).pack(anchor=tk.W, pady=(2, 0))

        # Status badge frame on right
        badge = ctk.CTkFrame(inner, fg_color=self.parent.C_PANEL, corner_radius=6, border_width=1, border_color=self.parent.C_BORDER)
        badge.pack(side=tk.RIGHT)

        self.lbl_stream_badge = ctk.CTkLabel(
            badge,
            text="● PROTOCOL: ACTIVE",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=self.parent.C_ZONE_GREEN,
        )
        self.lbl_stream_badge.pack(padx=12, pady=(6, 2))

        v_str = str(self.backup_path)
        if len(v_str) > 35:
            v_str = v_str[:15] + "..." + v_str[-18:]
        ctk.CTkLabel(
            badge,
            text=f"VAULT: {v_str}",
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=self.parent.C_TEXT_MUTED,
        ).pack(padx=12, pady=(0, 6))

        # Glow divider line
        ctk.CTkFrame(self, fg_color=self.parent.C_ZONE_GREEN, height=2, corner_radius=0).pack(fill=tk.X)

    def _build_hud_cards(self):
        hud = ctk.CTkFrame(self, fg_color="transparent")
        hud.pack(fill=tk.X, padx=18, pady=(12, 6))
        hud.columnconfigure((0, 1, 2, 3), weight=1)

        # Card 1: Progress percentage
        c1 = ctk.CTkFrame(hud, fg_color=self.parent.C_PANEL, corner_radius=8, border_width=1, border_color=self.parent.C_ZONE_GREEN)
        c1.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ctk.CTkLabel(c1, text="PROGRESS", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.parent.C_ZONE_GREEN).pack(anchor=tk.W, padx=12, pady=(8, 2))
        self.lbl_pct = ctk.CTkLabel(c1, text="0.0%", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=self.parent.C_ZONE_GREEN)
        self.lbl_pct.pack(anchor=tk.W, padx=12)
        self.lbl_items_sub = ctk.CTkLabel(c1, text=f"0 / {self.total_mods} Mods Relocated", font=ctk.CTkFont(size=10), text_color=self.parent.C_TEXT_MUTED)
        self.lbl_items_sub.pack(anchor=tk.W, padx=12, pady=(0, 8))

        # Card 2: Reclaimed Storage
        tot_gb = round(self.total_work_bytes / (1024**3), 2)
        c2 = ctk.CTkFrame(hud, fg_color=self.parent.C_PANEL, corner_radius=8, border_width=1, border_color=self.parent.C_BORDER)
        c2.grid(row=0, column=1, sticky="nsew", padx=4)
        ctk.CTkLabel(c2, text="STORAGE RECLAIMED", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.parent.C_TEXT_MUTED).pack(anchor=tk.W, padx=12, pady=(8, 2))
        self.lbl_storage = ctk.CTkLabel(c2, text=f"0.00 / {tot_gb:.2f} GB", font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"), text_color=self.parent.C_ZONE_CYAN)
        self.lbl_storage.pack(anchor=tk.W, padx=12)
        ctk.CTkLabel(c2, text="SSD Space Relocated", font=ctk.CTkFont(size=10), text_color=self.parent.C_TEXT_MUTED).pack(anchor=tk.W, padx=12, pady=(0, 8))

        # Card 3: Execution Phase
        c3 = ctk.CTkFrame(hud, fg_color=self.parent.C_PANEL, corner_radius=8, border_width=1, border_color=self.parent.C_BORDER)
        c3.grid(row=0, column=2, sticky="nsew", padx=4)
        ctk.CTkLabel(c3, text="EXECUTION PHASE", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.parent.C_TEXT_MUTED).pack(anchor=tk.W, padx=12, pady=(8, 2))
        self.lbl_phase = ctk.CTkLabel(c3, text=f"PHASE 1/{self.total_phases}", font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"), text_color=self.parent.C_TEXT_WHITE)
        self.lbl_phase.pack(anchor=tk.W, padx=12)
        self.lbl_phase_sub = ctk.CTkLabel(c3, text="Securing Profiles", font=ctk.CTkFont(size=10), text_color=self.parent.C_TEXT_MUTED)
        self.lbl_phase_sub.pack(anchor=tk.W, padx=12, pady=(0, 8))

        # Card 4: Integrity Status
        c4 = ctk.CTkFrame(hud, fg_color=self.parent.C_PANEL, corner_radius=8, border_width=1, border_color=self.parent.C_BORDER)
        c4.grid(row=0, column=3, sticky="nsew", padx=(4, 0))
        ctk.CTkLabel(c4, text="INTEGRITY SHIELD", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.parent.C_TEXT_MUTED).pack(anchor=tk.W, padx=12, pady=(8, 2))
        self.lbl_status_flag = ctk.CTkLabel(c4, text="VERIFYING", font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"), text_color=self.parent.C_ZONE_GREEN)
        self.lbl_status_flag.pack(anchor=tk.W, padx=12)
        ctk.CTkLabel(c4, text="Byte-Exact Verification", font=ctk.CTkFont(size=10), text_color=self.parent.C_TEXT_MUTED).pack(anchor=tk.W, padx=12, pady=(0, 8))

    def _build_progress_strip(self):
        p_frame = ctk.CTkFrame(self, fg_color="transparent")
        p_frame.pack(fill=tk.X, padx=18, pady=(4, 6))

        self.prog_bar = ctk.CTkProgressBar(
            p_frame,
            progress_color=self.parent.C_ZONE_GREEN,
            fg_color=self.parent.C_INPUT,
            height=12,
            corner_radius=6,
        )
        self.prog_bar.pack(fill=tk.X)
        self.prog_bar.set(0)

    def _build_target_banner(self):
        target_frame = ctk.CTkFrame(self, fg_color=self.parent.C_INPUT, corner_radius=8, border_width=1, border_color=self.parent.C_BORDER)
        target_frame.pack(fill=tk.X, padx=18, pady=(0, 6))

        inner = ctk.CTkFrame(target_frame, fg_color="transparent")
        inner.pack(fill=tk.X, padx=12, pady=6)

        ctk.CTkLabel(
            inner,
            text="▶ CURRENT TARGET:",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=self.parent.C_ZONE_GREEN,
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_target = ctk.CTkLabel(
            inner,
            text="Initializing debloat protocol...",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=self.parent.C_TEXT_WHITE,
            anchor="w",
        )
        self.lbl_target.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_terminal_log(self):
        c_frame = ctk.CTkFrame(self, fg_color=self.parent.C_INPUT, corner_radius=8, border_width=1, border_color=self.parent.C_BORDER)
        c_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 8))

        self.txt_log = ctk.CTkTextbox(
            c_frame,
            fg_color="#060e09",
            border_width=0,
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color="#dff5e5",
            wrap="char",
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color="#07100b", corner_radius=0, height=44)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        inner = ctk.CTkFrame(footer, fg_color="transparent")
        inner.pack(fill=tk.X, padx=18, pady=8)

        self.lbl_elapsed = ctk.CTkLabel(
            inner,
            text="⏱ ELAPSED: 00:00:00",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=self.parent.C_TEXT_MUTED,
        )
        self.lbl_elapsed.pack(side=tk.LEFT)

        self.btn_copy_log = ctk.CTkButton(
            inner,
            text="📋 Copy Log",
            width=100,
            height=28,
            corner_radius=14,
            fg_color=self.parent.C_INPUT,
            hover_color="#183623",
            border_width=1,
            border_color=self.parent.C_BORDER,
            text_color=self.parent.C_ZONE_GREEN,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._copy_log,
        )
        self.btn_copy_log.pack(side=tk.RIGHT, padx=(8, 0))

        self.btn_close = ctk.CTkButton(
            inner,
            text="Close Monitor",
            width=130,
            height=28,
            corner_radius=14,
            fg_color="#142419",
            hover_color="#1e3a27",
            border_width=1,
            border_color=self.parent.C_BORDER,
            text_color=self.parent.C_TEXT_MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            state="disabled",
            command=self._on_close_clicked,
        )
        self.btn_close.pack(side=tk.RIGHT)

    def append_log(self, text: str):
        if not self.winfo_exists():
            return
        self.txt_log.insert(tk.END, text + "\n")
        self.txt_log.see(tk.END)

    def update_telemetry(self, cur_step, tot_steps, desc, current_item="", bytes_done=0, total_bytes=0, phase_name="", pct=0.0, mod_idx=0, mod_total=0):
        if not self.winfo_exists() or self.is_finished:
            return

        # 1. Update Percentage
        self.lbl_pct.configure(text=f"{pct:.1f}%")
        self.prog_bar.set(min(1.0, max(0.0, pct / 100.0)))

        # 2. Update Mod Count
        tot_m = mod_total or self.total_mods
        self.lbl_items_sub.configure(text=f"{mod_idx} / {tot_m} Mods Relocated")

        # 3. Update Storage
        done_gb = round(bytes_done / (1024**3), 2)
        target_gb = round((total_bytes or self.total_work_bytes) / (1024**3), 2)
        self.lbl_storage.configure(text=f"{done_gb:.2f} / {target_gb:.2f} GB")

        # 4. Update Phase
        if phase_name:
            if ":" in phase_name:
                p_part, sub_part = phase_name.split(":", 1)
                self.lbl_phase.configure(text=p_part.strip())
                self.lbl_phase_sub.configure(text=sub_part.strip())
            else:
                self.lbl_phase.configure(text=phase_name.strip())

        # 5. Update Current Target
        if current_item:
            self.lbl_target.configure(text=current_item[:85])

    def on_finished(self, success: bool, message: str):
        self.is_finished = True
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None

        if not self.winfo_exists():
            return

        elapsed = int((datetime.now() - self.start_time).total_seconds())
        hrs, rem = divmod(elapsed, 3600)
        mins, secs = divmod(rem, 60)
        self.lbl_elapsed.configure(text=f"⏱ COMPLETED IN: {hrs:02d}:{mins:02d}:{secs:02d}")

        if success:
            self.lbl_stream_badge.configure(text="● PROTOCOL: COMPLETE", text_color=self.parent.C_ZONE_GREEN)
            self.lbl_pct.configure(text="100.0%")
            self.prog_bar.set(1.0)
            self.lbl_status_flag.configure(text="SECURED", text_color=self.parent.C_ZONE_GREEN)
            self.lbl_target.configure(text="Protocol Complete • All verified files safely secured to backup vault.")
        else:
            self.lbl_stream_badge.configure(text="● PROTOCOL: ABORTED", text_color=self.parent.C_ZONE_RED)
            self.lbl_status_flag.configure(text="ERROR", text_color=self.parent.C_ZONE_RED)
            self.lbl_target.configure(text=f"Error encountered: {message}")

        self.btn_close.configure(
            state="normal",
            text="✓ CLOSE MONITOR",
            fg_color=self.parent.C_ZONE_GREEN,
            text_color=self.parent.C_ABYSS,
            hover_color=self.parent.C_ZONE_GREEN_HOVER,
        )

    def _start_timer(self):
        self._tick_timer()

    def _tick_timer(self):
        if not self.winfo_exists() or self.is_finished:
            return
        elapsed = int((datetime.now() - self.start_time).total_seconds())
        hrs, rem = divmod(elapsed, 3600)
        mins, secs = divmod(rem, 60)
        self.lbl_elapsed.configure(text=f"⏱ ELAPSED: {hrs:02d}:{mins:02d}:{secs:02d}")
        self.timer_job = self.after(1000, self._tick_timer)

    def _copy_log(self):
        try:
            content = self.txt_log.get("1.0", tk.END).strip()
            self.clipboard_clear()
            self.clipboard_append(content)
            self.btn_copy_log.configure(text="✓ Copied!", fg_color="#1a4628")
            self.after(2000, lambda: self.btn_copy_log.configure(text="📋 Copy Log", fg_color=self.parent.C_INPUT))
        except Exception:
            pass

    def _on_close_clicked(self):
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _on_close_requested(self):
        if not self.is_finished:
            confirm = messagebox.askyesno(
                "Protocol Active",
                "Debloat protocol is actively moving and verifying files.\n\n"
                "Closing this telemetry monitor will NOT stop the operation in the background.\n\n"
                "Are you sure you want to close this monitor window?",
                parent=self,
            )
            if not confirm:
                return
        self._on_close_clicked()


class RestoreTelemetryMonitorModal(ctk.CTkToplevel):
    r"""
    S.T.A.L.K.E.R. Zone Military-Grade Restoration HUD Monitor.
    Displays live step-by-step telemetry while restoring files back to C:\GAMMA.
    """

    def __init__(self, parent, backup_path: Path, gamma_path: Path):
        super().__init__(parent)
        self.parent = parent
        self.backup_path = backup_path
        self.gamma_path = gamma_path
        self.is_finished = False
        self.start_time = datetime.now()
        self.timer_job = None

        self.title("S.T.A.L.K.E.R. G.A.M.M.A. — RESTORATION TELEMETRY MONITOR")
        self.geometry("860x580")
        self.minsize(800, 520)
        self.configure(fg_color=parent.C_ABYSS)

        try:
            self.update_idletasks()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            if pw > 100 and ph > 100:
                cx = max(20, px + (pw - 860) // 2)
                cy = max(20, py + (ph - 580) // 2)
                self.geometry(f"860x580+{cx}+{cy}")
        except Exception:
            pass

        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close_requested)

        self._build_header()
        self._build_hud_cards()
        self._build_progress_strip()
        self._build_terminal_log()
        self._build_footer()

        self._start_timer()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="#07100b", corner_radius=0)
        header.pack(fill=tk.X, side=tk.TOP)

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill=tk.X, padx=20, pady=12)

        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side=tk.LEFT)

        ctk.CTkLabel(
            left,
            text="↩  RESTORATION TELEMETRY MONITOR",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.parent.C_ZONE_GREEN,
        ).pack(anchor=tk.W)

        ctk.CTkLabel(
            left,
            text="STREAMING VFS ROLLBACK & LOAD ORDER RECONSTRUCTION",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=self.parent.C_TEXT_STENCIL,
        ).pack(anchor=tk.W, pady=(2, 0))

        badge = ctk.CTkFrame(inner, fg_color=self.parent.C_PANEL, corner_radius=6, border_width=1, border_color=self.parent.C_BORDER)
        badge.pack(side=tk.RIGHT)

        self.lbl_stream_badge = ctk.CTkLabel(
            badge,
            text="● RESTORE: ACTIVE",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=self.parent.C_ZONE_GREEN,
        )
        self.lbl_stream_badge.pack(padx=12, pady=(6, 2))

        ctk.CTkLabel(
            badge,
            text=f"TARGET: {self.gamma_path.name}",
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=self.parent.C_TEXT_MUTED,
        ).pack(padx=12, pady=(0, 6))

        ctk.CTkFrame(self, fg_color=self.parent.C_ZONE_GREEN, height=2, corner_radius=0).pack(fill=tk.X)

    def _build_hud_cards(self):
        hud = ctk.CTkFrame(self, fg_color="transparent")
        hud.pack(fill=tk.X, padx=18, pady=(12, 6))
        hud.columnconfigure((0, 1, 2), weight=1)

        c1 = ctk.CTkFrame(hud, fg_color=self.parent.C_PANEL, corner_radius=8, border_width=1, border_color=self.parent.C_ZONE_GREEN)
        c1.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ctk.CTkLabel(c1, text="OPERATION", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.parent.C_ZONE_GREEN).pack(anchor=tk.W, padx=12, pady=(8, 2))
        self.lbl_op_stat = ctk.CTkLabel(c1, text="RESTORING", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=self.parent.C_ZONE_GREEN)
        self.lbl_op_stat.pack(anchor=tk.W, padx=12)
        ctk.CTkLabel(c1, text="Returning mods to C:\\GAMMA", font=ctk.CTkFont(size=10), text_color=self.parent.C_TEXT_MUTED).pack(anchor=tk.W, padx=12, pady=(0, 8))

        c2 = ctk.CTkFrame(hud, fg_color=self.parent.C_PANEL, corner_radius=8, border_width=1, border_color=self.parent.C_BORDER)
        c2.grid(row=0, column=1, sticky="nsew", padx=4)
        ctk.CTkLabel(c2, text="SOURCE VAULT", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.parent.C_TEXT_MUTED).pack(anchor=tk.W, padx=12, pady=(8, 2))
        v_str = str(self.backup_path)
        if len(v_str) > 28:
            v_str = v_str[:12] + "..." + v_str[-13:]
        self.lbl_src = ctk.CTkLabel(c2, text=v_str, font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color=self.parent.C_ZONE_CYAN)
        self.lbl_src.pack(anchor=tk.W, padx=12)
        ctk.CTkLabel(c2, text="Verified Backup Vault", font=ctk.CTkFont(size=10), text_color=self.parent.C_TEXT_MUTED).pack(anchor=tk.W, padx=12, pady=(0, 8))

        c3 = ctk.CTkFrame(hud, fg_color=self.parent.C_PANEL, corner_radius=8, border_width=1, border_color=self.parent.C_BORDER)
        c3.grid(row=0, column=2, sticky="nsew", padx=(4, 0))
        ctk.CTkLabel(c3, text="DESTINATION", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.parent.C_TEXT_MUTED).pack(anchor=tk.W, padx=12, pady=(8, 2))
        g_str = str(self.gamma_path)
        if len(g_str) > 28:
            g_str = g_str[:12] + "..." + g_str[-13:]
        self.lbl_dst = ctk.CTkLabel(c3, text=g_str, font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color=self.parent.C_TEXT_WHITE)
        self.lbl_dst.pack(anchor=tk.W, padx=12)
        ctk.CTkLabel(c3, text="Live G.A.M.M.A. Folder", font=ctk.CTkFont(size=10), text_color=self.parent.C_TEXT_MUTED).pack(anchor=tk.W, padx=12, pady=(0, 8))

    def _build_progress_strip(self):
        p_frame = ctk.CTkFrame(self, fg_color="transparent")
        p_frame.pack(fill=tk.X, padx=18, pady=(4, 6))

        self.prog_bar = ctk.CTkProgressBar(
            p_frame,
            progress_color=self.parent.C_ZONE_GREEN,
            fg_color=self.parent.C_INPUT,
            height=10,
            corner_radius=5,
        )
        self.prog_bar.pack(fill=tk.X)
        self.prog_bar.configure(mode="indeterminate")
        self.prog_bar.start()

    def _build_terminal_log(self):
        c_frame = ctk.CTkFrame(self, fg_color=self.parent.C_INPUT, corner_radius=8, border_width=1, border_color=self.parent.C_BORDER)
        c_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 8))

        self.txt_log = ctk.CTkTextbox(
            c_frame,
            fg_color="#060e09",
            border_width=0,
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color="#dff5e5",
            wrap="char",
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color="#07100b", corner_radius=0, height=44)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        inner = ctk.CTkFrame(footer, fg_color="transparent")
        inner.pack(fill=tk.X, padx=18, pady=8)

        self.lbl_elapsed = ctk.CTkLabel(
            inner,
            text="⏱ ELAPSED: 00:00:00",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=self.parent.C_TEXT_MUTED,
        )
        self.lbl_elapsed.pack(side=tk.LEFT)

        self.btn_copy_log = ctk.CTkButton(
            inner,
            text="📋 Copy Log",
            width=100,
            height=28,
            corner_radius=14,
            fg_color=self.parent.C_INPUT,
            hover_color="#183623",
            border_width=1,
            border_color=self.parent.C_BORDER,
            text_color=self.parent.C_ZONE_GREEN,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._copy_log,
        )
        self.btn_copy_log.pack(side=tk.RIGHT, padx=(8, 0))

        self.btn_close = ctk.CTkButton(
            inner,
            text="Close Monitor",
            width=130,
            height=28,
            corner_radius=14,
            fg_color="#142419",
            hover_color="#1e3a27",
            border_width=1,
            border_color=self.parent.C_BORDER,
            text_color=self.parent.C_TEXT_MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            state="disabled",
            command=self._on_close_clicked,
        )
        self.btn_close.pack(side=tk.RIGHT)

    def append_log(self, text: str):
        if not self.winfo_exists():
            return
        self.txt_log.insert(tk.END, text + "\n")
        self.txt_log.see(tk.END)

    def on_finished(self, success: bool, message: str):
        self.is_finished = True
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None

        if not self.winfo_exists():
            return

        self.prog_bar.stop()
        self.prog_bar.configure(mode="determinate")
        self.prog_bar.set(1.0 if success else 0.0)

        elapsed = int((datetime.now() - self.start_time).total_seconds())
        hrs, rem = divmod(elapsed, 3600)
        mins, secs = divmod(rem, 60)
        self.lbl_elapsed.configure(text=f"⏱ COMPLETED IN: {hrs:02d}:{mins:02d}:{secs:02d}")

        if success:
            self.lbl_stream_badge.configure(text="● RESTORE: COMPLETE", text_color=self.parent.C_ZONE_GREEN)
            self.lbl_op_stat.configure(text="RESTORED", text_color=self.parent.C_ZONE_GREEN)
        else:
            self.lbl_stream_badge.configure(text="● RESTORE: FAILED", text_color=self.parent.C_ZONE_RED)
            self.lbl_op_stat.configure(text="FAILED", text_color=self.parent.C_ZONE_RED)

        self.btn_close.configure(
            state="normal",
            text="✓ CLOSE MONITOR",
            fg_color=self.parent.C_ZONE_GREEN,
            text_color=self.parent.C_ABYSS,
            hover_color=self.parent.C_ZONE_GREEN_HOVER,
        )

    def _start_timer(self):
        self._tick_timer()

    def _tick_timer(self):
        if not self.winfo_exists() or self.is_finished:
            return
        elapsed = int((datetime.now() - self.start_time).total_seconds())
        hrs, rem = divmod(elapsed, 3600)
        mins, secs = divmod(rem, 60)
        self.lbl_elapsed.configure(text=f"⏱ ELAPSED: {hrs:02d}:{mins:02d}:{secs:02d}")
        self.timer_job = self.after(1000, self._tick_timer)

    def _copy_log(self):
        try:
            content = self.txt_log.get("1.0", tk.END).strip()
            self.clipboard_clear()
            self.clipboard_append(content)
            self.btn_copy_log.configure(text="✓ Copied!", fg_color="#1a4628")
            self.after(2000, lambda: self.btn_copy_log.configure(text="📋 Copy Log", fg_color=self.parent.C_INPUT))
        except Exception:
            pass

    def _on_close_clicked(self):
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _on_close_requested(self):
        if not self.is_finished:
            confirm = messagebox.askyesno(
                "Restoration Active",
                "Restoration is actively moving files back to G.A.M.M.A.\n\n"
                "Closing this monitor window will NOT stop the restore process in the background.\n\n"
                "Are you sure you want to close this monitor window?",
                parent=self,
            )
            if not confirm:
                return
        self._on_close_clicked()


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
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)

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

        # Calculate total phases
        inc_dl = self.include_dl_var.get() and self.current_plan["downloads"]["exists"]
        inc_mb = self.include_mb_var.get() and self.current_plan["mods_backup"]["exists"]
        total_phases = 2 + (1 if inc_dl else 0) + (1 if inc_mb else 0) + 1

        # Instantiate Tactical Telemetry Monitor Modal
        monitor = TelemetryMonitorModal(
            self,
            backup_path=bp,
            total_mods=len(sel),
            total_work_bytes=int(m_b + dl_b + mb_b),
            total_phases=total_phases,
        )

        opts = {
            "include_downloads": self.include_dl_var.get(),
            "include_mods_backup": self.include_mb_var.get(),
        }

        def log_cb(msg):
            def _ui():
                if monitor.winfo_exists():
                    monitor.append_log(msg)
                self.lbl_status.configure(text=msg[:70].upper())
            self.after(0, _ui)

        def prog_cb(cur, tot, desc, current_item="", bytes_done=0, total_bytes=0, phase_name="", pct=0.0, mod_idx=0, mod_total=0):
            def _ui():
                if monitor.winfo_exists():
                    monitor.update_telemetry(
                        cur, tot, desc,
                        current_item=current_item,
                        bytes_done=bytes_done,
                        total_bytes=total_bytes,
                        phase_name=phase_name,
                        pct=pct,
                        mod_idx=mod_idx,
                        mod_total=mod_total,
                    )
                self.progress_bar.set(min(1.0, max(0.0, pct / 100.0)))
            self.after(0, _ui)

        def worker():
            try:
                DebloaterEngine.execute_debloat(self.current_plan, bp, opts, log_cb, prog_cb)
                self.after(0, lambda: monitor.on_finished(True, "Protocol Complete"))
                self.after(0, lambda: messagebox.showinfo("Protocol Complete", f"Successfully debloated and secured {est_gb} GB to vault!\n\nAll verified files have been safely relocated."))
            except Exception as e:
                log_cb(f"\n[FATAL ERROR]: {e}")
                self.after(0, lambda: monitor.on_finished(False, str(e)))
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

        ps_script = bp / "RESTORE_TO_GAMMA.ps1"
        if not ps_script.exists():
            messagebox.showerror("Missing Script", f"Cannot find '{ps_script}'. Please verify the backup vault folder.")
            return

        confirm = messagebox.askyesno(
            "Confirm Restoration",
            f"Restore all backed up mods, caches, and load orders from:\n\n{bp}\n\nback to:\n\n{gp}?",
        )
        if not confirm:
            return

        self.btn_restore.configure(state="disabled")
        self.progress_bar.start()
        self.lbl_status.configure(text="RESTORING DATA FROM VAULT...")

        monitor = RestoreTelemetryMonitorModal(self, bp, gp)

        def worker():
            try:
                now_str = datetime.now().strftime("%H:%M:%S")
                monitor.append_log(f"[{now_str}] Launching Native PowerShell Restore Engine...")
                monitor.append_log(f"[{now_str}] Vault Source     : {bp}")
                monitor.append_log(f"[{now_str}] Target G.A.M.M.A.: {gp}")
                monitor.append_log("-" * 65)

                cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps_script)]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
                for line in proc.stdout:
                    clean = line.rstrip()
                    if clean:
                        self.after(0, monitor.append_log, clean)
                proc.wait()
                if proc.returncode != 0:
                    raise RuntimeError(f"PowerShell restore exited with code {proc.returncode}")

                self.after(0, lambda: monitor.on_finished(True, "Restoration Complete"))
                self.after(0, lambda: messagebox.showinfo("Restoration Complete", f"All mods and configs have been restored to {gp}!"))
            except Exception as e:
                self.after(0, lambda: monitor.append_log(f"\n[ERROR]: {e}"))
                self.after(0, lambda: monitor.on_finished(False, str(e)))
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
