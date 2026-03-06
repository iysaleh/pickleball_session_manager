"""Tests for the per-session logging system."""

import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from python.session_logger import SessionLogger, initialize_session_logger, get_session_logger, session_log
import python.session_logger as logger_module


class TestSessionLoggerCreation(unittest.TestCase):
    """Test that the logger creates files and writes entries correctly."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
    
    def tearDown(self):
        # Reset global state
        logger_module._session_logger = None
        # Cleanup temp files
        for f in os.listdir(self.tmpdir):
            try:
                os.remove(os.path.join(self.tmpdir, f))
            except Exception:
                pass
        try:
            os.rmdir(self.tmpdir)
        except Exception:
            pass
    
    def test_file_created_on_init(self):
        """Logger should create a log file when initialized."""
        logger = SessionLogger(log_dir=self.tmpdir)
        self.assertTrue(os.path.exists(logger.filename))
        self.assertTrue(logger.filename.startswith(self.tmpdir))
        self.assertIn('pickleball_log_', logger.filename)
        logger.close()
    
    def test_filename_format(self):
        """Log filename should follow pickleball_log_YYYYMMDD_HHMMSS.log pattern."""
        logger = SessionLogger(log_dir=self.tmpdir)
        basename = os.path.basename(logger.filename)
        self.assertTrue(basename.startswith('pickleball_log_'))
        self.assertTrue(basename.endswith('.log'))
        # Should have a timestamp in between
        parts = basename.replace('pickleball_log_', '').replace('.log', '')
        # Format: YYYYMMDD_HHMMSS
        self.assertEqual(len(parts), 15)  # 8 + 1 + 6
        logger.close()
    
    def test_write_entry(self):
        """Logger should write entries to the file."""
        logger = SessionLogger(log_dir=self.tmpdir)
        logger.log("Test message")
        
        with open(logger.filename, 'r') as f:
            content = f.read()
        
        self.assertIn('Test message', content)
        logger.close()
    
    def test_immediate_flush(self):
        """Log entries should be immediately readable (flushed to disk)."""
        logger = SessionLogger(log_dir=self.tmpdir)
        logger.log("Flush test")
        
        # Should be readable immediately without closing the logger
        with open(logger.filename, 'r') as f:
            content = f.read()
        
        self.assertIn('Flush test', content)
        logger.close()
    
    def test_timestamp_format(self):
        """Log entries should have [YYYY-MM-DD HH:MM:SS] timestamp prefix."""
        logger = SessionLogger(log_dir=self.tmpdir)
        logger.log("Timestamp test")
        
        with open(logger.filename, 'r') as f:
            line = f.readline().strip()
        
        # Should start with [
        self.assertTrue(line.startswith('['))
        # Should have the timestamp pattern
        self.assertRegex(line, r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]')
        logger.close()
    
    def test_multiple_entries(self):
        """Multiple log entries should all appear in the file."""
        logger = SessionLogger(log_dir=self.tmpdir)
        logger.log("Entry 1")
        logger.log("Entry 2")
        logger.log("Entry 3")
        
        with open(logger.filename, 'r') as f:
            content = f.read()
        
        self.assertIn('Entry 1', content)
        self.assertIn('Entry 2', content)
        self.assertIn('Entry 3', content)
        
        lines = [l for l in content.strip().split('\n') if l.strip()]
        self.assertEqual(len(lines), 3)
        logger.close()


class TestSemanticLogMethods(unittest.TestCase):
    """Test the semantic log methods produce correct output."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.logger = SessionLogger(log_dir=self.tmpdir)
    
    def tearDown(self):
        self.logger.close()
        logger_module._session_logger = None
        for f in os.listdir(self.tmpdir):
            try:
                os.remove(os.path.join(self.tmpdir, f))
            except Exception:
                pass
        try:
            os.rmdir(self.tmpdir)
        except Exception:
            pass
    
    def _read_log(self):
        with open(self.logger.filename, 'r') as f:
            return f.read()
    
    def test_log_session_started(self):
        self.logger.log_session_started('competitive-variety', 16, 4, ['Alice', 'Bob'])
        content = self._read_log()
        self.assertIn('SESSION STARTED', content)
        self.assertIn('Mode: competitive-variety', content)
        self.assertIn('Players: 16', content)
        self.assertIn('Courts: 4', content)
        self.assertIn('PLAYER ROSTER', content)
        self.assertIn('Alice, Bob', content)
    
    def test_log_session_ended(self):
        self.logger.log_session_ended()
        content = self._read_log()
        self.assertIn('SESSION ENDED', content)
    
    def test_log_match_scheduled(self):
        self.logger.log_match_scheduled('m1', 2, ['Alice', 'Bob'], ['Charlie', 'Diana'])
        content = self._read_log()
        self.assertIn('MATCH SCHEDULED', content)
        self.assertIn('Match m1', content)
        self.assertIn('Court 2', content)
        self.assertIn('Alice, Bob vs Charlie, Diana', content)
    
    def test_log_match_queued(self):
        self.logger.log_match_queued('m2', ['Eve'], ['Frank'])
        content = self._read_log()
        self.assertIn('MATCH QUEUED', content)
        self.assertIn('Eve vs Frank', content)
    
    def test_log_score_input(self):
        self.logger.log_score_input('m1', 11, 7, ['Alice', 'Bob'], ['Charlie', 'Diana'])
        content = self._read_log()
        self.assertIn('SCORE INPUT', content)
        self.assertIn('Alice, Bob (11) vs Charlie, Diana (7)', content)
    
    def test_log_match_completed_team1_wins(self):
        self.logger.log_match_completed('m1', ['Alice', 'Bob'], ['Charlie', 'Diana'], 11, 7)
        content = self._read_log()
        self.assertIn('MATCH COMPLETED', content)
        self.assertIn('Alice, Bob (11) def. Charlie, Diana (7)', content)
    
    def test_log_match_completed_team2_wins(self):
        self.logger.log_match_completed('m1', ['Alice', 'Bob'], ['Charlie', 'Diana'], 5, 11)
        content = self._read_log()
        self.assertIn('Charlie, Diana (11) def. Alice, Bob (5)', content)
    
    def test_log_match_forfeited(self):
        self.logger.log_match_forfeited('m3', ['Alice'], ['Bob'])
        content = self._read_log()
        self.assertIn('MATCH FORFEITED', content)
    
    def test_log_manual_match_created(self):
        self.logger.log_manual_match_created(3, ['A', 'B'], ['C', 'D'])
        content = self._read_log()
        self.assertIn('MANUAL MATCH CREATED', content)
        self.assertIn('Court 3', content)
    
    def test_log_court_slide(self):
        self.logger.log_court_slide('m5', 3, 1)
        content = self._read_log()
        self.assertIn('COURT SLIDE', content)
        self.assertIn('Court 3 to Court 1', content)
    
    def test_log_match_score_edited(self):
        self.logger.log_match_score_edited('m1', ['Alice', 'Bob'], ['Charlie', 'Diana'], 11, 7, 11, 9)
        content = self._read_log()
        self.assertIn('MATCH SCORE EDITED', content)
        self.assertIn('Alice, Bob vs Charlie, Diana', content)
        self.assertIn('11-7', content)
        self.assertIn('11-9', content)
    
    def test_log_player_added(self):
        self.logger.log_player_added('NewPlayer')
        content = self._read_log()
        self.assertIn('PLAYER ADDED', content)
        self.assertIn('NewPlayer', content)
    
    def test_log_player_removed(self):
        self.logger.log_player_removed('OldPlayer')
        content = self._read_log()
        self.assertIn('PLAYER REMOVED', content)
        self.assertIn('OldPlayer', content)
    
    def test_log_first_bye_changed(self):
        self.logger.log_first_bye_changed(['Alice', 'Bob'])
        content = self._read_log()
        self.assertIn('FIRST BYE CHANGED', content)
        self.assertIn('Alice, Bob', content)
    
    def test_log_first_bye_changed_empty(self):
        self.logger.log_first_bye_changed([])
        content = self._read_log()
        self.assertIn('(none)', content)
    
    def test_log_slider_changed(self):
        self.logger.log_slider_changed('Variety', 3, 5)
        content = self._read_log()
        self.assertIn('SLIDER CHANGED', content)
        self.assertIn('Variety: 3', content)
    
    def test_log_court_ordering_changed(self):
        self.logger.log_court_ordering_changed([3, 1, 2, 4])
        content = self._read_log()
        self.assertIn('COURT ORDERING CHANGED', content)
        self.assertIn('[3, 1, 2, 4]', content)
    
    def test_log_locked_team(self):
        self.logger.log_locked_team('Alice', 'Bob')
        content = self._read_log()
        self.assertIn('LOCKED TEAM', content)
        self.assertIn('Alice + Bob', content)
    
    def test_log_banned_pair(self):
        self.logger.log_banned_pair('Charlie', 'Diana')
        content = self._read_log()
        self.assertIn('BANNED PAIR', content)
        self.assertIn('Charlie + Diana', content)
    
    def test_log_round_advanced(self):
        self.logger.log_round_advanced(3, 'King of Court')
        content = self._read_log()
        self.assertIn('ROUND ADVANCED', content)
        self.assertIn('King of Court Round 3', content)
    
    def test_log_schedule_generated(self):
        self.logger.log_schedule_generated(24)
        content = self._read_log()
        self.assertIn('SCHEDULE GENERATED', content)
        self.assertIn('24 matches', content)
    
    def test_log_export(self):
        self.logger.log_export('pickleball_session_20260306.log')
        content = self._read_log()
        self.assertIn('EXPORT', content)
        self.assertIn('pickleball_session_20260306.log', content)


class TestGlobalAccessor(unittest.TestCase):
    """Test the global accessor pattern (initialize / get)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        logger_module._session_logger = None
    
    def tearDown(self):
        if logger_module._session_logger:
            try:
                logger_module._session_logger.close()
            except Exception:
                pass
        logger_module._session_logger = None
        for f in os.listdir(self.tmpdir):
            try:
                os.remove(os.path.join(self.tmpdir, f))
            except Exception:
                pass
        try:
            os.rmdir(self.tmpdir)
        except Exception:
            pass
    
    def test_get_returns_none_when_not_initialized(self):
        """get_session_logger() should return None before initialization."""
        self.assertIsNone(get_session_logger())
    
    def test_initialize_returns_logger(self):
        """initialize_session_logger() should return a SessionLogger instance."""
        logger = initialize_session_logger(log_dir=self.tmpdir)
        self.assertIsInstance(logger, SessionLogger)
    
    def test_get_returns_logger_after_init(self):
        """get_session_logger() should return the initialized logger."""
        init_logger = initialize_session_logger(log_dir=self.tmpdir)
        get_logger = get_session_logger()
        self.assertIs(init_logger, get_logger)
    
    def test_session_log_noop_when_not_initialized(self):
        """session_log() should not crash when logger is not initialized."""
        # Should not raise any exception
        session_log("This should be a no-op")
    
    def test_session_log_writes_when_initialized(self):
        """session_log() should write when logger is initialized."""
        logger = initialize_session_logger(log_dir=self.tmpdir)
        session_log("Convenience test")
        
        with open(logger.filename, 'r') as f:
            content = f.read()
        
        self.assertIn('Convenience test', content)
    
    def test_reinitialize_closes_previous(self):
        """Reinitializing should close the previous logger."""
        logger1 = initialize_session_logger(log_dir=self.tmpdir)
        file1 = logger1.filename
        
        # Small delay to ensure different timestamp
        time.sleep(1.1)
        
        logger2 = initialize_session_logger(log_dir=self.tmpdir)
        file2 = logger2.filename
        
        # Should be different files
        self.assertNotEqual(file1, file2)
        # Both should exist
        self.assertTrue(os.path.exists(file1))
        self.assertTrue(os.path.exists(file2))
        # Current global should be logger2
        self.assertIs(get_session_logger(), logger2)


class TestSessionIntegration(unittest.TestCase):
    """Test that logger integrates with session creation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        logger_module._session_logger = None
    
    def tearDown(self):
        if logger_module._session_logger:
            try:
                logger_module._session_logger.close()
            except Exception:
                pass
        logger_module._session_logger = None
        # Cleanup log files from cwd too
        for f in os.listdir('.'):
            if f.startswith('pickleball_log_') and f.endswith('.log'):
                try:
                    os.remove(f)
                except Exception:
                    pass
        for f in os.listdir(self.tmpdir):
            try:
                os.remove(os.path.join(self.tmpdir, f))
            except Exception:
                pass
        try:
            os.rmdir(self.tmpdir)
        except Exception:
            pass
    
    def test_session_creation_initializes_logger(self):
        """Creating a session should initialize the session logger."""
        from python.time_manager import initialize_time_manager
        from python.session import create_session
        from python.pickleball_types import SessionConfig, Player
        
        initialize_time_manager()
        
        players = [Player(name=f'Player{i}', id=f'p{i}') for i in range(8)]
        config = SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=players,
            courts=2
        )
        session = create_session(config)
        
        logger = get_session_logger()
        self.assertIsNotNone(logger)
        self.assertTrue(os.path.exists(logger.filename))
        
        with open(logger.filename, 'r') as f:
            content = f.read()
        
        self.assertIn('SESSION STARTED', content)
        self.assertIn('competitive-variety', content)
        self.assertIn('Players: 8', content)
        self.assertIn('Courts: 2', content)


if __name__ == '__main__':
    unittest.main()
