"""Tests for export directory, auto-export tracking, and sleep inhibitor features."""

import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGetExportsDirectory(unittest.TestCase):
    """Tests for get_exports_directory() helper function."""
    
    def test_creates_exports_subdirectory(self):
        """Exports directory should be created inside cwd."""
        from python.gui import get_exports_directory
        exports_dir = get_exports_directory()
        self.assertTrue(os.path.isdir(exports_dir))
        self.assertTrue(exports_dir.endswith("exports"))
    
    def test_fallback_to_cwd_on_permission_error(self):
        """If exports dir can't be created, falls back to cwd."""
        from python.gui import get_exports_directory
        with patch('os.makedirs', side_effect=OSError("Permission denied")):
            result = get_exports_directory()
            self.assertEqual(result, os.getcwd())
    
    def test_idempotent_calls(self):
        """Calling get_exports_directory multiple times should work fine."""
        from python.gui import get_exports_directory
        d1 = get_exports_directory()
        d2 = get_exports_directory()
        self.assertEqual(d1, d2)


class TestGetLatestExportFile(unittest.TestCase):
    """Tests for get_latest_export_file() helper function."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
    
    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_returns_none_when_no_exports(self):
        """Should return None if no export files exist."""
        os.chdir(self.test_dir)
        os.makedirs(os.path.join(self.test_dir, "exports"), exist_ok=True)
        from python.gui import get_latest_export_file
        result = get_latest_export_file()
        self.assertIsNone(result)
    
    def test_returns_latest_file_from_exports_dir(self):
        """Should return the most recent file from exports/ dir."""
        os.chdir(self.test_dir)
        exports = os.path.join(self.test_dir, "exports")
        os.makedirs(exports, exist_ok=True)
        
        # Create some export files
        for ts in ["20260101_100000", "20260102_100000", "20260103_100000"]:
            filepath = os.path.join(exports, f"pickleball_session_{ts}.txt")
            with open(filepath, 'w') as f:
                f.write("test")
        
        from python.gui import get_latest_export_file
        result = get_latest_export_file()
        self.assertIsNotNone(result)
        self.assertIn("20260103_100000", result)
    
    def test_falls_back_to_cwd_legacy_exports(self):
        """Should find legacy exports in cwd if exports/ dir has none."""
        os.chdir(self.test_dir)
        exports = os.path.join(self.test_dir, "exports")
        os.makedirs(exports, exist_ok=True)
        
        # Create a legacy export in cwd
        legacy = os.path.join(self.test_dir, "pickleball_session_20260101_100000.txt")
        with open(legacy, 'w') as f:
            f.write("legacy export")
        
        from python.gui import get_latest_export_file
        result = get_latest_export_file()
        self.assertIsNotNone(result)
        self.assertIn("20260101_100000", result)


class TestSessionExportedField(unittest.TestCase):
    """Tests for session_exported field on Session dataclass."""
    
    def test_session_exported_default_false(self):
        """session_exported should default to False."""
        from python.pickleball_types import Session, SessionConfig, Player
        config = SessionConfig(
            players=[Player(id="p1", name="Player 1")],
            courts=1,
            mode="competitive-variety",
            session_type="doubles"
        )
        session = Session(id="test-session", config=config)
        self.assertFalse(session.session_exported)
    
    def test_session_exported_can_be_set_true(self):
        """session_exported should be settable."""
        from python.pickleball_types import Session, SessionConfig, Player
        config = SessionConfig(
            players=[Player(id="p1", name="Player 1")],
            courts=1,
            mode="competitive-variety",
            session_type="doubles"
        )
        session = Session(id="test-session", config=config)
        session.session_exported = True
        self.assertTrue(session.session_exported)


class TestSessionExportedPersistence(unittest.TestCase):
    """Tests for session_exported serialization/deserialization."""
    
    def _make_session(self, exported=False):
        from python.pickleball_types import Session, SessionConfig, Player
        config = SessionConfig(
            players=[Player(id="p1", name="Player 1")],
            courts=1,
            mode="competitive-variety",
            session_type="doubles"
        )
        session = Session(id="test-session", config=config)
        session.session_exported = exported
        return session
    
    def test_serialize_session_exported_false(self):
        """Serialized session should include session_exported=False."""
        from python.session_persistence import serialize_session
        session = self._make_session(exported=False)
        data = serialize_session(session)
        self.assertIn('session_exported', data)
        self.assertFalse(data['session_exported'])
    
    def test_serialize_session_exported_true(self):
        """Serialized session should include session_exported=True."""
        from python.session_persistence import serialize_session
        session = self._make_session(exported=True)
        data = serialize_session(session)
        self.assertTrue(data['session_exported'])
    
    def test_deserialize_session_exported(self):
        """Deserialized session should restore session_exported."""
        from python.session_persistence import serialize_session, deserialize_session
        session = self._make_session(exported=True)
        data = serialize_session(session)
        restored = deserialize_session(data)
        self.assertTrue(restored.session_exported)
    
    def test_deserialize_missing_session_exported_defaults_false(self):
        """Old session data without session_exported should default to False."""
        from python.session_persistence import serialize_session, deserialize_session
        session = self._make_session(exported=False)
        data = serialize_session(session)
        # Remove the field to simulate old data
        data.pop('session_exported', None)
        restored = deserialize_session(data)
        self.assertFalse(restored.session_exported)


class TestSleepInhibitor(unittest.TestCase):
    """Tests for the sleep_inhibitor module."""
    
    def test_singleton_pattern(self):
        """get_sleep_inhibitor should return the same instance."""
        from python.sleep_inhibitor import get_sleep_inhibitor
        a = get_sleep_inhibitor()
        b = get_sleep_inhibitor()
        self.assertIs(a, b)
    
    def test_enable_disable_idempotent(self):
        """Enable and disable should be safe to call multiple times."""
        from python.sleep_inhibitor import get_sleep_inhibitor
        inhibitor = get_sleep_inhibitor()
        # Should not raise
        inhibitor.enable()
        inhibitor.enable()
        self.assertTrue(inhibitor.is_active)
        inhibitor.disable()
        inhibitor.disable()
        self.assertFalse(inhibitor.is_active)
    
    def test_cleanup(self):
        """cleanup() should disable the inhibitor."""
        from python.sleep_inhibitor import get_sleep_inhibitor
        inhibitor = get_sleep_inhibitor()
        inhibitor.enable()
        inhibitor.cleanup()
        self.assertFalse(inhibitor.is_active)
    
    def test_is_active_property(self):
        """is_active should reflect current state."""
        from python.sleep_inhibitor import get_sleep_inhibitor
        inhibitor = get_sleep_inhibitor()
        inhibitor.disable()
        self.assertFalse(inhibitor.is_active)
        inhibitor.enable()
        self.assertTrue(inhibitor.is_active)
        inhibitor.disable()
        self.assertFalse(inhibitor.is_active)


class TestOpenFileHelpers(unittest.TestCase):
    """Tests for open_file_with_default_app and open_directory_in_explorer."""
    
    @patch('subprocess.Popen')
    def test_open_file_linux(self, mock_popen):
        """On Linux, should call xdg-open."""
        from python.gui import open_file_with_default_app
        with patch('sys.platform', 'linux'):
            result = open_file_with_default_app('/tmp/test.txt')
            self.assertTrue(result)
            mock_popen.assert_called_once_with(['xdg-open', '/tmp/test.txt'])
    
    @patch('subprocess.Popen')
    def test_open_file_darwin(self, mock_popen):
        """On macOS, should call open."""
        from python.gui import open_file_with_default_app
        with patch('sys.platform', 'darwin'):
            result = open_file_with_default_app('/tmp/test.txt')
            self.assertTrue(result)
            mock_popen.assert_called_once_with(['open', '/tmp/test.txt'])
    
    @patch('subprocess.Popen')
    def test_open_directory_linux(self, mock_popen):
        """On Linux, should call xdg-open for directories."""
        from python.gui import open_directory_in_explorer
        with patch('sys.platform', 'linux'):
            result = open_directory_in_explorer('/tmp')
            self.assertTrue(result)
            mock_popen.assert_called_once_with(['xdg-open', '/tmp'])
    
    def test_open_file_handles_exception(self):
        """Should return False and not crash on error."""
        from python.gui import open_file_with_default_app
        with patch('subprocess.Popen', side_effect=Exception("not found")):
            with patch('sys.platform', 'linux'):
                result = open_file_with_default_app('/nonexistent/file.txt')
                self.assertFalse(result)


class TestExportToExportsDirectory(unittest.TestCase):
    """Integration test: export files should go into exports/ subdir."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_export_dir_gets_created(self):
        """The exports/ directory should be automatically created."""
        from python.gui import get_exports_directory
        exports_dir = get_exports_directory()
        self.assertTrue(os.path.isdir(exports_dir))
        self.assertEqual(os.path.basename(exports_dir), "exports")
        self.assertEqual(os.path.dirname(exports_dir), self.test_dir)


if __name__ == '__main__':
    unittest.main()
