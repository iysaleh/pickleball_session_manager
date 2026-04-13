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


def _get_pythonw() -> str:
    """Get pythonw.exe (GUI Python, no console) on Windows.
    Falls back to python.exe if pythonw.exe is not found."""
    if sys.platform == 'win32':
        python_dir = os.path.dirname(sys.executable)
        pythonw = os.path.join(python_dir, 'pythonw.exe')
        if os.path.exists(pythonw):
            return pythonw
    return sys.executable


def create_update_script(app_dir: str, zip_path: str, pid_to_kill: int,
                         new_version: str = 'unknown') -> str:
    """
    Prepare the standalone updater script and its configuration.

    Copies python/update_ui.py to a temp location and writes a JSON config
    file so the updater can run independently after the main app exits.

    Returns the path to the updater script in the temp directory.
    """
    config = {
        'app_dir': app_dir,
        'zip_path': zip_path,
        'parent_pid': pid_to_kill,
        'python_exe': sys.executable,
        'new_version': new_version,
    }
    config_path = os.path.join(tempfile.gettempdir(), 'pickleball_update_config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    # Copy update_ui.py to temp so it can run after the source dir is replaced
    source_ui = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'update_ui.py')
    dest_script = os.path.join(tempfile.gettempdir(), 'pickleball_updater.py')
    shutil.copy2(source_ui, dest_script)

    return dest_script


def launch_update(release_info: dict) -> bool:
    """
    Download the release and launch the standalone updater UI.
    The updater runs as a separate process with its own tkinter window
    that shows progress while replacing files and relaunching the app.

    Returns True if the updater was launched successfully.
    """
    app_dir = get_app_directory()
    zipball_url = release_info.get('zipball_url', '')
    new_version = release_info.get('version', 'unknown')

    if not zipball_url:
        logger.error("No zipball URL in release info")
        return False

    # Download to temp
    zip_path = os.path.join(tempfile.gettempdir(), 'pickleball_update.zip')
    logger.info(f"Downloading update from {zipball_url}...")

    if not _download_release_zip(zipball_url, zip_path):
        return False

    logger.info(f"Update downloaded to {zip_path}")

    # Create updater script and config
    pid = os.getpid()
    script_path = create_update_script(app_dir, zip_path, pid, new_version)
    logger.info(f"Updater script created at {script_path}")

    try:
        # Use pythonw.exe on Windows for a clean GUI-only experience (no console)
        python_cmd = _get_pythonw()

        if sys.platform == 'win32':
            subprocess.Popen(
                [python_cmd, script_path],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )
        else:
            subprocess.Popen(
                [python_cmd, script_path],
                start_new_session=True,
                close_fds=True
            )
        logger.info("Updater launched. Application will exit now.")
        return True
    except Exception as e:
        logger.error(f"Failed to launch updater: {e}")
        return False
