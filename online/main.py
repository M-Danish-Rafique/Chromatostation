# main.py
import tkinter as tk
from login import LoginWindow
from app import ChromatographyApp

def main():
    # Show login screen first
    login_root = tk.Tk()
    login_window = LoginWindow(login_root)
    login_root.mainloop()
    
    # If authenticated, launch main app
    if login_window.authenticated:
        app_root = tk.Tk()
        app = ChromatographyApp(app_root)
        app_root.mainloop()

if __name__ == "__main__":
    main()