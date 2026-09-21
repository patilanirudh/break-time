"""PyInstaller entry point.

A thin wrapper rather than pointing PyInstaller directly at src/breaktime/main.py, so the
built exe imports the `breaktime` package the normal way (via pathex) instead of running
main.py as a loose top-level script.
"""

from breaktime.main import main

if __name__ == "__main__":
    main()
