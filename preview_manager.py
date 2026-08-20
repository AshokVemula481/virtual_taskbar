import win32gui
import win32con
import win32ui
import ctypes
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QSize, QTimer, QPoint
from PyQt5.QtGui import QColor, QPainter, QBrush, QPixmap, QImage, QFont

class PreviewWidget(QWidget):
    """
    Floating Thumbnail Preview Widget.
    Isolated from main taskbar logic for stability.
    """
    def __init__(self, parent=None):
        super().__init__(None) # Independent window
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.target_hwnd = 0
        self.app_name = ""
        
        # UI Setup
        self.setFixedSize(220, 160)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        self.title_label = QLabel(self)
        self.title_label.setStyleSheet("color: white; font-weight: bold; font-family: 'Segoe UI', sans-serif; font-size: 11px;")
        self.layout.addWidget(self.title_label)
        
        self.image_label = QLabel(self)
        self.image_label.setFixedSize(200, 120)
        self.image_label.setStyleSheet("background: rgba(0,0,0,100); border-radius: 4px;")
        self.layout.addWidget(self.image_label)
        
    def set_target(self, hwnd: int, name: str):
        self.target_hwnd = hwnd
        self.app_name = name
        self.title_label.setText(name)
        self.refresh_preview()

    def refresh_preview(self):
        if not self.target_hwnd or not win32gui.IsWindow(self.target_hwnd):
            return

        try:
            # Native Window Capture logic (PrintWindow)
            left, top, right, bottom = win32gui.GetWindowRect(self.target_hwnd)
            w = right - left
            h = bottom - top
            
            if w <= 0 or h <= 0: return

            hwnd_dc = win32gui.GetWindowDC(self.target_hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
            save_dc.SelectObject(bitmap)
            
            # Use PrintWindow for modern compatibility (including UWP/Electron)
            # Flag 2 = PW_RENDERFULLCONTENT
            ctypes.windll.user32.PrintWindow(self.target_hwnd, save_dc.GetSafeHdc(), 2)
            
            bmpinfo = bitmap.GetInfo()
            bmpstr = bitmap.GetBitmapBits(True)
            
            img = QImage(bmpstr, bmpinfo['bmWidth'], bmpinfo['bmHeight'], QImage.Format_ARGB32_Premultiplied)
            pix = QPixmap.fromImage(img)
            
            # Cleanup
            win32gui.ReleaseDC(self.target_hwnd, hwnd_dc)
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.DeleteObject(bitmap.GetHandle())
            
            # Scale and display
            scaled_pix = pix.scaled(200, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pix)
            self.image_label.setAlignment(Qt.AlignCenter)
            
        except Exception as e:
            # print(f"Preview Capture Failed: {e}")
            pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Match Taskbar Glassmorphism
        painter.setBrush(QBrush(QColor(20, 20, 20, 220)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)
        
        # Top accent line
        painter.setBrush(QBrush(QColor(0, 180, 255, 150)))
        painter.drawRoundedRect(0, 0, self.width(), 3, 1.5, 1.5)
