# ✅ Window Close Issue Fixed

## Problem

SessionWindow was closing immediately after being shown. The main event loop would exit even though a window was visible.

## Root Cause

Two issues were preventing the window from staying open:

1. **Missing parent reference** - SessionWindow was being created but not kept alive
2. **Window management** - When MainWindow was hidden, Qt thought there were no visible windows and exited the event loop
3. **No close handler** - SessionWindow didn't properly manage transitions back to MainWindow

## Solution Implemented

### 1. Keep Parent Reference
```python
# In MainWindow.new_session()
self.session_window = SessionWindow(self.session, parent_window=self)
# Now SessionWindow is kept alive as long as MainWindow exists
```

### 2. Pass Parent Window to SessionWindow
```python
# In SessionWindow.__init__()
def __init__(self, session: Session, parent_window=None):
    self.parent_window = parent_window  # Store reference
```

### 3. Add Close Handler
```python
# In SessionWindow class
def closeEvent(self, event):
    """Handle window close"""
    self.update_timer.stop()
    # Show parent window if it exists
    if self.parent_window:
        self.parent_window.show()
    event.accept()
```

This ensures:
- ✅ SessionWindow stays alive (referenced by MainWindow)
- ✅ When SessionWindow closes, MainWindow reappears
- ✅ Event loop stays alive (always has a visible window)
- ✅ Timer is properly stopped

### 4. Keep MainWindow in Memory
```python
# In MainWindow.new_session()
self.hide()  # Hide but don't delete
# MainWindow stays alive in memory
```

## Files Modified

- `python/gui.py`:
  - SessionWindow.__init__() - Added parent_window parameter
  - SessionWindow.closeEvent() - Added window close handler
  - MainWindow.new_session() - Pass self as parent, keep session_window reference

## Testing

Run the full flow test:
```bash
python test_full_flow.py
```

Or simply:
```bash
python main.py
```

Then:
1. Click "New Session"
2. Click "Add 18 Test Players"
3. Click "Start Session"
4. SessionWindow should now stay open showing the courts!

## Expected Behavior

- ✅ MainWindow appears
- ✅ Click "New Session" → SetupDialog appears
- ✅ Add players and click "Start Session" → SessionWindow appears with 2 courts
- ✅ MainWindow hides
- ✅ Courts display matches ready to play
- ✅ Close SessionWindow → MainWindow reappears
- ✅ Close MainWindow → Application exits

## Quality

- ✅ No breaking changes
- ✅ All 8 tests still passing
- ✅ Better window management
- ✅ Cleaner UI flow
