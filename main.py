import os
import sys

# Step 1: Absolute Production Silence (Must be first)
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"
os.environ["QT_OPENGL"] = "software"
os.environ["QT_QUICK_BACKEND"] = "software"
sys.stderr = open(os.devnull, "w")

"""
Virtual Floating Taskbar — Main entry point.
Final Production Build.
"""

import ctypes
import psutil

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSharedMemory, QTimer, Qt

# Set Global Attributes BEFORE creating QApplication
QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)
QApplication.setAttribute(Qt.AA_ForceRasterWidgets)

from overlay import TaskbarOverlay

# Step 1: Singleton Key
APP_KEY = "VirtualTaskbar_Final_Fix_Key"

def cleanup_ghosts():
    """Kill hanging taskbar processes."""
    pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = proc.info.get('cmdline')
            if cmd and any('main.py' in arg for arg in cmd):
                if proc.info['pid'] != pid: proc.kill()
        except: pass

def set_dpi():
    try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except: pass

def main():
    # Step 6: Debug Print
    print("Starting Virtual Taskbar...")
    
    set_dpi()

    app = QApplication(sys.argv)
    
    # Step 1: Singleton Architecture (Stale Lock Fix)
    shared = QSharedMemory(APP_KEY)
    if shared.attach():
        shared.detach()
        print("Another instance is already running.")
        sys.exit(0)
    if not shared.create(1):
        print("Another instance is already running.")
        sys.exit(0)

    cleanup_ghosts()

    # Step 2 & 3: UI Startup
    window = TaskbarOverlay()
    window.show()
    window.raise_()
    window.activateWindow()
    
    # Standard topmost maintenance
    timer = QTimer(app)
    timer.timeout.connect(window.ensure_topmost)
    timer.start(2000)

    print("Taskbar is now active.")
    
    res = app.exec_()
    shared.detach()
    sys.exit(res)

if __name__ == "__main__":
    main()
