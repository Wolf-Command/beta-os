"""Wolf Core software packages (Beta). Organisation Registry first."""

import os
import sys
from pathlib import Path


def _install_test_guard() -> None:
    testish = (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1"
    argv = " ".join(sys.argv).replace("\\", "/")
    if not testish and "scripts/tests" not in argv and sys.argv:
        try:
            testish = "scripts/tests" in str(Path(sys.argv[0]).resolve())
        except OSError:
            testish = False
    if not testish:
        return
    from core.canonical_guard import install

    install()


_install_test_guard()
