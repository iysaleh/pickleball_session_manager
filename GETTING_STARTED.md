# Getting Started with the Python Pickleball App

## 🎉 What You've Received

A complete, tested Python GUI application for managing pickleball Round Robin sessions.

**Status**: ✅ Ready to use | 🚀 Ready for Phase 2 development

---

## 🚀 Quick Start (2 minutes)

### Step 1: Install Dependencies
```bash
python -m pip install PyQt6
```

### Step 2: Run the Application
```bash
python main.py
```

### Step 3: Create a Session
1. Click **"New Session"**
2. Leave defaults or customize:
   - Game Mode: Round Robin ✅ (King of the Court coming in Phase 2)
   - Session Type: Doubles or Singles
   - Number of Courts: 1-10
3. Click **"Add 18 Test Players"** for quick demo
4. Click **"Start Session"**

### Step 4: Play
1. Each court shows two teams
2. Enter scores (Team 1 vs Team 2)
3. Click **"Complete Match"**
4. Watch new matches auto-populate!

---

## 📚 Documentation

Read these in order:

1. **FINAL_SUMMARY.md** ← Start here! Executive overview
2. **PYTHON_VERSION_README.md** ← Feature details
3. **PYTHON_DEVELOPMENT_GUIDE.md** ← For developers
4. **MIGRATION_STATUS.md** ← Project progress
5. **IMPLEMENTATION_CHECKLIST.md** ← What's complete

---

## 🧪 Verify Installation

### Run Tests
```bash
python test_roundrobin.py
```

**Expected output:**
```
Ran 8 tests in 0.010s
OK
```

---

## 📁 File Structure

```
pickleball_rework_python/
├── python/                    # Core application
│   ├── types.py              # Data structures
│   ├── utils.py              # Helpers
│   ├── roundrobin.py         # Algorithm
│   ├── session.py            # Session logic
│   ├── queue_manager.py      # Court management
│   ├── gui.py                # GUI
│   └── kingofcourt.py        # KOC skeleton
│
├── main.py                   # Application launcher
├── test_roundrobin.py        # Unit tests
├── requirements.txt          # Dependencies
│
└── Documentation/
    ├── FINAL_SUMMARY.md      # Executive summary
    ├── PYTHON_VERSION_README.md
    ├── PYTHON_DEVELOPMENT_GUIDE.md
    ├── MIGRATION_STATUS.md
    └── IMPLEMENTATION_CHECKLIST.md
```

---

## ⚡ What Works Right Now

✅ **Round Robin Mode**
- Optimized match generation
- Maximizes player diversity
- Auto-fills courts

✅ **Session Management**
- Create sessions
- Add/remove players
- Complete matches with scores
- Forfeit matches
- Track statistics

✅ **UI**
- Professional PyQt6 interface
- Real-time court displays
- Score input
- Player list management

✅ **Testing**
- 8 comprehensive tests
- All passing ✅

---

## 🚧 What's Coming

### Phase 2: King of the Court
- ELO rating system
- Rank-based matchmaking
- Strategic waiting
- Expected: 1-2 days to implement

### Phase 3: Advanced Features
- Session save/load
- Locked teams
- Statistics dashboard
- Expected: 3-4 days

### Phase 4: Polish
- Dark mode
- Better UI
- Performance optimization
- Expected: 2-3 days

---

## 🆘 Troubleshooting

### "PyQt6 not found"
```bash
python -m pip install PyQt6
```

### "ModuleNotFoundError: No module named 'python'"
Make sure you're running from the project root:
```bash
cd /path/to/pickleball_rework_python
python main.py
```

### Tests not running
```bash
# From project root
python test_roundrobin.py
```

### GUI won't start
- Check Python version: `python --version` (need 3.8+)
- Check PyQt6: `python -c "import PyQt6; print('OK')"`
- Check current directory: `pwd` should end in `pickleball_rework_python`

---

## 💻 System Requirements

**Minimum:**
- Python 3.8+
- 50MB disk space
- 100MB RAM

**Recommended:**
- Python 3.10+
- 200MB disk space
- 256MB RAM

**Supported:**
- Windows 10+
- macOS 10.14+
- Linux (Ubuntu 20.04+)

---

## 🎯 Key Features

### Round Robin Algorithm
The heart of the app - intelligently generates matches to maximize variety:

```
Every match tries to:
✓ Use different partners than before
✓ Face different opponents than before
✓ Distribute play time fairly
✓ Respect banned pairs
```

### Real-time Court Management
```
1. Match completed on Court 1
2. Next match from queue auto-fills Court 1
3. Seamless, continuous play
```

### Player Statistics
```
Tracks:
- Games played/waited
- Wins/losses
- Points scored/against
- Partners history
- Opponents history
```

---

## 🔧 For Developers

### To Understand the Code
1. Read `PYTHON_DEVELOPMENT_GUIDE.md`
2. Study `python/types.py` (data model)
3. Study `python/roundrobin.py` (algorithm)
4. Study `test_roundrobin.py` (how it works)

### To Add Features
1. Define types in `types.py`
2. Implement logic in appropriate module
3. Write tests
4. Update GUI if needed
5. Run test suite: `python test_roundrobin.py`

### To Implement Phase 2 (KOC)
1. Read King of the Court section in `PYTHON_DEVELOPMENT_GUIDE.md`
2. Reference TypeScript version: `src/kingofcourt.ts`
3. Implement functions in `python/kingofcourt.py`
4. Add tests
5. Update `gui.py` to support KOC mode

---

## 📊 Project Stats

```
Total Code: ~1,710 lines
Python Modules: 8
Tests: 8/8 passing ✅
Documentation: 6 files
Type Coverage: 100% with dataclasses
```

---

## ✨ What Makes This Great

✅ **Complete** - Round Robin fully working
✅ **Tested** - 8 tests, all passing
✅ **Documented** - 6 detailed guides
✅ **Type-Safe** - Dataclasses + type hints
✅ **Modular** - Clean architecture
✅ **Extensible** - Phase 2 skeleton ready
✅ **Professional** - Production-quality code

---

## 📞 Quick Reference

### Common Commands

```bash
# Install dependencies
python -m pip install PyQt6

# Run application
python main.py

# Run tests
python test_roundrobin.py

# Check Python version
python --version

# Check syntax
python -m py_compile python/*.py
```

### Key Files

- **main.py** - Start the app here
- **python/types.py** - Understand the data model here
- **python/roundrobin.py** - Understand the algorithm here
- **test_roundrobin.py** - See how everything works here
- **PYTHON_DEVELOPMENT_GUIDE.md** - Learn to extend here

---

## 🎓 Learning Path

### For Users
1. Run `python main.py`
2. Create a session with test players
3. Complete a few matches
4. Observe the player variety

### For Developers
1. Read `PYTHON_DEVELOPMENT_GUIDE.md`
2. Run `python test_roundrobin.py`
3. Study `python/types.py`
4. Study `python/roundrobin.py`
5. Try implementing a small feature

### For Contributors
1. Complete Learning Path (Developers)
2. Pick a Phase 2 task
3. Reference TypeScript version in `src/`
4. Implement with tests
5. Submit for review

---

## 🎉 You're Ready!

The application is **production-ready for Round Robin mode**.

Start playing with it now, and follow the development guide when you're ready for Phase 2!

**Questions?** Check the relevant documentation file above.

---

*Start here: `python main.py` ✨*
