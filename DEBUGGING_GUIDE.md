# Debugging Guide - Session Creation Crash

## Quick Fix Summary

If the application crashes silently when pressing "Start Session", follow these steps:

### Step 1: Run with Error Output

Instead of:
```bash
python main.py
```

Run one of these to see errors:

```bash
# Option A: With debug logging
python -u main.py 2>&1

# Option B: With debug launcher
python debug_main.py

# Option C: With full traceback
python -X dev main.py
```

### Step 2: Test Components Individually

Test if the core logic works without GUI:
```bash
python test_session_creation.py
```

Test if GUI components work:
```bash
python test_gui_debug.py
```

Test if tests pass:
```bash
python test_roundrobin.py
```

### Step 3: Check Error Messages

Error messages now appear in:
1. **Console output** (terminal window)
2. **Pop-up dialog** (in the GUI)
3. **Log file** (when using debug launcher)

---

## What Was Added

### Error Handling Improvements

1. **SetupDialog.start_session()** - Added try/except with error dialog
2. **MainWindow.new_session()** - Added try/except around session window creation
3. **SessionWindow.__init__()** - Added try/except around initialization
4. **SessionWindow.refresh_display()** - Added try/except with graceful fallback
5. **main.py** - Added logging and error handling

### New Debug Tools

1. **debug_main.py** - Debug launcher with detailed logging
2. **test_session_creation.py** - Test session creation logic
3. **test_gui_debug.py** - Test GUI components without main window
4. **ERROR DIALOGS** - Pop-up dialogs now show errors with full traceback

---

## How to Run in Debug Mode

### Method 1: Simple Console Output
```bash
cd C:\path\to\pickleball_rework_python
python main.py 2>&1 | findstr ERROR
```

This will show any errors that occur.

### Method 2: With Logging
```bash
python debug_main.py
```

This shows detailed logging of everything the application does.

### Method 3: Full Exception Details
```bash
python -X dev main.py
```

This enables all debugging features in Python.

---

## Common Issues & Fixes

### Issue: "ModuleNotFoundError: No module named 'python'"
**Solution**: Run from the project root directory
```bash
cd C:\Users\Ibraheem Saleh\Documents\ProjectDevelopment\pickleball_rework_python
python main.py
```

### Issue: "No module named 'PyQt6'"
**Solution**: Install PyQt6
```bash
python -m pip install PyQt6
```

### Issue: GUI closes without error message
**Solution**: Run with error output redirection
```bash
python main.py 2>&1
```

### Issue: Can't see error dialog
**Solution**: Check console output while running:
```bash
python debug_main.py
```

---

## Verifying Everything Works

Run all tests:
```bash
python test_roundrobin.py        # Core logic tests
python test_session_creation.py  # Session creation
python test_gui_debug.py         # GUI components
```

All should show `✓ PASSED` or `OK`.

---

## If Problems Persist

1. **Note the exact error message** - Copy it from the console or pop-up
2. **Check the traceback** - Shows the file and line number where it crashed
3. **Run component tests** - Narrow down which part is failing
4. **Check logs** - Review debug_main.py output for clues

---

## How Errors Will Now Appear

### Before (Silent Crash)
- GUI closes with no message
- User confused

### After (Clear Error Messages)
- **Pop-up dialog** shows error with traceback
- **Console output** shows detailed error information
- **Log file** available when using debug launcher

Example error dialog:
```
Error creating session:
[detailed error message]

Type: [ExceptionType]
```

---

## Next Steps

1. **Run the app**: `python main.py`
2. **If it crashes**, run: `python debug_main.py`
3. **Copy the error** shown in console or dialog
4. **Share the error** for further debugging

The app should now work, but if you encounter any issues, the error messages will clearly show what went wrong and where.
