"""
Auto-updater for Pickleball Session Manager.

Checks GitHub releases for new versions, downloads updates,
and replaces the local source code with the latest release.
"""

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import Optional, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from python.version import __version__, GITHUB_REPO_OWNER, GITHUB_REPO_NAME

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
RELEASES_URL = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"


def _parse_version(version_str: str) -> Tuple[int, ...]:
    """Parse a version string like 'v1.2.3' or '1.2.3' into a tuple of ints."""
    cleaned = version_str.strip().lstrip('v')
    parts = []
    for part in cleaned.split('.'):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def is_newer_version(remote_version: str, local_version: str) -> bool:
    """Check if remote_version is newer than local_version."""
    return _parse_version(remote_version) > _parse_version(local_version)


def get_current_version() -> str:
    """Return the current application version."""
    return __version__


def check_for_updates() -> Optional[dict]:
    """
    Check GitHub for the latest release.

    Returns a dict with release info if a newer version is available:
        {
            'version': str,       # e.g. '1.1.0'
            'tag_name': str,      # e.g. 'v1.1.0'
            'release_notes': str, # Markdown body
            'zipball_url': str,   # URL to download source zip
            'html_url': str,      # URL to view release on GitHub
        }
    Returns None if already up to date or on error.
    """
    try:
        req = Request(RELEASES_URL, headers={
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': f'PickleballSessionManager/{__version__}'
        })
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        tag_name = data.get('tag_name', '')
        remote_version = tag_name.lstrip('v')

        if not is_newer_version(remote_version, __version__):
            return None

        return {
            'version': remote_version,
            'tag_name': tag_name,
            'release_notes': data.get('body', 'No release notes available.'),
            'zipball_url': data.get('zipball_url', ''),
            'html_url': data.get('html_url', ''),
        }
    except HTTPError as e:
        if e.code == 404:
            logger.info("No releases found on GitHub.")
        else:
            logger.warning(f"HTTP error checking for updates: {e.code} {e.reason}")
        return None
    except (URLError, OSError) as e:
        logger.warning(f"Network error checking for updates: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error checking for updates: {e}")
        return None


def get_app_directory() -> str:
    """Get the root directory of the application (where main.py lives)."""
    # This file is at python/updater.py, so app root is one level up
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _download_release_zip(zipball_url: str, dest_path: str) -> bool:
    """Download a release zipball to dest_path. Returns True on success."""
    try:
        req = Request(zipball_url, headers={
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': f'PickleballSessionManager/{__version__}'
        })
        with urlopen(req, timeout=60) as resp:
            with open(dest_path, 'wb') as f:
                shutil.copyfileobj(resp, f)
        return True
    except Exception as e:
        logger.error(f"Failed to download release: {e}")
        return False


def _extract_and_replace(zip_path: str, app_dir: str) -> bool:
    """
    Extract the downloaded zip and replace source files in app_dir.
    Preserves user data (exports/, session files, preferences).
    Returns True on success.
    """
    try:
        with tempfile.TemporaryDirectory() as extract_dir:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)

            # GitHub zipball extracts to a subdirectory like 'owner-repo-sha/'
            extracted_items = os.listdir(extract_dir)
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
                source_dir = os.path.join(extract_dir, extracted_items[0])
            else:
                source_dir = extract_dir

            # Files/directories to preserve (never overwrite)
            preserve = {
                'exports', 'logs', 'node_modules', '.git', '__pycache__',
                'pickleball.ico', 'players.json', 'players-singles.json',
                'players-teams.json',
            }
            # File patterns to preserve (session files, logs, preferences)
            preserve_prefixes = ('pickleball_session_', 'pickleball_log_')

            # Copy new files over existing ones
            for item in os.listdir(source_dir):
                if item in preserve:
                    continue
                if any(item.startswith(p) for p in preserve_prefixes):
                    continue

                src = os.path.join(source_dir, item)
                dst = os.path.join(app_dir, item)

                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

        return True
    except Exception as e:
        logger.error(f"Failed to extract and replace files: {e}")
        return False


def create_update_script(app_dir: str, zip_path: str, pid_to_kill: int) -> str:
    """
    Create a platform-appropriate script that:
    1. Waits for the current process to exit
    2. Extracts the update
    3. Relaunches the application

    Returns the path to the created script.
    """
    python_exe = sys.executable
    main_py = os.path.join(app_dir, 'main.py')

    if sys.platform == 'win32':
        script_path = os.path.join(tempfile.gettempdir(), 'pickleball_update.bat')
        with open(script_path, 'w') as f:
            f.write('@echo off\n')
            f.write('echo Updating Pickleball Session Manager...\n')
            f.write('echo Waiting for application to close...\n')
            # Wait for the process to exit
            f.write(f':waitloop\n')
            f.write(f'tasklist /FI "PID eq {pid_to_kill}" 2>NUL | find /I "{pid_to_kill}" >NUL\n')
            f.write(f'if %ERRORLEVEL% == 0 (\n')
            f.write(f'    timeout /t 1 /nobreak >NUL\n')
            f.write(f'    goto waitloop\n')
            f.write(f')\n')
            f.write('echo Application closed. Applying update...\n')
            # Run the extraction via Python
            updater_module = os.path.abspath(__file__)
            f.write(f'"{python_exe}" -c "import sys; sys.path.insert(0, r\'{app_dir}\'); ')
            f.write(f'from python.updater import _extract_and_replace; ')
            f.write(f'result = _extract_and_replace(r\'{zip_path}\', r\'{app_dir}\'); ')
            f.write(f'print(\'Update applied successfully!\' if result else \'Update failed!\')"\n')
            f.write('echo Relaunching application...\n')
            f.write(f'start "" "{python_exe}" "{main_py}"\n')
            # Clean up
            f.write(f'del "{zip_path}" 2>NUL\n')
            f.write('exit\n')
    else:
        script_path = os.path.join(tempfile.gettempdir(), 'pickleball_update.sh')
        with open(script_path, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write('echo "Updating Pickleball Session Manager..."\n')
            f.write('echo "Waiting for application to close..."\n')
            # Wait for the process to exit
            f.write(f'while kill -0 {pid_to_kill} 2>/dev/null; do\n')
            f.write('    sleep 1\n')
            f.write('done\n')
            f.write('echo "Application closed. Applying update..."\n')
            # Run the extraction via Python
            f.write(f'PYTHONPATH="{app_dir}" "{python_exe}" -c "\n')
            f.write(f'import sys; sys.path.insert(0, \'{app_dir}\')\n')
            f.write(f'from python.updater import _extract_and_replace\n')
            f.write(f'result = _extract_and_replace(\'{zip_path}\', \'{app_dir}\')\n')
            f.write(f'print(\'Update applied successfully!\' if result else \'Update failed!\')\n')
            f.write('"\n')
            f.write('echo "Relaunching application..."\n')
            f.write(f'"{python_exe}" "{main_py}" &\n')
            # Clean up
            f.write(f'rm -f "{zip_path}"\n')
            f.write(f'rm -f "{script_path}"\n')
        os.chmod(script_path, 0o755)

    return script_path


def launch_update(release_info: dict) -> bool:
    """
    Download the release and launch the update script.
    This will terminate the current application.

    Returns True if the update script was launched successfully.
    """
    app_dir = get_app_directory()
    zipball_url = release_info.get('zipball_url', '')
    if not zipball_url:
        logger.error("No zipball URL in release info")
        return False

    # Download to temp
    zip_path = os.path.join(tempfile.gettempdir(), 'pickleball_update.zip')
    logger.info(f"Downloading update from {zipball_url}...")

    if not _download_release_zip(zipball_url, zip_path):
        return False

    logger.info(f"Update downloaded to {zip_path}")

    # Create and launch the update script
    pid = os.getpid()
    script_path = create_update_script(app_dir, zip_path, pid)
    logger.info(f"Update script created at {script_path}")

    try:
        if sys.platform == 'win32':
            # Launch the batch script detached
            subprocess.Popen(
                ['cmd', '/c', script_path],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )
        else:
            subprocess.Popen(
                ['bash', script_path],
                start_new_session=True,
                close_fds=True
            )
        logger.info("Update script launched. Application will exit now.")
        return True
    except Exception as e:
        logger.error(f"Failed to launch update script: {e}")
        return False
