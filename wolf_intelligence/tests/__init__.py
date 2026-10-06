"""Wolf Intelligence tests. Importing this package isolates WI state first."""
# --- State isolation (Vesper M1) -------------------------------------------
# Runs before any wolf_intelligence import so paths.STATE_ROOT resolves to a
# throwaway temp dir. No test can read or write the live Beta WI state.
import atexit as _atexit
import os as _os
import shutil as _shutil
import sys as _sys
import tempfile as _tempfile


def _isolate_test_state() -> None:
    if _os.environ.get("WI_TEST_STATE_ISOLATED"):
        return
    _os.environ["WI_TEST_CONFIGURED_STATE_ROOT"] = _os.environ.get("WOLF_INTELLIGENCE_STATE_ROOT", "")
    _TEST_STATE_ROOT = _tempfile.mkdtemp(prefix="wi-test-state-")
    _os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = _TEST_STATE_ROOT
    _os.environ["WI_TEST_STATE_ISOLATED"] = _TEST_STATE_ROOT
    _os.environ.pop("WOLF_INTELLIGENCE_CONFIG_MIRROR", None)
    _atexit.register(_shutil.rmtree, _TEST_STATE_ROOT, True)
    if "wolf_intelligence.paths" in _sys.modules:
        from wolf_intelligence.paths import rebind_state_paths

        rebind_state_paths()


_isolate_test_state()
# ---------------------------------------------------------------------------
