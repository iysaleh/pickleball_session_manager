"""
Standalone updater UI for Pickleball Session Manager.

This script runs independently from the main application in a separate process.
It shows a tkinter progress window while updating the application files.

IMPORTANT: This file must be completely self-contained.
Do NOT import anything from the python/ package since it gets replaced during update.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile


CONFIG_PATH = os.path.join(tempfile.gettempdir(), 'pickleball_update_config.json')

PRESERVE_ITEMS = {
    'exports', 'logs', 'node_modules', '.git', '__pycache__',
    'pickleball.ico', 'players.json', 'players-singles.json',
    'players-teams.json',
}

PRESERVE_PREFIXES = ('pickleball_session_', 'pickleball_log_')


def load_config():
    """Load the update configuration from the temp JSON file."""
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def is_process_running(pid):
    """Check if a process with the given PID is still running."""
    if sys.platform == 'win32':
        import ctypes
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            exit_code = ctypes.c_ulong()
            kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            kernel32.CloseHandle(handle)
            return exit_code.value == STILL_ACTIVE
        return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False


def extract_and_replace(zip_path, app_dir, progress_callback=None):
    """
    Extract the downloaded zip and replace app files, preserving user data.

    progress_callback(phase, current, total, detail_text) is called during
    extraction and installation phases. Phase values: 'extract', 'install',
    'warn', 'error'.

    Returns True on success.
    """
    extract_dir = tempfile.mkdtemp(prefix='pickleball_extract_')
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            members = zf.namelist()
            total = len(members)
            for i, member in enumerate(members):
                zf.extract(member, extract_dir)
                if progress_callback and i % 5 == 0:
                    progress_callback('extract', i, total, os.path.basename(member))

        # GitHub zipball extracts to a subdirectory like 'owner-repo-sha/'
        extracted_items = os.listdir(extract_dir)
        if (len(extracted_items) == 1
                and os.path.isdir(os.path.join(extract_dir, extracted_items[0]))):
            source_dir = os.path.join(extract_dir, extracted_items[0])
        else:
            source_dir = extract_dir

        items = [
            item for item in os.listdir(source_dir)
            if item not in PRESERVE_ITEMS
            and not any(item.startswith(p) for p in PRESERVE_PREFIXES)
        ]

        for i, item in enumerate(items):
            src = os.path.join(source_dir, item)
            dst = os.path.join(app_dir, item)

            if progress_callback:
                progress_callback('install', i, len(items), item)

            try:
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            except PermissionError:
                if progress_callback:
                    progress_callback('warn', i, len(items),
                                      f"Skipped (in use): {item}")

        return True
    except Exception as e:
        if progress_callback:
            progress_callback('error', 0, 0, str(e))
        return False
    finally:
        try:
            shutil.rmtree(extract_dir, ignore_errors=True)
        except Exception:
            pass


def run_with_gui(config):
    """Run the update process with a visible tkinter progress window."""
    import tkinter as tk
    from tkinter import ttk

    app_dir = config['app_dir']
    zip_path = config['zip_path']
    parent_pid = config['parent_pid']
    python_exe = config['python_exe']
    new_version = config['new_version']

    root = tk.Tk()
    root.title(f"Pickleball Session Manager — Updating to v{new_version}")
    root.geometry("540x400")
    root.resizable(False, False)
    root.configure(bg='#1e1e1e')

    # Center on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() - 540) // 2
    y = (root.winfo_screenheight() - 400) // 2
    root.geometry(f"540x400+{x}+{y}")

    # Try to set the app icon
    try:
        icon_path = os.path.join(app_dir, 'pickleball.ico')
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    # -- Build UI widgets --
    title_label = tk.Label(
        root, text="Pickleball Session Manager",
        font=("Segoe UI", 18, "bold"), fg="#ffffff", bg="#1e1e1e")
    title_label.pack(pady=(30, 5))

    version_label = tk.Label(
        root, text=f"Updating to v{new_version}",
        font=("Segoe UI", 12), fg="#888888", bg="#1e1e1e")
    version_label.pack(pady=(0, 30))

    status_label = tk.Label(
        root, text="Preparing update...",
        font=("Segoe UI", 13), fg="#4CAF50", bg="#1e1e1e")
    status_label.pack(pady=(5, 15))

    # Progress bar
    style = ttk.Style()
    style.theme_use('default')
    style.configure(
        "green.Horizontal.TProgressbar",
        troughcolor='#333333', background='#4CAF50', thickness=22)

    progress_frame = tk.Frame(root, bg="#1e1e1e")
    progress_frame.pack(pady=5, padx=50, fill='x')

    progress = ttk.Progressbar(
        progress_frame, length=440, mode='determinate',
        style="green.Horizontal.TProgressbar", maximum=100)
    progress.pack(fill='x')

    step_label = tk.Label(
        root, text="",
        font=("Segoe UI", 10), fg="#666666", bg="#1e1e1e")
    step_label.pack(pady=(8, 0))

    detail_label = tk.Label(
        root, text="",
        font=("Segoe UI", 9), fg="#555555", bg="#1e1e1e", wraplength=460)
    detail_label.pack(pady=(5, 10))

    error_frame = tk.Frame(root, bg="#1e1e1e")

    def set_status(msg, step_text="", detail="", pct=0):
        status_label.config(text=msg)
        step_label.config(text=step_text)
        detail_label.config(text=detail)
        progress['value'] = pct
        root.update()

    def on_error(msg):
        status_label.config(text="Update Failed", fg="#ff4444")
        detail_label.config(text=msg, fg="#ff6666")
        close_btn = tk.Button(
            error_frame, text="Close", command=root.destroy,
            font=("Segoe UI", 11), bg="#555555", fg="white",
            padx=20, pady=5, relief='flat')
        close_btn.pack(pady=10)
        error_frame.pack()
        root.update()

    def do_update():
        try:
            # Step 1: Wait for parent process to exit
            set_status("Waiting for application to close...",
                       "Step 1 of 4", f"Process {parent_pid}", 5)

            waited = 0.0
            while is_process_running(parent_pid) and waited < 30:
                time.sleep(0.5)
                waited += 0.5
                set_status("Waiting for application to close...",
                           "Step 1 of 4", f"Waiting... ({int(waited)}s)",
                           5 + min(waited, 20))

            # Step 2: Verify download
            set_status("Verifying download...", "Step 2 of 4",
                       os.path.basename(zip_path), 28)
            time.sleep(0.3)

            if not os.path.exists(zip_path):
                on_error(f"Update file not found:\n{zip_path}")
                return

            # Step 3: Extract and install files
            def on_progress(phase, current, total, detail_text):
                if phase == 'extract':
                    pct = 30 + (current / max(total, 1)) * 25
                    set_status("Extracting update files...", "Step 3 of 4",
                               detail_text, pct)
                elif phase == 'install':
                    pct = 55 + (current / max(total, 1)) * 35
                    set_status("Installing files...", "Step 3 of 4",
                               f"Copying: {detail_text}", pct)
                elif phase == 'warn':
                    detail_label.config(text=f"Warning: {detail_text}")
                    root.update()
                elif phase == 'error':
                    on_error(detail_text)

            set_status("Extracting and installing...", "Step 3 of 4", "", 30)
            success = extract_and_replace(zip_path, app_dir, on_progress)

            if not success:
                if not error_frame.winfo_children():
                    on_error("Failed to extract and install update files.")
                return

            # Step 4: Clean up and relaunch
            set_status("Update complete!", "Step 4 of 4",
                       "Launching updated application...", 95)

            try:
                os.remove(zip_path)
            except Exception:
                pass
            try:
                os.remove(CONFIG_PATH)
            except Exception:
                pass

            main_py = os.path.join(app_dir, 'main.py')
            if sys.platform == 'win32':
                subprocess.Popen(
                    [python_exe, main_py],
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            else:
                subprocess.Popen(
                    [python_exe, main_py],
                    start_new_session=True)

            set_status("Update complete!", "Done",
                       "Application is restarting...", 100)
            root.update()
            time.sleep(2)
            root.destroy()

        except Exception as e:
            on_error(str(e))

    root.after(500, do_update)
    root.mainloop()


def run_headless(config):
    """Fallback: run update without GUI (if tkinter is unavailable)."""
    app_dir = config['app_dir']
    zip_path = config['zip_path']
    parent_pid = config['parent_pid']
    python_exe = config['python_exe']

    print("Pickleball Session Manager Updater")
    print("=" * 40)

    print("Waiting for application to close...")
    waited = 0
    while is_process_running(parent_pid) and waited < 30:
        time.sleep(1)
        waited += 1
        print(f"  Waiting... ({waited}s)")

    print("Extracting and installing update...")
    success = extract_and_replace(
        zip_path, app_dir,
        lambda p, c, t, d: print(f"  [{p}] {d}"))

    if success:
        print("Update complete! Restarting application...")
        try:
            os.remove(zip_path)
        except Exception:
            pass
        try:
            os.remove(CONFIG_PATH)
        except Exception:
            pass
        main_py = os.path.join(app_dir, 'main.py')
        subprocess.Popen([python_exe, main_py])
        print("Done.")
    else:
        print("Update failed!")
        if sys.platform == 'win32':
            input("Press Enter to close...")


if __name__ == '__main__':
    config = load_config()
    try:
        import tkinter
        run_with_gui(config)
    except ImportError:
        run_headless(config)
