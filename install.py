import os
import sys
import subprocess
import time
import datetime
import importlib

def log(msg, log_file):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    try:
        with open(log_file, "a") as f:
            f.write(formatted + "\n")
    except Exception as e:
        print(f"Failed to write to log file: {e}")

def check_python(log_file):
    version = sys.version
    log(f"Verifying Python... Installed version: {version}", log_file)
    return True

def check_dependencies(log_file):
    log("Verifying dependencies...", log_file)
    dependencies = {
        "PyQt5": "PyQt5",
        "pywin32": "win32com",
        "psutil": "psutil",
        "Pillow": "PIL",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "websockets": "websockets"
    }
    
    missing = []
    for name, module_name in dependencies.items():
        try:
            importlib.import_module(module_name)
            log(f"  - {name}: INSTALLED", log_file)
        except ImportError:
            log(f"  - {name}: MISSING", log_file)
            missing.append(name)
            
    if missing:
        log(f"Missing dependencies: {', '.join(missing)}. Attempting to install...", log_file)
        try:
            req_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
            if os.path.exists(req_path):
                # Run pip install
                res = subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path], 
                                     capture_output=True, text=True)
                if res.returncode == 0:
                    log("Successfully installed all missing dependencies via pip.", log_file)
                    return True
                else:
                    log(f"Failed to install dependencies via pip. Error: {res.stderr}", log_file)
                    return False
            else:
                log("requirements.txt not found. Cannot auto-install dependencies.", log_file)
                return False
        except Exception as e:
            log(f"Error while installing dependencies: {e}", log_file)
            return False
    return True

def create_shortcut(log_file):
    log("Creating startup shortcut...", log_file)
    try:
        installer_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "install_virtual_taskbar.py")
        res = subprocess.run([sys.executable, installer_script], capture_output=True, text=True)
        if res.returncode == 0:
            log("Startup shortcut created successfully.", log_file)
            log(res.stdout.strip(), log_file)
            return True
        else:
            log(f"Failed to create startup shortcut. Error: {res.stderr or res.stdout}", log_file)
            return False
    except Exception as e:
        log(f"Error while running shortcut creator: {e}", log_file)
        return False

def is_taskbar_running():
    try:
        import psutil
    except ImportError:
        return False
        
    pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = proc.info.get('cmdline')
            if cmd:
                is_python = 'python' in proc.info['name'].lower()
                has_main = any(os.path.basename(arg) == 'main.py' for arg in cmd)
                if is_python and has_main and proc.info['pid'] != pid:
                    return True
        except:
            pass
    return False

def test_launch(log_file):
    log("Test-launching Virtual Taskbar...", log_file)
    if is_taskbar_running():
        log("Virtual Taskbar is already running. Test launch verified (Startup safety works!).", log_file)
        return True
        
    vbs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VirtualTaskbar.vbs")
    log(f"Running startup VBScript file: {vbs_path}", log_file)
    try:
        subprocess.Popen(["wscript.exe", vbs_path])
        log("Process started in background. Waiting to verify...", log_file)
        time.sleep(3)
        if is_taskbar_running():
            log("SUCCESS: Virtual Taskbar is now running and verified.", log_file)
            return True
        else:
            log("FAILURE: Virtual Taskbar process not detected after launch.", log_file)
            return False
    except Exception as e:
        log(f"Error during test-launch: {e}", log_file)
        return False

def main():
    project_path = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(project_path, "install.log")
    
    # Reset log file
    try:
        with open(log_file, "w") as f:
            f.write(f"=== Virtual Taskbar Installation Log ===\n")
    except Exception as e:
        print(f"Could not open/write log file: {e}")
        
    log("Starting installation process...", log_file)
    
    py_ok = check_python(log_file)
    dep_ok = check_dependencies(log_file)
    shortcut_ok = create_shortcut(log_file)
    launch_ok = test_launch(log_file)
    
    if py_ok and dep_ok and shortcut_ok and launch_ok:
        log("=== INSTALLATION COMPLETED SUCCESSFULLY ===", log_file)
    else:
        log("=== INSTALLATION COMPLETED WITH ERRORS ===", log_file)

if __name__ == "__main__":
    main()
