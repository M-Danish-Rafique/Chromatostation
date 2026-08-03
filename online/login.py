import tkinter as tk
import os
from tkinter import messagebox
from functools import partial

class LoginWindow:
    """Professional old-school login screen for N2000 chromatostation."""
    
    # Hardcoded credentials (single user)
    VALID_USERNAME = "admin"
    VALID_PASSWORD = "password123"
    
    def __init__(self, root):
        self.root = root
        self.root.title("N2000 chromatostation - Login")
        self.root.geometry("380x320")
        self.root.resizable(False, False)
        
        # Set application icon
        icon_path = os.path.join(os.path.dirname(__file__), 'Resources', 'Icon.ico')
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                # Silently fail if icon can't be loaded (some systems may not support .ico)
                pass
        
        # Center window on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (190)
        y = (self.root.winfo_screenheight() // 2) - (160)
        self.root.geometry(f"380x320+{x}+{y}")
        
        self.authenticated = False
        self.create_ui()
        
    def setup_navigation(self, widgets):
        """Set up arrow key navigation for a list of widgets"""
        for i, widget in enumerate(widgets):
            if isinstance(widget, tk.Entry):
                widget.bind('<Up>', partial(self.move_focus, widgets, i, 'prev'))
                widget.bind('<Down>', partial(self.move_focus, widgets, i, 'next'))
                widget.bind('<Left>', partial(self.move_focus, widgets, i, 'prev'))
                widget.bind('<Right>', partial(self.move_focus, widgets, i, 'next'))

    def move_focus(self, widgets, current_i, direction, event):
        """Move focus to next or previous widget in the list"""
        if direction == 'next':
            next_i = (current_i + 1) % len(widgets)
        else:
            next_i = (current_i - 1) % len(widgets)
        widgets[next_i].focus_set()
        return 'break'
        
    def create_ui(self):
        """Build login form UI with old-school aesthetics."""
        
        # Main container with border
        main_frame = tk.Frame(self.root, bg="#F0F0F0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Title area
        title_frame = tk.Frame(main_frame, bg="#000080", height=80)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="N2000 chromatostation",
            font=("Arial", 18, "bold"),
            bg="#000080",
            fg="#FFFFFF"
        )
        title_label.pack(pady=(15, 2))
        
        subtitle_label = tk.Label(
            title_frame,
            text="Chromatography Data System",
            font=("Arial", 9),
            bg="#000080",
            fg="#C0C0C0"
        )
        subtitle_label.pack()
        
        # Form container
        form_frame = tk.Frame(main_frame, bg="#F0F0F0")
        form_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=35)
        
        # Username label and entry
        username_label = tk.Label(
            form_frame,
            text="Username:",
            font=("Arial", 10, "bold"),
            bg="#F0F0F0",
            anchor="w"
        )
        username_label.pack(fill=tk.X, pady=(0, 4))
        
        self.username_entry = tk.Entry(
            form_frame,
            font=("Times New Roman", 11),
            relief=tk.SUNKEN,
            bd=2
        )
        self.username_entry.pack(fill=tk.X, pady=(0, 12))
        self.username_entry.focus()
        
        # Password label and entry
        password_label = tk.Label(
            form_frame,
            text="Password:",
            font=("Arial", 10, "bold"),
            bg="#F0F0F0",
            anchor="w"
        )
        password_label.pack(fill=tk.X, pady=(0, 4))
        
        self.password_entry = tk.Entry(
            form_frame,
            font=("Times New Roman", 11),
            relief=tk.SUNKEN,
            bd=2,
            show="*"
        )
        self.password_entry.pack(fill=tk.X, pady=(0, 20))
        
        # Set up navigation
        self.setup_navigation([self.username_entry, self.password_entry])
        
        # Bind Enter key to login
        self.username_entry.bind("<Return>", lambda e: self.login())
        self.password_entry.bind("<Return>", lambda e: self.login())
        
        # Button frame
        button_frame = tk.Frame(form_frame, bg="#F0F0F0")
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        login_btn = tk.Button(
            button_frame,
            text="Login",
            font=("Arial", 11, "bold"),
            width=14,
            height=2,
            relief=tk.RAISED,
            bd=3,
            command=self.login,
            bg="#D4D4D4",
            activebackground="#C0C0C0",
            cursor="hand2"
        )
        login_btn.pack(side=tk.LEFT, padx=(0, 10), ipady=5)
        
        exit_btn = tk.Button(
            button_frame,
            text="Exit",
            font=("Arial", 11, "bold"),
            width=14,
            height=2,
            relief=tk.RAISED,
            bd=3,
            command=self.root.quit,
            bg="#D4D4D4",
            activebackground="#C0C0C0",
            cursor="hand2"
        )
        exit_btn.pack(side=tk.LEFT, ipady=5)
        
    def login(self):
        """Validate credentials and authenticate user."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if username == self.VALID_USERNAME and password == self.VALID_PASSWORD:
            self.authenticated = True
            self.root.destroy()
        else:
            messagebox.showerror(
                "Login Failed",
                "Invalid username or password.\n\nPlease try again.",
                parent=self.root
            )
            self.password_entry.delete(0, tk.END)
            self.username_entry.select_range(0, tk.END)
            self.username_entry.focus()