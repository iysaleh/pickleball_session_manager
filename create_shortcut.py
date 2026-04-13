#!/usr/bin/env python3
"""
Create a desktop shortcut for Pickleball Session Manager.

Supports Windows, macOS, and Linux.
On Windows, the shortcut uses a pickleball icon.

Usage:
    python create_shortcut.py
"""

import os
import sys
import platform


def get_desktop_path() -> str:
    """Get the user's desktop directory path."""
    if sys.platform == 'win32':
        import winreg
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
            )
            desktop = winreg.QueryValueEx(key, "Desktop")[0]
            winreg.CloseKey(key)
            return desktop
        except Exception:
            return os.path.join(os.path.expanduser("~"), "Desktop")
    else:
        return os.path.join(os.path.expanduser("~"), "Desktop")


def get_bundled_ico_path() -> str:
    """Return the path to the bundled pickleball.ico file."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "pickleball.ico")


def _get_windows_native_icon_path(ico_source: str, desktop: str) -> str:
    """Get a Windows-native path for the icon, copying if needed (e.g. from WSL)."""
    import shutil

    # If already a native Windows path, use it directly
    if not ico_source.startswith('\\\\wsl') and not ico_source.startswith('/'):
        return ico_source

    # Copy icon to a Windows-native location next to the shortcut
    # Use %LOCALAPPDATA%/PickleballSessionManager/ for a clean location
    local_app_data = os.environ.get('LOCALAPPDATA', '')
    if local_app_data and os.path.isdir(local_app_data):
        icon_dir = os.path.join(local_app_data, 'PickleballSessionManager')
    else:
        # Fallback: put it on the desktop
        icon_dir = desktop

    os.makedirs(icon_dir, exist_ok=True)
    dest = os.path.join(icon_dir, 'pickleball.ico')
    shutil.copy2(ico_source, dest)
    return dest


def create_windows_shortcut(app_dir: str, desktop: str):
    """Create a .lnk shortcut on Windows."""
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut_path = os.path.join(desktop, "Pickleball Session Manager.lnk")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = sys.executable
        shortcut.Arguments = f'"{os.path.join(app_dir, "main.py")}"'
        shortcut.WorkingDirectory = app_dir
        shortcut.Description = "Pickleball Session Manager"

        # Use bundled pickleball icon
        ico_path = get_bundled_ico_path()

        # Ensure icon is on a Windows-native path (not WSL network path)
        native_ico = _get_windows_native_icon_path(ico_path, desktop)
        shortcut.IconLocation = native_ico

        shortcut.save()
        print(f"Shortcut created: {shortcut_path}")
        print(f"Icon: {native_ico}")
        return True
    except ImportError:
        # Fallback: create a .bat file if pywin32 is not available
        bat_path = os.path.join(desktop, "Pickleball Session Manager.bat")
        python_exe = sys.executable
        with open(bat_path, 'w') as f:
            f.write(f'@echo off\n')
            f.write(f'cd /d "{app_dir}"\n')
            f.write(f'"{python_exe}" "{os.path.join(app_dir, "main.py")}"\n')
        print(f"Batch shortcut created: {bat_path}")
        print("Note: Install pywin32 (`pip install pywin32`) for a proper .lnk shortcut with icon.")
        return True


def create_macos_shortcut(app_dir: str, desktop: str):
    """Create a .command file on macOS."""
    shortcut_path = os.path.join(desktop, "Pickleball Session Manager.command")
    python_exe = sys.executable

    with open(shortcut_path, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write(f'cd "{app_dir}"\n')
        f.write(f'"{python_exe}" "{os.path.join(app_dir, "main.py")}"\n')

    os.chmod(shortcut_path, 0o755)
    print(f"Shortcut created: {shortcut_path}")
    return True


def create_linux_shortcut(app_dir: str, desktop: str):
    """Create a .desktop file on Linux."""
    shortcut_path = os.path.join(desktop, "pickleball-session-manager.desktop")
    python_exe = sys.executable

    with open(shortcut_path, 'w') as f:
        f.write("[Desktop Entry]\n")
        f.write("Type=Application\n")
        f.write("Name=Pickleball Session Manager\n")
        f.write("Comment=Manage pickleball sessions and matches\n")
        f.write(f"Exec={python_exe} {os.path.join(app_dir, 'main.py')}\n")
        f.write(f"Path={app_dir}\n")
        f.write("Terminal=false\n")
        f.write("Categories=Utility;\n")

    os.chmod(shortcut_path, 0o755)
    print(f"Shortcut created: {shortcut_path}")
    return True


def main():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    desktop = get_desktop_path()

    if not os.path.isdir(desktop):
        print(f"Desktop directory not found: {desktop}")
        sys.exit(1)

    print(f"Application directory: {app_dir}")
    print(f"Desktop directory: {desktop}")
    print(f"Python executable: {sys.executable}")
    print(f"Platform: {platform.system()}")
    print()

    if sys.platform == 'win32':
        success = create_windows_shortcut(app_dir, desktop)
    elif sys.platform == 'darwin':
        success = create_macos_shortcut(app_dir, desktop)
    else:
        success = create_linux_shortcut(app_dir, desktop)

    if success:
        print("\nDesktop shortcut created successfully!")
    else:
        print("\nFailed to create desktop shortcut.")
        sys.exit(1)


if __name__ == '__main__':
    main()
