"""Tests for session setup defaults and shortcut creation."""

import sys
import os
import struct
import tempfile
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCreateShortcut(unittest.TestCase):
    """Test the desktop shortcut creation script."""

    def test_ico_generation_valid_file(self):
        """Test that ICO file is generated with valid header and multiple sizes."""
        from create_shortcut import create_tennis_ball_ico
        ico_path = os.path.join(tempfile.gettempdir(), 'test_tennis_ball.ico')
        try:
            create_tennis_ball_ico(ico_path)
            self.assertTrue(os.path.exists(ico_path))
            size = os.path.getsize(ico_path)
            # Multi-size ICO should be substantially larger than single 32x32
            self.assertGreater(size, 10000)
        finally:
            if os.path.exists(ico_path):
                os.unlink(ico_path)

    def test_ico_header_format(self):
        """Test that ICO header has correct format with multiple images."""
        from create_shortcut import create_tennis_ball_ico
        ico_path = os.path.join(tempfile.gettempdir(), 'test_tennis_ball2.ico')
        try:
            create_tennis_ball_ico(ico_path)
            with open(ico_path, 'rb') as f:
                data = f.read(6)
            reserved, ico_type, count = struct.unpack('<HHH', data)
            self.assertEqual(reserved, 0)
            self.assertEqual(ico_type, 1)  # ICO type
            self.assertEqual(count, 5)     # 5 sizes: 16, 32, 48, 64, 256
        finally:
            if os.path.exists(ico_path):
                os.unlink(ico_path)

    def test_ico_directory_entry(self):
        """Test ICO contains all expected sizes (16, 32, 48, 64, 256)."""
        from create_shortcut import create_tennis_ball_ico
        ico_path = os.path.join(tempfile.gettempdir(), 'test_tennis_ball3.ico')
        try:
            create_tennis_ball_ico(ico_path)
            with open(ico_path, 'rb') as f:
                header = f.read(6)
                _, _, count = struct.unpack('<HHH', header)
                sizes_found = []
                for _ in range(count):
                    dir_data = f.read(16)
                    w, h, palette, reserved, planes, bpp = struct.unpack('<BBBBHH', dir_data[:8])
                    actual_w = 256 if w == 0 else w
                    sizes_found.append(actual_w)
                    self.assertEqual(bpp, 32)
            self.assertEqual(sorted(sizes_found), [16, 32, 48, 64, 256])
        finally:
            if os.path.exists(ico_path):
                os.unlink(ico_path)

    def test_get_desktop_path_returns_string(self):
        """Test that get_desktop_path returns a string path."""
        from create_shortcut import get_desktop_path
        path = get_desktop_path()
        self.assertIsInstance(path, str)
        self.assertTrue(len(path) > 0)


class TestSessionSetupDefaults(unittest.TestCase):
    """Test session setup dialog defaults without launching GUI."""

    def test_default_game_mode_is_continuous_rr(self):
        """Test that the first game mode in the list is Continuous Round Robin."""
        # Verify by checking the source code directly
        import python.gui as gui_module
        source_file = gui_module.__file__
        with open(source_file, 'r') as f:
            content = f.read()

        # Find the addItems line for mode_combo
        import re
        match = re.search(r'self\.mode_combo\.addItems\(\[(.*?)\]\)', content)
        self.assertIsNotNone(match, "Could not find mode_combo.addItems in gui.py")
        items_str = match.group(1)
        # First item should be "Continuous Round Robin"
        first_item = items_str.split(',')[0].strip().strip('"').strip("'")
        self.assertEqual(first_item, "Continuous Round Robin",
                         f"First game mode should be 'Continuous Round Robin', got '{first_item}'")

    def test_competitive_variety_forces_doubles(self):
        """Test that Competitive Variety mode forces Doubles session type."""
        import python.gui as gui_module
        source_file = gui_module.__file__
        with open(source_file, 'r') as f:
            content = f.read()

        # Verify the code contains the Competitive Variety -> Doubles restriction
        self.assertIn('is_competitive_variety', content)
        # Check that when is_competitive_variety is true, we add only "Doubles"
        # Find the block
        cv_block_start = content.find('elif is_competitive_variety:')
        self.assertGreater(cv_block_start, 0, "Could not find 'elif is_competitive_variety:' block")
        # Get the next few lines
        cv_block = content[cv_block_start:cv_block_start + 200]
        self.assertIn('self.type_combo.clear()', cv_block)
        self.assertIn('self.type_combo.addItem("Doubles")', cv_block)
        # Should NOT add Singles for competitive variety
        self.assertNotIn('addItem("Singles")', cv_block)

    def test_continuous_rr_before_strict_in_mode_list(self):
        """Test that Continuous Round Robin appears before Strict in the mode list."""
        import python.gui as gui_module
        source_file = gui_module.__file__
        with open(source_file, 'r') as f:
            content = f.read()

        import re
        match = re.search(r'self\.mode_combo\.addItems\(\[(.*?)\]\)', content)
        self.assertIsNotNone(match)
        items_str = match.group(1)
        items = [item.strip().strip('"').strip("'") for item in items_str.split(',')]
        crr_idx = items.index("Continuous Round Robin")
        scrr_idx = items.index("Strict Continuous Round Robin")
        self.assertLess(crr_idx, scrr_idx,
                        "Continuous Round Robin should appear before Strict Continuous Round Robin")

    def test_pooled_rr_still_forces_singles(self):
        """Verify that Pooled RR still forces Singles (existing behavior preserved)."""
        import python.gui as gui_module
        source_file = gui_module.__file__
        with open(source_file, 'r') as f:
            content = f.read()

        # Find the pooled RR block
        pooled_block_start = content.find('if is_pooled_rr:')
        self.assertGreater(pooled_block_start, 0)
        pooled_block = content[pooled_block_start:pooled_block_start + 200]
        self.assertIn('self.type_combo.clear()', pooled_block)
        self.assertIn('self.type_combo.addItem("Singles")', pooled_block)

    def test_other_modes_restore_both_options(self):
        """Verify that non-restricted modes restore both Doubles and Singles."""
        import python.gui as gui_module
        source_file = gui_module.__file__
        with open(source_file, 'r') as f:
            content = f.read()

        # The else block should restore both options
        restore_start = content.find('# Restore both options if not already present')
        self.assertGreater(restore_start, 0)
        restore_block = content[restore_start:restore_start + 200]
        self.assertIn('self.type_combo.addItems(["Doubles", "Singles"])', restore_block)


class TestShortcutScriptStructure(unittest.TestCase):
    """Test that the shortcut script has proper cross-platform support."""

    def test_script_exists(self):
        """Test that create_shortcut.py exists in project root."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(project_root, 'create_shortcut.py')
        self.assertTrue(os.path.exists(script_path))

    def test_script_is_importable(self):
        """Test that the shortcut script can be imported without errors."""
        import create_shortcut
        self.assertTrue(hasattr(create_shortcut, 'main'))
        self.assertTrue(hasattr(create_shortcut, 'create_tennis_ball_ico'))
        self.assertTrue(hasattr(create_shortcut, 'get_desktop_path'))

    def test_script_has_platform_functions(self):
        """Test that the script has functions for all supported platforms."""
        import create_shortcut
        self.assertTrue(hasattr(create_shortcut, 'create_windows_shortcut'))
        self.assertTrue(hasattr(create_shortcut, 'create_macos_shortcut'))
        self.assertTrue(hasattr(create_shortcut, 'create_linux_shortcut'))

    def test_linux_shortcut_creates_desktop_file(self):
        """Test that Linux shortcut creates a valid .desktop file."""
        from create_shortcut import create_linux_shortcut
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            result = create_linux_shortcut(app_dir, tmpdir)
            self.assertTrue(result)
            desktop_file = os.path.join(tmpdir, 'pickleball-session-manager.desktop')
            self.assertTrue(os.path.exists(desktop_file))
            with open(desktop_file, 'r') as f:
                content = f.read()
            self.assertIn('[Desktop Entry]', content)
            self.assertIn('Type=Application', content)
            self.assertIn('Pickleball Session Manager', content)
            self.assertIn('main.py', content)

    def test_macos_shortcut_creates_command_file(self):
        """Test that macOS shortcut creates a valid .command file."""
        from create_shortcut import create_macos_shortcut
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            result = create_macos_shortcut(app_dir, tmpdir)
            self.assertTrue(result)
            command_file = os.path.join(tmpdir, 'Pickleball Session Manager.command')
            self.assertTrue(os.path.exists(command_file))
            with open(command_file, 'r') as f:
                content = f.read()
            self.assertIn('#!/bin/bash', content)
            self.assertIn('main.py', content)
            # Check executable permission
            self.assertTrue(os.access(command_file, os.X_OK))


if __name__ == '__main__':
    unittest.main()
