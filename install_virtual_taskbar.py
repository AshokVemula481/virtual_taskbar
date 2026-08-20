import os
import sys
import win32com.client

def create_startup_shortcut():
    project_path = os.path.dirname(os.path.abspath(__file__))
    vbs_path = os.path.join(project_path, "VirtualTaskbar.vbs")
    bat_path = os.path.join(project_path, "install_startup.bat")
    
    # 1. Clean up the old BAT file if it exists
    if os.path.exists(bat_path):
        try:
            os.remove(bat_path)
            print("Cleaned up old install_startup.bat")
        except Exception as e:
            print(f"Could not remove old BAT file: {e}")
            
    # 2. Dynamically create the VBScript launcher
    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{project_path}"
WshShell.Run "pythonw main.py", 0, False
'''
    try:
        with open(vbs_path, "w") as f:
            f.write(vbs_content)
        print(f"Created VBScript launcher: {vbs_path}")
    except Exception as e:
        print(f"Error creating VBScript launcher: {e}")
        sys.exit(1)
        
    # Path to shell:startup (Startup folder)
    startup_dir = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
    shortcut_path = os.path.join(startup_dir, "VirtualTaskbar.lnk")
    
    print(f"Target VBS file: {vbs_path}")
    print(f"Startup folder: {startup_dir}")
    print(f"Shortcut destination: {shortcut_path}")
    
    # Create the shortcut using WScript.Shell
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(shortcut_path)
        shortcut.TargetPath = "wscript.exe"
        shortcut.Arguments = f'"{vbs_path}"'
        shortcut.WorkingDirectory = project_path
        shortcut.WindowStyle = 7  # 7 = Minimized
        shortcut.Description = "Start Virtual Taskbar on Windows Login via VBScript"
        shortcut.save()
    except Exception as e:
        print(f"Error creating shortcut: {e}")
        sys.exit(1)
        
    # Verify the shortcut exists
    if os.path.exists(shortcut_path):
        print("Verification SUCCESS: Startup shortcut exists.")
        return True
    else:
        print("Verification FAILED: Startup shortcut does not exist.")
        sys.exit(1)

if __name__ == "__main__":
    create_startup_shortcut()
