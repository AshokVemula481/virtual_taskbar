"""
Window Switcher — Switch to and close application windows.

Behavior:
  - Switch: bring window to front (restore if minimized)
  - Close: close using hwnd via WM_CLOSE
  - Uses AttachThreadInput trick for reliable foreground switching
"""

import ctypes
import ctypes.wintypes
import logging
from typing import Optional

import win32con
import win32gui
import win32process

logger = logging.getLogger(__name__)

DEBUG_MODE = False
SYSTEM_EXCLUDED_APPS = {
    "antigravity.exe",
    "python.exe",
    "pythonw.exe",
    "virtual taskbar.exe"
}

class WindowSwitcher:
    """
    Manages window switching and closing operations.
    Implements reliable force-foreground techniques.
    """

    @staticmethod
    def get_real_window(hwnd: int) -> int:
        root = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
        while True:
            owner = win32gui.GetWindow(root, win32con.GW_OWNER)
            if not owner:
                break
            root = owner
        return root

    @staticmethod
    def toggle_window(hwnd: int, app_key: str, active_app_key: Optional[str]) -> bool:
        """
        STABLE IDENTITY STATE MACHINE:
        Every click compares the clicked app identity with the last known active app.
        """
        if not hwnd or not win32gui.IsWindow(hwnd):
            return False

        try:
            import win32api
            
            # STEP 1: Get REAL current minimized state
            is_minimized = win32gui.IsIconic(hwnd)

            # STEP 2: Identity Comparison
            is_active = (app_key == active_app_key) and (active_app_key is not None)

            if DEBUG_MODE:
                print(f"CLICKED APP: {app_key}")
                print(f"CURRENT ACTIVE: {active_app_key}")

            # STEP 3: Native State Branching
            if is_minimized:
                if DEBUG_MODE: print("ACTION: RESTORE")
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return True

            elif is_active:
                if DEBUG_MODE: print("ACTION: MINIMIZE")
                win32api.PostMessage(
                    hwnd,
                    win32con.WM_SYSCOMMAND,
                    win32con.SC_MINIMIZE,
                    0
                )
                return True

            else:
                if DEBUG_MODE: print("ACTION: FOCUS")
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.SetForegroundWindow(hwnd)
                return True

        except Exception as e:
            if DEBUG_MODE: print("TOGGLE ERROR:", e)
            logger.error(f"Failed to toggle hwnd {hwnd}: {e}")
            return False

    @staticmethod
    def close_window(hwnd: int) -> bool:
        """
        Close the specified window gracefully via WM_CLOSE.
        Returns True on success.
        """
        if not hwnd or not win32gui.IsWindow(hwnd):
            return False

        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return True
        except Exception as e:
            logger.error(f"Failed to close hwnd {hwnd}: {e}")
            return False

    @staticmethod
    def minimize_window(hwnd: int) -> bool:
        """Minimize the specified window."""
        if not hwnd or not win32gui.IsWindow(hwnd):
            return False

        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return True
        except Exception as e:
            logger.error(f"Failed to minimize hwnd {hwnd}: {e}")
            return False

    @staticmethod
    def _force_foreground(hwnd: int):
        """
        Forcefully bring a window to the foreground.
        Uses AttachThreadInput trick to bypass Windows restrictions.
        """
        try:
            fg_hwnd = win32gui.GetForegroundWindow()
            fg_thread = ctypes.windll.user32.GetWindowThreadProcessId(
                fg_hwnd, ctypes.byref(ctypes.c_ulong())
            )
            our_thread = ctypes.windll.kernel32.GetCurrentThreadId()

            if fg_thread != our_thread:
                ctypes.windll.user32.AttachThreadInput(fg_thread, our_thread, True)

            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)

            if fg_thread != our_thread:
                ctypes.windll.user32.AttachThreadInput(fg_thread, our_thread, False)

        except Exception:
            # Fallback
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass
