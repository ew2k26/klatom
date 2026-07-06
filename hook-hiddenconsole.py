import ctypes
import sys

if sys.platform == "win32":
    try:
        k = ctypes.windll.kernel32
        h = k.GetConsoleWindow()
        if h:
            ctypes.windll.user32.ShowWindow(h, 0)
    except Exception:
        pass
