"""AreaGrab entry point.

The implementation lives in the ``areagrab`` package; this file stays as the
PyInstaller entry point so existing build scripts keep working.
"""

from areagrab.app import main

if __name__ == "__main__":
    main()
