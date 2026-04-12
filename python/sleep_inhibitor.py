"""
Cross-platform sleep/screen inhibitor for keeping the system awake.

Supports:
- Windows: SetThreadExecutionState API
- macOS: caffeinate subprocess
- Linux: D-Bus org.freedesktop.ScreenSaver / org.gnome.SessionManager, 
         fallback to xdg-screensaver and systemd-inhibit
"""

import sys
import subprocess
import os
import threading


class SleepInhibitor:
    """Prevents the system from sleeping or dimming the screen."""
    
    def __init__(self):
        self._active = False
        self._platform = sys.platform
        self._process = None  # For macOS caffeinate / Linux systemd-inhibit
        self._dbus_cookie = None  # For Linux D-Bus inhibit
        self._lock = threading.Lock()
    
    @property
    def is_active(self) -> bool:
        return self._active
    
    def enable(self) -> bool:
        """Enable sleep prevention. Returns True if successful."""
        with self._lock:
            if self._active:
                return True
            
            try:
                if self._platform == 'win32':
                    success = self._enable_windows()
                elif self._platform == 'darwin':
                    success = self._enable_macos()
                else:
                    success = self._enable_linux()
                
                if success:
                    self._active = True
                return success
            except Exception as e:
                print(f"Sleep inhibitor enable error: {e}")
                return False
    
    def disable(self) -> bool:
        """Disable sleep prevention. Returns True if successful."""
        with self._lock:
            if not self._active:
                return True
            
            try:
                if self._platform == 'win32':
                    success = self._disable_windows()
                elif self._platform == 'darwin':
                    success = self._disable_macos()
                else:
                    success = self._disable_linux()
                
                if success:
                    self._active = False
                return success
            except Exception as e:
                print(f"Sleep inhibitor disable error: {e}")
                return False
    
    def cleanup(self):
        """Ensure sleep prevention is disabled. Call on application exit."""
        self.disable()
    
    # --- Windows ---
    
    def _enable_windows(self) -> bool:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002
        result = ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
        return result != 0
    
    def _disable_windows(self) -> bool:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        result = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        return result != 0
    
    # --- macOS ---
    
    def _enable_macos(self) -> bool:
        # caffeinate -d prevents display sleep, -i prevents idle sleep
        self._process = subprocess.Popen(
            ['caffeinate', '-d', '-i'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return self._process.poll() is None
    
    def _disable_macos(self) -> bool:
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        return True
    
    # --- Linux ---
    
    def _enable_linux(self) -> bool:
        # Try D-Bus first (works with GNOME, KDE, etc.)
        if self._enable_linux_dbus():
            return True
        # Fallback: xdg-screensaver suspend (needs a window ID, less reliable)
        # Fallback: systemd-inhibit subprocess
        return self._enable_linux_systemd_inhibit()
    
    def _disable_linux(self) -> bool:
        if self._dbus_cookie is not None:
            return self._disable_linux_dbus()
        if self._process is not None:
            return self._disable_linux_process()
        return True
    
    def _enable_linux_dbus(self) -> bool:
        try:
            import dbus
            bus = dbus.SessionBus()
            
            # Try org.freedesktop.ScreenSaver (works on KDE and many DEs)
            for service in ['org.freedesktop.ScreenSaver', 'org.gnome.ScreenSaver']:
                try:
                    proxy = bus.get_object(service, f'/{service.replace(".", "/")}')
                    iface = dbus.Interface(proxy, service)
                    self._dbus_cookie = iface.Inhibit(
                        'Pickleball Session Manager',
                        'Active session in progress - preventing sleep'
                    )
                    self._dbus_service = service
                    return True
                except dbus.exceptions.DBusException:
                    continue
            
            return False
        except ImportError:
            return False
        except Exception:
            return False
    
    def _disable_linux_dbus(self) -> bool:
        try:
            import dbus
            bus = dbus.SessionBus()
            proxy = bus.get_object(
                self._dbus_service,
                f'/{self._dbus_service.replace(".", "/")}'
            )
            iface = dbus.Interface(proxy, self._dbus_service)
            iface.UnInhibit(self._dbus_cookie)
            self._dbus_cookie = None
            self._dbus_service = None
            return True
        except Exception:
            self._dbus_cookie = None
            return True
    
    def _enable_linux_systemd_inhibit(self) -> bool:
        try:
            # systemd-inhibit keeps running as long as the child process runs
            # We use 'sleep infinity' as the child process
            self._process = subprocess.Popen(
                [
                    'systemd-inhibit',
                    '--what=idle:sleep',
                    '--who=Pickleball Session Manager',
                    '--why=Active session in progress',
                    '--mode=block',
                    'sleep', 'infinity'
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return self._process.poll() is None
        except FileNotFoundError:
            return False
        except Exception:
            return False
    
    def _disable_linux_process(self) -> bool:
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        return True


# Module-level singleton
_inhibitor = None


def get_sleep_inhibitor() -> SleepInhibitor:
    """Get the global SleepInhibitor singleton."""
    global _inhibitor
    if _inhibitor is None:
        _inhibitor = SleepInhibitor()
    return _inhibitor
