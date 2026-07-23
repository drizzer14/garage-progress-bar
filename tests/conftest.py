import os
import sys
import types

# Make the in-game package importable in tests without the game engine.
_CLIENT = os.path.join(os.path.dirname(__file__), "..", "src", "res", "scripts", "client")
sys.path.insert(0, os.path.abspath(_CLIENT))

# bridge/mod_settings imports the game's `debug_utils` at module load; stub it once here
# (idempotent) so every test can import the bridge without the game engine.
if "debug_utils" not in sys.modules:
    _dbg = types.ModuleType("debug_utils")
    _dbg.LOG_CURRENT_EXCEPTION = lambda *a, **k: None
    _dbg.LOG_NOTE = lambda *a, **k: None
    sys.modules["debug_utils"] = _dbg
