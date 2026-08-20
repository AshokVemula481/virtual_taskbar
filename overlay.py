"""
Overlay UI — Direct Architecture (Real Final Fix).
- Software Rendering Pipeline.
- Static Icons (No animations/ghosts).
- Stable Opaque-Alpha background.
"""

# SAFE ENGINEERING MODE ENABLED
# ALWAYS CREATE BACKUP BEFORE MODIFYING
# NEVER REMOVE STABLE LOGIC
# NEVER ENABLE PERMANENT DEBUG PRINTS

import os
import signal
import logging
import json
from typing import Dict, List, Optional

from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt, QTimer, QSize, QPoint, QRect, QRectF, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen, QPixmap, QCursor, QFont

from tracker import AppInfo, AppState, OWN_WINDOW_TITLE, get_active_app_key
from icons import IconManager, ICON_SIZE
from switcher import WindowSwitcher
from preview_manager import PreviewWidget

logger = logging.getLogger(__name__)

# Design Tokens
BAR_WIDTH = 600
BAR_HEIGHT = 45
ICON_WIDGET_WIDTH = 40
ICON_BASE_SIZE = 26
WIDGET_SPACING = 6
TASKBAR_Y_OFFSET = 10
CONTROL_BTN_SIZE = 26

def format_usage(seconds: float) -> str:
    """Helper to format seconds into h m format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"

# Step 6: Opaque-Alpha Background (No WA_TranslucentBackground)
BG_COLOR = QColor(10, 10, 15, 230)
ACTIVE_INDICATOR = QColor(255, 255, 255, 255)
RUNNING_INDICATOR = QColor(255, 255, 255, 120)
MINIMIZED_INDICATOR = QColor(255, 255, 255, 60)

class AppIconWidget(QWidget):
    switch_requested = pyqtSignal(str) # app_key

    def __init__(self, app_key: str, pid: int, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.app_key, self.pid = app_key, pid
        self._pixmap = pixmap
        self._state = AppState.RUNNING
        
        # DRAG STATE
        self.drag_start_pos = None
        self.is_dragging = False
        
        # PREVIEW TIMER (300ms delay)
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.show_preview)
        
        # Step 3: Create Floating Close Button
        self.close_btn = QPushButton("✕", self)
        self.close_btn.hide()
        self.close_btn.setFixedSize(14, 14)
        self.close_btn.move(26, 2)
        
        # Step 4: Close Button Style
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 70, 70, 220);
                color: white;
                border: none;
                border-radius: 7px;
                font-size: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 30, 30, 255);
            }
        """)
        self.close_btn.clicked.connect(self.close_app)
        
        # Feature 1: Hover Scaling (Safe Version)
        self._hover_scale = 1.0
        self.anim = QPropertyAnimation(self, b"hover_scale")
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.OutElastic) # Premium Elastic Feel
        
        # INDICATOR ANIMATION (Step 1)
        self._indicator_val = 0.0
        self.ind_anim = QPropertyAnimation(self, b"indicator_val")
        self.ind_anim.setDuration(300)
        self.ind_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.setFixedSize(ICON_WIDGET_WIDTH, BAR_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        
        # Step 1 & 2: Disable Graphics Effects & Force full repaint
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

    @pyqtProperty(float)
    def hover_scale(self):
        return self._hover_scale

    @hover_scale.setter
    def hover_scale(self, val):
        self._hover_scale = val
        self.update() # SAFE update only

    @pyqtProperty(float)
    def indicator_val(self): return self._indicator_val
    @indicator_val.setter
    def indicator_val(self, val):
        self._indicator_val = val
        self.update()

    def enterEvent(self, e):
        self.close_btn.show()
        self.anim.stop()
        self.anim.setEndValue(1.18) # SAFE Limit
        self.anim.start()
        
        # Start Preview Timer
        self.preview_timer.start(350)

    def leaveEvent(self, e):
        self.close_btn.hide()
        self.anim.stop()
        self.anim.setEndValue(1.0)
        self.anim.start()
        
        # Stop and Hide Preview
        self.preview_timer.stop()
        if hasattr(self.parent(), 'preview_popup'):
            self.parent().preview_popup.hide()

    def show_preview(self):
        if not hasattr(self.parent(), 'preview_popup'): return
        
        # Get REAL hwnd from tracker
        from tracker import get_running_apps
        apps = get_running_apps()
        if self.app_key not in apps: return
        
        info = apps[self.app_key]
        hwnd = info.best_hwnd()
        
        # Position preview above icon
        pos = self.mapToGlobal(QPoint(0, 0))
        preview = self.parent().preview_popup
        preview.set_target(hwnd, self.app_key.split('\\')[-1])
        preview.move(pos.x() + (self.width() - preview.width())//2, pos.y() - preview.height() - 10)
        preview.show()

    def close_app(self):
        try:
            if self.pid:
                os.kill(self.pid, signal.SIGTERM)
        except Exception as e:
            print(f"Close failed: {e}")

    def update_state(self, state: AppState):
        if self._state == state: return
        old_state = self._state
        self._state = state
        
        # Trigger indicator animation on state change
        if state == AppState.ACTIVE:
            self.ind_anim.stop()
            self.ind_anim.setEndValue(1.0)
            self.ind_anim.start()
        elif old_state == AppState.ACTIVE:
            self.ind_anim.stop()
            self.ind_anim.setEndValue(0.0)
            self.ind_anim.start()
            
        self.update()

    def paintEvent(self, event):
        # Step 8: Simple Paint Event (No CompositionModes)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        dot_y = h - 6
        dot_x = (w - 3) // 2
        
        # Feature 1 & 5: Static Icon with Scaling (Step 5)
        pix = self._pixmap
        if not pix or pix.isNull():
            # STEP 6: UI PLACEHOLDER (Single temporary icon)
            from icons import get_fallback_icon
            pix = get_fallback_icon()

        if pix and not pix.isNull():
            size = int(ICON_BASE_SIZE * self._hover_scale)
            x = (w - size) // 2
            y = (h - size) // 2 - 2
            painter.drawPixmap(x, y, size, size, pix)

        # Feature 3: Premium Active App Glow & Line
        if self._state == AppState.ACTIVE or self._indicator_val > 0.0:
            alpha = int(self._indicator_val * 255)
            
            # 1. Subtle Glow behind icon
            from PyQt5.QtGui import QRadialGradient
            glow = QRadialGradient(w/2, h/2, 20)
            glow.setColorAt(0, QColor(0, 180, 255, int(alpha * 0.2)))
            glow.setColorAt(1, QColor(0, 180, 255, 0))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.NoPen)
            painter.drawRect(self.rect())

            # 2. Animated Underline (Expands from center)
            painter.setBrush(QBrush(QColor(0, 180, 255, alpha)))
            line_w = 12 * self._indicator_val
            line_x = (w - line_w) / 2
            painter.drawRoundedRect(QRectF(line_x, h - 4, line_w, 2), 1, 1)
        else:
            # Standard Running Indicator
            painter.setPen(Qt.NoPen)
            color = RUNNING_INDICATOR if self._state == AppState.RUNNING else MINIMIZED_INDICATOR
            painter.setBrush(QBrush(color))
            painter.drawEllipse(int(dot_x), int(dot_y), 3, 3)
        
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
            
    def mouseMoveEvent(self, event):
        if not self.drag_start_pos: return
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
            
        # Start Drag
        self.is_dragging = True
            
        from PyQt5.QtGui import QDrag
        from PyQt5.QtCore import QMimeData
        
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.app_key)
        drag.setMimeData(mime)
        
        # Translucent Preview
        pix = self.grab()
        drag.setPixmap(pix)
        drag.setHotSpot(event.pos())
        
        # Stop Preview Timer (Don't show thumbnail while dragging)
        self.preview_timer.stop()
        if hasattr(self.parent(), 'preview_popup'):
            self.parent().preview_popup.hide()
            
        drag.exec_(Qt.MoveAction)
        self.is_dragging = False
        self.drag_start_pos = None

    def mouseReleaseEvent(self, event):
        if not self.is_dragging:
            self.switch_requested.emit(self.app_key)
        
        self.is_dragging = False
        self.drag_start_pos = None

class ControlButton(QWidget):
    clicked = pyqtSignal()
    def __init__(self, icon_type: str, color: QColor, parent=None):
        super().__init__(parent)
        self.icon_type, self.color = icon_type, color
        self.setFixedSize(CONTROL_BTN_SIZE, CONTROL_BTN_SIZE)
        self.setCursor(Qt.PointingHandCursor)
    def mousePressEvent(self, event): self.clicked.emit()
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(255,255,255,20)))
        painter.setPen(QPen(Qt.white, 2))
        painter.drawEllipse(self.rect().adjusted(1,1,-1,-1))
        c, d = self.width()//2, 5
        if self.icon_type=="close":
            painter.drawLine(c-d, c-d, c+d, c+d); painter.drawLine(c+d, c-d, c-d, c+d)
        else: painter.drawLine(c-d, c, c+d, c)

        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 7, 7)

class TaskbarOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self._icon_manager = IconManager()
        self._switcher = WindowSwitcher()
        self._widgets: Dict[str, AppIconWidget] = {}
        self.is_minimized = False
        self.visual_order = self.load_layout()
        
        self.setAcceptDrops(True)
        self._init_ui()

    def _init_ui(self):
        # Step 6: Create Single Root Container
        self.main_container = QWidget(self)
        self.main_container.setObjectName("mainContainer")
        self.main_container.setStyleSheet("""
            QWidget#mainContainer {
                background-color: rgba(10, 15, 25, 210);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 26px;
            }
        """)

        # Step 3: Initialize Restore Dot (Hidden by default)
        self.min_dot = QPushButton("", self)
        self.min_dot.hide()
        self.min_dot.setFixedSize(46, 18)
        self.min_dot.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #4facfe,
                    stop:1 #7b61ff
                );
                border: none;
                border-radius: 9px;
            }
            QPushButton:hover {
                background: #7b61ff;
            }
        """)
        self.min_dot.clicked.connect(self.restore_taskbar)

        self._setup_window()
        self._setup_layout()
        
        # PREVIEW SYSTEM
        self.preview_popup = PreviewWidget()
        
        # ACTIVE APP POLLING (High Frequency)
        # Ensures tracker knows pre-click state even after overlay steals focus
        self.active_poll_timer = QTimer(self)
        self.active_poll_timer.timeout.connect(self.poll_active_app)
        self.active_poll_timer.start(500) # 2 times per second

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_apps)
        self.refresh_timer.start(1500) # UI Refresh Rate

        self.show()
        self.raise_()
        print("Overlay UI Loaded")

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        app_key = event.mimeData().text()
        pos = event.pos()
        
        # Determine new index
        new_index = -1
        for i in range(self.icons_layout.count()):
            w = self.icons_layout.itemAt(i).widget()
            if w and pos.x() < w.mapTo(self, w.rect().center()).x():
                new_index = i
                break
        
        if new_index == -1:
            new_index = self.icons_layout.count()
            
        # Update Visual Order
        if app_key in self.visual_order:
            self.visual_order.remove(app_key)
            
        # Correct index if moving forward
        self.visual_order.insert(min(new_index, len(self.visual_order)), app_key)
        self.save_layout()
        self.refresh_apps()
        event.acceptProposedAction()

    def load_layout(self):
        try:
            if os.path.exists("taskbar_layout.json"):
                with open("taskbar_layout.json", "r") as f:
                    return json.load(f)
        except: pass
        return []

    def save_layout(self):
        try:
            with open("taskbar_layout.json", "w") as f:
                json.dump(self.visual_order, f)
        except: pass

    def poll_active_app(self):
        # Update tracker logic - will automatically skip taskbar
        from tracker import update_active_app
        update_active_app()

    def _setup_window(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - BAR_WIDTH) // 2
        y = TASKBAR_Y_OFFSET
        
        self.setWindowTitle(OWN_WINDOW_TITLE)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # Initial geometry (Restored state)
        self.setGeometry(x, y, BAR_WIDTH, 72)
        self.main_container.setGeometry(0, 0, BAR_WIDTH, 60)
        
        # Position dot at top center
        self.min_dot.move(int((BAR_WIDTH - 46) / 2), 8)

    def _setup_layout(self):
        # Step 2: Single Main Layout
        self.main_layout = QHBoxLayout(self.main_container)
        self.main_layout.setContentsMargins(16, 0, 16, 0)
        self.main_layout.setSpacing(10)
        
        # Step 3: App Icon Section
        self.icons_layout = QHBoxLayout()
        self.icons_layout.setSpacing(12)
        self.main_layout.addLayout(self.icons_layout)
        
        # Step 4: Push Controls to Right
        self.main_layout.addStretch()
        
        # Step 5: Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setStyleSheet("background: rgba(255,255,255,40); max-width: 1px;")
        divider.setFixedHeight(34)
        self.main_layout.addWidget(divider)

        # Step 7 & 8: Control Buttons Style & Size
        BTN_STYLE = """
            QPushButton {
                background: rgba(255, 255, 255, 25);
                border: none;
                border-radius: 20px;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 55);
            }
        """
        
        # Minimize
        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(40, 40)
        self.min_btn.setStyleSheet(BTN_STYLE)
        self.min_btn.clicked.connect(self.minimize_taskbar)
        
        # Close
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(40, 40)
        self.close_btn.setStyleSheet("background: rgba(255, 70, 70, 180); border-radius: 20px; color: white; border: none;")
        self.close_btn.clicked.connect(QApplication.quit)
        
        # Step 9: Add to same main layout
        self.main_layout.addWidget(self.min_btn)
        self.main_layout.addWidget(self.close_btn)

    def refresh_apps(self):
        from tracker import get_running_apps
        from icons import IconManager
        from PyQt5.QtGui import QPixmapCache
        
        apps = get_running_apps()
        
        # 1. Update visual_order
        for key in apps.keys():
            if key not in self.visual_order:
                self.visual_order.append(key)
        self.visual_order = [k for k in self.visual_order if k in apps]
        
        # 2. AGGRESSIVE REBUILD (Prevention of icon inheritance)
        # Clear existing layout items
        while self.icons_layout.count():
            item = self.icons_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()

        # Clear Widget Tracking & Cache
        self._widgets.clear()
        QPixmapCache.clear()

        # 3. Recreate ALL Widgets (Fresh state every cycle)
        for i, key in enumerate(self.visual_order):
            info = apps[key]
            # Always get fresh pixmap from manager
            pix = IconManager.get_app_icon(key, info.exe_path, info.best_hwnd())
            
            # Create fresh widget
            w = AppIconWidget(key, info.pid, pix, self)
            w.update_state(info.state)
            w.switch_requested.connect(self._on_switch_app)
            
            self._widgets[key] = w
            w.show()
            self.icons_layout.insertWidget(i, w)

        self.update()

    def _on_switch_app(self, app_key: str):
        from tracker import get_running_apps, get_active_app_key
        # Get latest window list
        apps = get_running_apps()
        active_app_key = get_active_app_key()
        
        for info in apps.values():
            if info.app_key == app_key:
                # Direct Native State Toggle with Identity Comparison
                self._switcher.toggle_window(info.best_hwnd(), app_key, active_app_key)
                break

    # Step 5 & 6: Transition Logic
    # Step 4: MINIMIZE FUNCTION
    def minimize_taskbar(self):
        if self.is_minimized: return
        self.is_minimized = True
        
        # Hide main content and show capsule dot
        self.main_container.hide()
        self.min_dot.show()
        
        # Shrink window height to capsule size
        self.setFixedHeight(34)

    # Step 5: RESTORE FUNCTION
    def restore_taskbar(self):
        if not self.is_minimized: return
        self.is_minimized = False
        
        self.min_dot.hide()
        self.main_container.show()
        
        # Restore full taskbar height
        self.setFixedHeight(72)
        self.raise_()
        self.activateWindow()

    def paintEvent(self, event):
        # Background is now handled by stylesheet for stability
        pass

    def ensure_topmost(self):
        try:
            hwnd = int(self.winId())
            import win32con
            # Use HWND_TOPMOST without raise_()
            ctypes.windll.user32.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 1|2|16)
        except: pass
