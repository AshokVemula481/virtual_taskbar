# Virtual Floating Taskbar for Windows

A sleek, lightweight, and modern floating virtual taskbar for Windows built with Python and PyQt5.

## ✨ Features

- **Live Window Tracking**: Automatically tracks and displays open Win32 and UWP applications with their native icons.
- **Glassmorphic Floating UI**: Modern semi-transparent dark UI with smooth hover animations and active indicators.
- **Live Window Previews**: DWM-powered live thumbnail previews on hover.
- **Window Switching & Management**: Left-click to switch/restore windows, minimize, or close.
- **Drag & Reorder**: Reorder pinned and active application icons dynamically with layout persistence (`taskbar_layout.json`).
- **Silent Background Execution**: Runs unobtrusively via VBScript background launcher.
- **Auto-Startup Support**: Automatic Windows startup shortcut setup.

## 🚀 Getting Started

### Prerequisites

- Windows 10 or Windows 11
- Python 3.9+

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/AshokVemula481/virtual_taskbar.git
   cd virtual_taskbar
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Run the automated installer to verify dependencies and set up the startup shortcut:
   ```bash
   python install.py
   ```

### Running the App

- **Direct Launch**:
  ```bash
  python main.py
  ```
- **Silent Background Launch**:
  Double-click `VirtualTaskbar.vbs` or run:
  ```bash
  wscript.exe VirtualTaskbar.vbs
  ```

## 📁 Project Structure

```
virtual_taskbar/
├── assets/                  # Application icons and custom assets
├── icons.py                 # Windows & UWP icon extraction and caching
├── install.py               # Dependency verification and installation script
├── install_virtual_taskbar.py # Windows startup shortcut creator
├── main.py                  # Main application entry point & singleton lock
├── overlay.py               # Taskbar overlay UI, animations, and event handling
├── preview_manager.py       # DWM live thumbnail preview manager
├── requirements.txt         # Python dependencies
├── switcher.py              # Window activation and switching logic
├── tracker.py               # Win32 window event tracking
└── VirtualTaskbar.vbs       # Silent background launcher
```

## 📄 License

MIT License
