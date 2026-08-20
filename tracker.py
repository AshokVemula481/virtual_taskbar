import win32gui
import win32process
import win32con
import psutil
import logging
import ctypes
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

# STEP 1: AppUserModelID Integration
import pythoncom
from win32com.propsys import propsys, pscon

DEBUG_MODE = False
PERSISTENT_APP_CACHE: Dict[str, 'AppInfo'] = {}

logger = logging.getLogger(__name__)

OWN_WINDOW_TITLE = "Virtual Taskbar Overlay"
SYSTEM_EXCLUDED_APPS = {
    "antigravity.exe",
    "python.exe",
    "pythonw.exe",
    "virtual taskbar.exe"
}

class AppState(Enum):
    ACTIVE = 1
    RUNNING = 2
    MINIMIZED = 3

# STEP 1 — CREATE TITLE MAP
UWP_TITLE_MAP = {
    "weather": "windows_weather",
    "maps": "windows_maps",
    "calculator": "windows_calculator",
    "clock": "windows_clock",
    "settings": "windows_settings",
    "films": "windows_filmtv",
    "media player": "windows_media",
    "news": "windows_news",
    "ticktick": "ticktick",
    "to do": "windows_todo",
}

def get_stable_app_id(title: str, exe_path: str, hwnd: int) -> str:
    # STEP 2 — NORMALIZE TITLE
    title_lower = title.lower().strip()
    low_exe = exe_path.lower()
    
    # STEP 3 — MATCH TITLES
    for keyword, app_id in UWP_TITLE_MAP.items():
        if keyword in title_lower:
            # STEP 4 — FORCE STABLE APP ID
            return app_id

    # If it's a generic host (UWP), assign a unique HWND-based key if no title match
    if "applicationframehost.exe" in low_exe:
        return f"uwp_{hwnd}"
        
    for excluded in SYSTEM_EXCLUDED_APPS:
        if excluded in low_exe:
            return None
            
    return low_exe

@dataclass
class AppInfo:
    app_key: str
    exe_path: str
    process_name: str
    pid: int
    hwnds: List[int]
    state: AppState
    usage_seconds: float = 0.0
    icon_loaded: bool = False # STEP 3: ICON LOADING STATE

    def best_hwnd(self) -> int:
        return self.hwnds[0] if self.hwnds else 0

# Track usage times
USAGE_STATS = {} # app_key -> seconds

def get_usage_time(app_key: str) -> float:
    return USAGE_STATS.get(app_key, 0.0)

def update_usage(active_app_key: str):
    if not active_app_key: return
    USAGE_STATS[active_app_key] = USAGE_STATS.get(active_app_key, 0.0) + 1.2 # Match refresh rate

LAST_KNOWN_ACTIVE_APP: Optional[str] = None

def get_running_apps() -> Dict[str, AppInfo]:
    global PERSISTENT_APP_CACHE, LAST_KNOWN_ACTIVE_APP
    
    foreground_hwnd = win32gui.GetForegroundWindow()
    DWMWA_CLOAKED = 14
    
    found_this_cycle = set()
    current_cycle_active: Optional[str] = None
    
    def enum_windows(hwnd, _):
        nonlocal current_cycle_active
        # 1. STRICT HWND FILTERS
        title = win32gui.GetWindowText(hwnd).strip()
        class_name = win32gui.GetClassName(hwnd)
        
        # STEP 5: SHELL FILTER
        SHELL_IGNORE_LIST = ["desktopwindowxamlsource", "gdi+ window", "default ime", "msctfime ui", "msg", "system tray"]
        low_title = title.lower()
        low_class = class_name.lower()
        if any(x in low_title or x in low_class for x in SHELL_IGNORE_LIST): return
        
        if not title: title = class_name
        if not title: return
        
        if not win32gui.IsWindowVisible(hwnd): return
        if win32gui.GetParent(hwnd) != 0: return
        
        exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if exstyle & win32con.WS_EX_TOOLWINDOW: return
        
        try:
            cloaked = ctypes.c_int()
            ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
            if cloaked.value != 0: return
        except: pass

        # STEP 6: OWN WINDOW FILTER
        is_own = OWN_WINDOW_TITLE.lower() in title.lower() or class_name in ["Qt5QWindowIcon", "Qt5152QWindowIcon"]
        if is_own: return

        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            proc_name = proc.name().lower()
            if proc_name == "python.exe": return
            
            exe_path = proc.exe().lower()
            
            # STEP 1 & 3: Get Stable Identity (STRICT)
            app_id = get_stable_app_id(title, exe_path, hwnd)
            if not app_id: return # BLOCK Generic Host Windows

            state = AppState.RUNNING
            if hwnd == foreground_hwnd:
                state = AppState.ACTIVE
                current_cycle_active = app_id
            elif win32gui.IsIconic(hwnd): 
                state = AppState.MINIMIZED

            if state == AppState.ACTIVE: update_usage(app_id)
                
            # STEP 5: PERSISTENT UPDATE
            PERSISTENT_APP_CACHE[app_id] = AppInfo(
                app_key=app_id,
                exe_path=exe_path,
                process_name=proc_name,
                pid=pid,
                hwnds=[hwnd],
                state=state,
                usage_seconds=get_usage_time(app_id)
            )
            found_this_cycle.add(app_id)

        except (psutil.NoSuchProcess, psutil.AccessDenied): pass

    win32gui.EnumWindows(enum_windows, None)
    
    # UPDATE PERSISTENT ACTIVE APP
    # Only update if we found a new active app (that isn't the taskbar)
    if current_cycle_active:
        LAST_KNOWN_ACTIVE_APP = current_cycle_active
    
    # STEP 6: INVISIBLE WINDOW CLEANUP
    stale_keys = []
    for app_id, info in PERSISTENT_APP_CACHE.items():
        if app_id not in found_this_cycle:
            if not win32gui.IsWindow(info.best_hwnd()):
                stale_keys.append(app_id)
            else:
                if info.state == AppState.ACTIVE:
                    info.state = AppState.RUNNING

    for key in stale_keys:
        PERSISTENT_APP_CACHE.pop(key)
            
    return PERSISTENT_APP_CACHE

def update_active_app():
    """High-speed polling for the active window to ensure tracker.active_app_key is never None."""
    global LAST_KNOWN_ACTIVE_APP
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd or not win32gui.IsWindow(hwnd): return

        # 1. Identity Verification
        title = win32gui.GetWindowText(hwnd)
        class_name = win32gui.GetClassName(hwnd)
        
        # SKIP OWN WINDOW
        if OWN_WINDOW_TITLE.lower() in title.lower() or class_name in ["Qt5QWindowIcon", "Qt5152QWindowIcon"]:
            return

        # 2. Get Root Window (For UWP/Electron consistency)
        root = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
        while True:
            owner = win32gui.GetWindow(root, win32con.GW_OWNER)
            if not owner: break
            root = owner

        # 3. Get Process ID and Path
        _, pid = win32process.GetWindowThreadProcessId(root)
        proc = psutil.Process(pid)
        p_name = proc.name().lower()
        
        # EXCLUDE INTERNAL APPS
        if p_name in SYSTEM_EXCLUDED_APPS:
            return
        
        exe_path = proc.exe().lower()
        title = win32gui.GetWindowText(root)

        # 4. Generate Stable Key (Same as get_running_apps)
        app_id = get_stable_app_id(title, exe_path, root)
        
        if app_id:
            LAST_KNOWN_ACTIVE_APP = app_id
            if DEBUG_MODE:
                print(f"ACTIVE UPDATED: {LAST_KNOWN_ACTIVE_APP}")
            
    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
        pass

def get_active_app_key() -> Optional[str]:
    """Helper to find the key of the currently active app."""
    return LAST_KNOWN_ACTIVE_APP
