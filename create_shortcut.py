#!/usr/bin/env python3
"""
Create a desktop shortcut for Pickleball Session Manager.

Supports Windows, macOS, and Linux.
On Windows, the shortcut uses a tennis ball icon.

Usage:
    python create_shortcut.py
"""

import os
import sys
import struct
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


def _render_tennis_ball(size: int) -> list:
    """Render a tennis ball image at the given size. Returns list of rows of (B,G,R,A) tuples."""
    import math
    pixels = []
    cx, cy = size / 2, size / 2
    radius = size / 2 - 1
    # Scale seam thickness relative to image size
    seam_thickness = max(0.08, 0.14 * (32 / size))
    # Scale edge AA width
    aa_width = max(1.0, size / 32.0)

    for y in range(size):
        row = []
        for x in range(size):
            dx = x - cx + 0.5
            dy = y - cy + 0.5
            dist = math.sqrt(dx * dx + dy * dy)

            if dist <= radius + aa_width:
                # Base tennis ball yellow-green (optic yellow)
                base_r, base_g, base_b = 207, 220, 40

                # 3D sphere shading with specular highlight
                norm_dist = dist / radius
                # Diffuse: light from upper-left
                light_x, light_y = -0.5, -0.6
                light_len = math.sqrt(light_x ** 2 + light_y ** 2)
                light_x /= light_len
                light_y /= light_len
                if dist > 0:
                    nx, ny = dx / dist, dy / dist
                else:
                    nx, ny = 0, 0
                nz = math.sqrt(max(0, 1 - min(1, norm_dist) ** 2))
                diffuse = max(0, -(nx * light_x + ny * light_y) * 0.3 + nz * 0.7)
                diffuse = 0.55 + diffuse * 0.55

                # Specular highlight (bright spot upper-left)
                spec_x = dx / radius + 0.35
                spec_y = dy / radius + 0.4
                spec_dist = math.sqrt(spec_x ** 2 + spec_y ** 2)
                specular = max(0, 1 - spec_dist * 2.2) ** 3

                r = min(255, int(base_r * diffuse + 255 * specular * 0.5))
                g = min(255, int(base_g * diffuse + 255 * specular * 0.5))
                b = min(255, int(base_b * diffuse + 255 * specular * 0.3))

                # Felt texture (subtle noise via deterministic pattern)
                felt = ((x * 7 + y * 13) % 5 - 2) * max(1, size // 32)
                r = max(0, min(255, r + felt))
                g = max(0, min(255, g + felt))
                b = max(0, min(255, b + felt))

                # Darker rim for depth
                if norm_dist > 0.85:
                    rim_factor = 1 - (norm_dist - 0.85) / 0.15 * 0.35
                    r = int(r * rim_factor)
                    g = int(g * rim_factor)
                    b = int(b * rim_factor)

                # Tennis ball seam curves (two mirrored S-curves)
                norm_x = dx / radius if radius > 0 else 0
                norm_y = dy / radius if radius > 0 else 0

                # Classic tennis ball seam: two curves that wrap around
                seam1_y = 0.45 * math.sin(norm_x * math.pi * 1.3 + 0.2)
                seam2_y = -0.45 * math.sin(norm_x * math.pi * 1.3 + 0.2)
                seam1_dist = abs(norm_y - seam1_y)
                seam2_dist = abs(norm_y - seam2_y)
                min_seam_dist = min(seam1_dist, seam2_dist)

                if min_seam_dist < seam_thickness and norm_dist < 0.92:
                    # Anti-aliased seam
                    seam_alpha = max(0, 1 - min_seam_dist / seam_thickness)
                    seam_alpha = seam_alpha ** 0.6  # Softer falloff
                    # Seam is white/light with slight shadow edge
                    seam_r, seam_g, seam_b = 245, 245, 240
                    r = int(r * (1 - seam_alpha) + seam_r * seam_alpha)
                    g = int(g * (1 - seam_alpha) + seam_g * seam_alpha)
                    b = int(b * (1 - seam_alpha) + seam_b * seam_alpha)

                # Alpha with smooth anti-aliased edge
                if dist > radius:
                    a = max(0, min(255, int(255 * (1 - (dist - radius) / aa_width))))
                else:
                    a = 255
            else:
                r, g, b, a = 0, 0, 0, 0

            row.append((max(0, min(255, b)),
                        max(0, min(255, g)),
                        max(0, min(255, r)),
                        max(0, min(255, a))))
        pixels.append(row)
    return pixels


def _build_bmp_image_data(pixels: list, size: int) -> bytes:
    """Build BMP image data (header + pixel bytes) for an ICO entry."""
    bmp_header_size = 40
    pixel_data_size = size * size * 4

    bmp_info = struct.pack('<IiiHHIIiiII',
        bmp_header_size, size, size * 2, 1, 32, 0,
        pixel_data_size, 0, 0, 0, 0)

    pixel_bytes = bytearray()
    for row in reversed(pixels):
        for b, g, r, a in row:
            pixel_bytes.extend((b, g, r, a))

    return bmp_info + bytes(pixel_bytes)


def create_tennis_ball_ico(ico_path: str):
    """Generate a multi-size tennis ball .ico file (16, 32, 48, 64, 256)."""
    sizes = [16, 32, 48, 64, 256]
    images = []
    for s in sizes:
        pixels = _render_tennis_ball(s)
        img_data = _build_bmp_image_data(pixels, s)
        images.append((s, img_data))

    num_images = len(images)
    # ICO header: 6 bytes, each directory entry: 16 bytes
    header_size = 6 + 16 * num_images
    current_offset = header_size

    # Build ICO header
    ico_header = struct.pack('<HHH', 0, 1, num_images)

    # Build directory entries
    dir_entries = b''
    for s, img_data in images:
        w = 0 if s >= 256 else s  # 0 means 256 in ICO format
        h = 0 if s >= 256 else s
        dir_entries += struct.pack('<BBBBHHII',
            w, h, 0, 0, 1, 32, len(img_data), current_offset)
        current_offset += len(img_data)

    with open(ico_path, 'wb') as f:
        f.write(ico_header)
        f.write(dir_entries)
        for _, img_data in images:
            f.write(img_data)


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

        # Create and set tennis ball icon
        ico_path = os.path.join(app_dir, "pickleball.ico")
        if not os.path.exists(ico_path):
            create_tennis_ball_ico(ico_path)

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
