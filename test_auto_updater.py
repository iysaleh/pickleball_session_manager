"""Tests for the auto-updater and version system."""

import json
import os
import struct
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.version import __version__, GITHUB_REPO_OWNER, GITHUB_REPO_NAME
from python.updater import (
    _parse_version,
    is_newer_version,
    get_current_version,
    check_for_updates,
    get_app_directory,
    _extract_and_replace,
    create_update_script,
    RELEASES_URL,
)


class TestVersionModule(unittest.TestCase):
    """Test the version module."""

    def test_version_format(self):
        """Version string should be in X.Y.Z format."""
        parts = __version__.split('.')
        self.assertEqual(len(parts), 3, f"Version should have 3 parts: {__version__}")
        for part in parts:
            self.assertTrue(part.isdigit(), f"Version part '{part}' should be numeric")

    def test_github_repo_owner(self):
        """Repo owner should be set."""
        self.assertEqual(GITHUB_REPO_OWNER, "iysaleh")

    def test_github_repo_name(self):
        """Repo name should be set."""
        self.assertEqual(GITHUB_REPO_NAME, "pickleball_session_manager")

    def test_version_importable_from_package(self):
        """Version should be importable from the python package."""
        from python import __version__ as pkg_version
        self.assertEqual(pkg_version, __version__)

    def test_get_current_version(self):
        """get_current_version should return the module version."""
        self.assertEqual(get_current_version(), __version__)


class TestVersionParsing(unittest.TestCase):
    """Test version parsing and comparison logic."""

    def test_parse_simple_version(self):
        self.assertEqual(_parse_version("1.2.3"), (1, 2, 3))

    def test_parse_version_with_v_prefix(self):
        self.assertEqual(_parse_version("v1.2.3"), (1, 2, 3))

    def test_parse_version_with_spaces(self):
        self.assertEqual(_parse_version("  v1.0.0  "), (1, 0, 0))

    def test_newer_major(self):
        self.assertTrue(is_newer_version("2.0.0", "1.0.0"))

    def test_newer_minor(self):
        self.assertTrue(is_newer_version("1.1.0", "1.0.0"))

    def test_newer_patch(self):
        self.assertTrue(is_newer_version("1.0.1", "1.0.0"))

    def test_same_version(self):
        self.assertFalse(is_newer_version("1.0.0", "1.0.0"))

    def test_older_version(self):
        self.assertFalse(is_newer_version("1.0.0", "1.0.1"))

    def test_newer_with_v_prefix(self):
        self.assertTrue(is_newer_version("v2.0.0", "1.0.0"))

    def test_compare_current_to_same(self):
        self.assertFalse(is_newer_version(__version__, __version__))


class TestCheckForUpdates(unittest.TestCase):
    """Test the update checking logic."""

    def test_releases_url_format(self):
        """Releases URL should point to the correct repo."""
        self.assertIn("iysaleh", RELEASES_URL)
        self.assertIn("pickleball_session_manager", RELEASES_URL)
        self.assertIn("releases/latest", RELEASES_URL)

    @patch('python.updater.urlopen')
    def test_no_update_when_same_version(self, mock_urlopen):
        """Should return None when remote version matches local."""
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({
            'tag_name': f'v{__version__}',
            'body': 'Current release',
            'zipball_url': 'https://example.com/zip',
            'html_url': 'https://example.com',
        }).encode('utf-8')
        mock_urlopen.return_value = mock_response

        result = check_for_updates()
        self.assertIsNone(result)

    @patch('python.updater.urlopen')
    def test_update_available_when_newer(self, mock_urlopen):
        """Should return release info when remote is newer."""
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({
            'tag_name': 'v99.0.0',
            'body': 'New features!',
            'zipball_url': 'https://example.com/zip',
            'html_url': 'https://example.com/release',
        }).encode('utf-8')
        mock_urlopen.return_value = mock_response

        result = check_for_updates()
        self.assertIsNotNone(result)
        self.assertEqual(result['version'], '99.0.0')
        self.assertEqual(result['release_notes'], 'New features!')
        self.assertIn('zipball_url', result)

    @patch('python.updater.urlopen')
    def test_network_error_returns_none(self, mock_urlopen):
        """Should return None on network error."""
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection refused")
        result = check_for_updates()
        self.assertIsNone(result)

    @patch('python.updater.urlopen')
    def test_404_returns_none(self, mock_urlopen):
        """Should return None when no releases exist (404)."""
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(
            RELEASES_URL, 404, "Not Found", {}, None
        )
        result = check_for_updates()
        self.assertIsNone(result)


class TestExtractAndReplace(unittest.TestCase):
    """Test the file extraction and replacement logic."""

    def _create_test_zip(self, zip_path: str, files: dict):
        """Create a test zip with the given files dict {path: content}."""
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for path, content in files.items():
                zf.writestr(f"owner-repo-abc123/{path}", content)

    def test_extract_replaces_source_files(self):
        """Should replace source files from the zip."""
        with tempfile.TemporaryDirectory() as app_dir:
            # Create existing file
            os.makedirs(os.path.join(app_dir, 'python'), exist_ok=True)
            with open(os.path.join(app_dir, 'python', 'version.py'), 'w') as f:
                f.write('__version__ = "1.0.0"')
            with open(os.path.join(app_dir, 'main.py'), 'w') as f:
                f.write('# old main')

            # Create zip with new files
            zip_path = os.path.join(app_dir, 'update.zip')
            self._create_test_zip(zip_path, {
                'main.py': '# new main',
                'python/version.py': '__version__ = "2.0.0"',
            })

            result = _extract_and_replace(zip_path, app_dir)
            self.assertTrue(result)

            with open(os.path.join(app_dir, 'main.py'), 'r') as f:
                self.assertEqual(f.read(), '# new main')
            with open(os.path.join(app_dir, 'python', 'version.py'), 'r') as f:
                self.assertIn('2.0.0', f.read())

    def test_extract_preserves_exports(self):
        """Should NOT overwrite the exports directory."""
        with tempfile.TemporaryDirectory() as app_dir:
            exports_dir = os.path.join(app_dir, 'exports')
            os.makedirs(exports_dir)
            with open(os.path.join(exports_dir, 'my_export.txt'), 'w') as f:
                f.write('precious data')

            zip_path = os.path.join(app_dir, 'update.zip')
            self._create_test_zip(zip_path, {
                'exports/new_file.txt': 'should not appear',
                'main.py': '# updated',
            })

            _extract_and_replace(zip_path, app_dir)

            # Original export preserved
            self.assertTrue(os.path.exists(os.path.join(exports_dir, 'my_export.txt')))
            with open(os.path.join(exports_dir, 'my_export.txt'), 'r') as f:
                self.assertEqual(f.read(), 'precious data')

    def test_extract_preserves_git_directory(self):
        """Should NOT overwrite .git directory."""
        with tempfile.TemporaryDirectory() as app_dir:
            git_dir = os.path.join(app_dir, '.git')
            os.makedirs(git_dir)
            with open(os.path.join(git_dir, 'HEAD'), 'w') as f:
                f.write('ref: refs/heads/main')

            zip_path = os.path.join(app_dir, 'update.zip')
            self._create_test_zip(zip_path, {
                'main.py': '# updated',
            })

            _extract_and_replace(zip_path, app_dir)

            self.assertTrue(os.path.exists(os.path.join(git_dir, 'HEAD')))

    def test_extract_preserves_session_files(self):
        """Should NOT overwrite pickleball_session_* files."""
        with tempfile.TemporaryDirectory() as app_dir:
            session_file = os.path.join(app_dir, 'pickleball_session_20260101_120000.txt')
            with open(session_file, 'w') as f:
                f.write('session data')

            zip_path = os.path.join(app_dir, 'update.zip')
            self._create_test_zip(zip_path, {
                'pickleball_session_20260101_120000.txt': 'overwritten',
                'main.py': '# updated',
            })

            _extract_and_replace(zip_path, app_dir)

            with open(session_file, 'r') as f:
                self.assertEqual(f.read(), 'session data')

    def test_extract_preserves_player_files(self):
        """Should NOT overwrite players.json."""
        with tempfile.TemporaryDirectory() as app_dir:
            players_file = os.path.join(app_dir, 'players.json')
            with open(players_file, 'w') as f:
                f.write('{"players": []}')

            zip_path = os.path.join(app_dir, 'update.zip')
            self._create_test_zip(zip_path, {
                'players.json': '{"players": ["new"]}',
                'main.py': '# updated',
            })

            _extract_and_replace(zip_path, app_dir)

            with open(players_file, 'r') as f:
                self.assertEqual(f.read(), '{"players": []}')


class TestUpdateScript(unittest.TestCase):
    """Test update script generation."""

    def test_creates_script_file(self):
        """Should create a script file."""
        with tempfile.TemporaryDirectory() as app_dir:
            zip_path = os.path.join(app_dir, 'update.zip')
            script = create_update_script(app_dir, zip_path, 99999)
            self.assertTrue(os.path.exists(script))
            os.unlink(script)

    def test_script_references_main_py(self):
        """Script should reference main.py for relaunch."""
        with tempfile.TemporaryDirectory() as app_dir:
            zip_path = os.path.join(app_dir, 'update.zip')
            script = create_update_script(app_dir, zip_path, 99999)
            with open(script, 'r') as f:
                content = f.read()
            self.assertIn('main.py', content)
            os.unlink(script)

    def test_script_waits_for_pid(self):
        """Script should contain logic to wait for the PID to exit."""
        with tempfile.TemporaryDirectory() as app_dir:
            zip_path = os.path.join(app_dir, 'update.zip')
            script = create_update_script(app_dir, zip_path, 12345)
            with open(script, 'r') as f:
                content = f.read()
            self.assertIn('12345', content)
            os.unlink(script)

    def test_script_platform_appropriate(self):
        """Script extension should match platform."""
        with tempfile.TemporaryDirectory() as app_dir:
            zip_path = os.path.join(app_dir, 'update.zip')
            script = create_update_script(app_dir, zip_path, 99999)
            if sys.platform == 'win32':
                self.assertTrue(script.endswith('.bat'))
            else:
                self.assertTrue(script.endswith('.sh'))
                self.assertTrue(os.access(script, os.X_OK))
            os.unlink(script)


class TestAppDirectory(unittest.TestCase):
    """Test app directory detection."""

    def test_app_directory_contains_main_py(self):
        """App directory should contain main.py."""
        app_dir = get_app_directory()
        self.assertTrue(os.path.exists(os.path.join(app_dir, 'main.py')),
                        f"main.py not found in {app_dir}")

    def test_app_directory_contains_python_dir(self):
        """App directory should contain python/ subdirectory."""
        app_dir = get_app_directory()
        self.assertTrue(os.path.isdir(os.path.join(app_dir, 'python')))


class TestGUIVersionDisplay(unittest.TestCase):
    """Test that version is embedded in GUI code."""

    def test_main_window_shows_version(self):
        """MainWindow title should include version."""
        import python.gui as gui_module
        with open(gui_module.__file__, 'r') as f:
            content = f.read()
        self.assertIn('APP_VERSION', content)
        self.assertIn('Pickleball Session Manager v{APP_VERSION}', content)

    def test_session_window_shows_version(self):
        """SessionWindow should display version."""
        import python.gui as gui_module
        with open(gui_module.__file__, 'r') as f:
            content = f.read()
        # Check version label exists in session window setup
        self.assertIn('version_label = QLabel(f"v{APP_VERSION}")', content)

    def test_check_for_updates_button_exists(self):
        """MainWindow should have a Check for Updates button."""
        import python.gui as gui_module
        with open(gui_module.__file__, 'r') as f:
            content = f.read()
        self.assertIn('Check for Updates', content)
        self.assertIn('check_for_updates', content)

    def test_version_imported_in_gui(self):
        """GUI should import APP_VERSION from version module."""
        import python.gui as gui_module
        with open(gui_module.__file__, 'r') as f:
            content = f.read()
        self.assertIn('from python.version import __version__ as APP_VERSION', content)


if __name__ == '__main__':
    unittest.main()
