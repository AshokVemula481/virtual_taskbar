import win32gui
import win32ui
import win32con
import win32api
import os
import win32com.client
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtWinExtras import QtWin

# 1. CORE CONFIG
ICON_SIZE = 32
ICON_CACHE = {}
LOGGED_UWP_WARNINGS = set()
DEBUG_MODE = False # Production Mode Active

# 2. STRICT REGISTRY
# Only apps in this map get premium PNG icons
APP_ICONS = {
    "windows_maps": "assets/maps.png",
    "windows_news": "assets/news.png",
    "windows_media": "assets/media_player.png",
    "windows_settings": "assets/settings.png",
    "windows_calculator": "assets/calculator.png",
    "windows_clock": "assets/clock.png",
    "windows_weather": "assets/weather.png",
    "windows_photos": "assets/photos.png",
    "windows_filmtv": "assets/filmtv.png",
    "windows_todo": "assets/todo.png",
    "ticktick": "assets/ticktick.png",
    "microsoft edge": "assets/edge.png",
}

def get_neutral_fallback():
    """Final safety net icon - neutral and professional."""
    from PyQt5.QtWidgets import QApplication, QStyle
    return QApplication.style().standardIcon(QStyle.SP_FileIcon).pixmap(28, 28)

def extract_exe_icon(exe_path):
    """Dynamic extraction from binary files."""
    try:
        large, small = win32gui.ExtractIconEx(exe_path, 0)
        hicon = None
        if small:
            hicon = small[0]
            for i in range(1, len(small)): win32gui.DestroyIcon(small[i])
            if large:
                for h in large: win32gui.DestroyIcon(h)
        elif large:
            hicon = large[0]
            for i in range(1, len(large)): win32gui.DestroyIcon(large[i])
        
        if not hicon: return None
        pixmap = QtWin.fromHICON(hicon)
        win32gui.DestroyIcon(hicon)
        return pixmap
    except: return None

class IconManager:
    @classmethod
    def get_app_icon(cls, app_key: str, exe_path: str, hwnd: int = 0):
        """Final Production Pipeline - Stable & Accurate."""
        # 0. Check Cache
        if app_key in ICON_CACHE: return ICON_CACHE[app_key]

        resolved_pixmap = None
        source = "NONE"

        # STEP 1: NATIVE WINDOW HANDLE (Best for Live State & WhatsApp)
        if hwnd:
            try:
                res = win32gui.SendMessage(hwnd, win32con.WM_GETICON, win32con.ICON_BIG, 0)
                if not res: res = win32gui.SendMessage(hwnd, win32con.WM_GETICON, win32con.ICON_SMALL, 0)
                if not res: res = win32gui.GetClassLong(hwnd, win32con.GCL_HICON)
                
                if res:
                    pix = QtWin.fromHICON(res)
                    if pix and not pix.isNull():
                        resolved_pixmap = pix.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        source = "HWND_NATIVE"
            except: pass

        # STEP 2: BINARY EXTRACTION (For standard Win32 apps)
        if not resolved_pixmap:
            if not "applicationframehost" in exe_path.lower():
                pix = extract_exe_icon(exe_path)
                if pix and not pix.isNull():
                    resolved_pixmap = pix.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    source = f"EXE_BINARY ({os.path.basename(exe_path)})"

        # STEP 3: CURATED PNG REGISTRY (Best for UWP Identity)
        if not resolved_pixmap:
            # A. Direct Key Match
            if app_key in APP_ICONS:
                path = APP_ICONS[app_key]
                if os.path.exists(path):
                    if DEBUG_MODE: print(f"ICON FILE: {path}")
                    pix = QPixmap(path)
                    if not pix.isNull():
                        resolved_pixmap = pix.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        source = f"STATIC_REGISTRY ({path})"
                elif DEBUG_MODE:
                    print(f"MISSING ICON ASSET: {path}")

            # B. UWP Title Match (Final fallback for Host Windows)
            if not resolved_pixmap and hwnd:
                title = win32gui.GetWindowText(hwnd).lower()
                UWP_KEYWORDS = {
                    "maps": "assets/maps.png",
                    "news": "assets/news.png",
                    "media player": "assets/media_player.png",
                    "ticktick": "assets/ticktick.png",
                    "settings": "assets/settings.png",
                    "photos": "assets/photos.png",
                    "calculator": "assets/calculator.png",
                    "weather": "assets/weather.png",
                    "film": "assets/filmtv.png",
                    "media player": "assets/media_player.png",
                    "media": "assets/media_player.png",
                    "to do": "assets/todo.png",
                }
                for keyword, path in UWP_KEYWORDS.items():
                    if keyword in title:
                        if os.path.exists(path):
                            if DEBUG_MODE: print(f"ICON FILE: {path} (via UWP Keyword: {keyword})")
                            pix = QPixmap(path)
                            if not pix.isNull():
                                resolved_pixmap = pix.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                source = f"REGISTRY_UWP_KEYWORD ({keyword})"
                                break
                        elif DEBUG_MODE:
                            print(f"MISSING UWP ASSET: {path}")

        # STEP 4: NEUTRAL FALLBACK
        if not resolved_pixmap:
            resolved_pixmap = get_neutral_fallback()
            source = "NEUTRAL_FALLBACK"

        # Debug Trace
        if DEBUG_MODE:
            print(f"ICON_RESOLVE | KEY: {app_key} | SOURCE: {source}")

        ICON_CACHE[app_key] = resolved_pixmap
        return resolved_pixmap

def is_uwp_key(app_key):
    return app_key.startswith("windows_") or app_key.startswith("uwp_")

# Compatibility Export
def get_fallback_icon():
    return get_neutral_fallback()
