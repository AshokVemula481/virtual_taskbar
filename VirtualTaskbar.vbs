Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "c:\Users\Lenovo\OneDrive\Documents\Desktop\virtual taskbar"
WshShell.Run "pythonw main.py", 0, False
