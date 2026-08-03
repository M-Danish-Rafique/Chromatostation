"""Toolbar creation and management"""
import tkinter as tk
import os
from utils import load_image_with_ratio, _HAS_PIL, resource_path

class Toolbar:
    def __init__(self, root, dummy_action_callback=None, 
                 open_callback=None, load_callback=None,
                 save_callback=None, save_as_callback=None,
                 print_callback=None, preview_callback=None):
        self.root = root
        self.dummy_action_callback = dummy_action_callback or (lambda: None)
        self.open_callback = open_callback
        self.load_callback = load_callback
        self.save_callback = save_callback
        self.save_as_callback = save_as_callback
        self.print_callback = print_callback
        self.preview_callback = preview_callback
        self.toolbar_images = {}
        self.toolbar_active_images = {}
        self.button_toolbar_images = {}
        self.toolbar_buttons = {}  # Store button references
        self.create_toolbar()
        self.create_button_toolbar()
    
    def create_separator(self, parent, c1="#FFFFFF", c2="#F0F0F0", c3="#A0A0A0", **pack_opts):
        """Create a vertical 3px separator with gradient"""
        sep = tk.Frame(parent, width=3)
        sep.pack_propagate(False)
        sep.pack(
            side=pack_opts.pop("side", tk.LEFT),
            fill=pack_opts.pop("fill", tk.Y),
            **pack_opts
        )
        
        cols = []
        for _ in range(3):
            col = tk.Frame(sep, width=1)
            col.pack(side=tk.LEFT, fill=tk.Y)
            col.pack_propagate(False)
            cols.append(col)
        
        # Top row
        for col_index, color in enumerate([c1, c1, c3]):
            tk.Frame(cols[col_index], height=1, bg=color).pack(side=tk.TOP, fill=tk.X)
        
        # Middle
        for col_index, color in enumerate([c1, c2, c3]):
            tk.Frame(cols[col_index], bg=color).pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Bottom row
        for col_index, color in enumerate([c1, c3, c3]):
            tk.Frame(cols[col_index], height=1, bg=color).pack(side=tk.BOTTOM, fill=tk.X)
        
        return sep
    
    def create_toolbar(self):
        icons_dir = resource_path("Resources/Icons")
        
        # Separator under menu
        sep_frame = tk.Frame(self.root, height=1)
        sep_frame.pack(side=tk.TOP, fill=tk.X)
        tk.Frame(sep_frame, height=0.5, bg="#A0A0A0").pack(fill=tk.X)
        tk.Frame(sep_frame, height=0.5, bg="#FDFDFD").pack(fill=tk.X)
        
        toolbar_frame = tk.Frame(self.root, relief=tk.RAISED, borderwidth=0, bg='#f0f0f0')
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        
        self.create_separator(toolbar_frame, side=tk.LEFT, fill=tk.Y, padx=4, pady=2)
        
        groups = [
            ["Open.png", "Save.png"],
            ["Default.png", "Load.png", "Save as.png"],
            ["Auto.png", "Manual.png", "Record.png"],
            ["Print.png", "Preview.png"],
            ["Calendar.png", "Peak Info.png"]
        ]
        
        for group_idx, group in enumerate(groups):
            if group_idx > 0:
                sep = tk.Frame(toolbar_frame, width=2, bg="#f0f0f0")
                sep.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=2)
                tk.Frame(sep, width=1, bg="#A0A0A0").pack(side=tk.LEFT, fill=tk.Y)
                tk.Frame(sep, width=1, bg="#FDFDFD").pack(side=tk.LEFT, fill=tk.Y)
            
            for name in group:
                file_path = os.path.join(icons_dir, name)
                base, ext = os.path.splitext(name)
                active_file = f"{base}_Active{ext}"
                active_path = os.path.join(icons_dir, active_file)
                
                # Determine callback based on button name
                callback = self._get_button_callback(name)
                
                img = load_image_with_ratio(file_path, target_height=55)
                img_active = load_image_with_ratio(active_path, target_height=55) or img
                
                if img is None:
                    btn = tk.Button(toolbar_frame, text=base, command=callback,
                                    relief=tk.RAISED, padx=6, pady=4,
                                    font=('Times New Roman', 12), bg='#e8e8e8', borderwidth=1)
                    btn.pack(side=tk.LEFT, padx=3, pady=3)
                    self.toolbar_buttons[name] = btn
                    continue
                
                btn = tk.Button(toolbar_frame, image=img, command=callback,
                                relief=tk.FLAT, bg='#f0f0f0', borderwidth=0, highlightthickness=0)
                btn.pack(side=tk.LEFT, padx=3, pady=3)
                
                btn._img_normal = img
                btn._img_active = img_active
                self.toolbar_images[name] = img
                self.toolbar_active_images[name] = img_active
                self.toolbar_buttons[name] = btn
                
                def _on_enter(event, b=btn):
                    if getattr(b, "_img_active", None):
                        b.config(image=b._img_active)
                
                def _on_leave(event, b=btn):
                    if getattr(b, "_img_normal", None):
                        b.config(image=b._img_normal)
                
                btn.bind("<Enter>", _on_enter)
                btn.bind("<Leave>", _on_leave)
        
        # Separator under toolbar
        sep_frame = tk.Frame(self.root, height=1)
        sep_frame.pack(side=tk.TOP, fill=tk.X)
        tk.Frame(sep_frame, height=0.5, bg="#A0A0A0").pack(fill=tk.X)
        tk.Frame(sep_frame, height=0.5, bg="#FDFDFD").pack(fill=tk.X)
    
    def _get_button_callback(self, button_name):
        """Return appropriate callback based on button name"""
        if button_name == "Open.png":
            return self.open_callback or self.dummy_action_callback
        elif button_name == "Load.png":
            return self.load_callback or self.dummy_action_callback
        elif button_name == "Save.png":
            return self.save_callback or self.dummy_action_callback
        elif button_name == "Save as.png":
            return self.save_as_callback or self.dummy_action_callback
        elif button_name == "Print.png":
            return self.print_callback or self.dummy_action_callback
        elif button_name == "Preview.png":
            return self.preview_callback or self.dummy_action_callback
        else:
            return self.dummy_action_callback
    
    def create_button_toolbar(self):
        button_toolbar = tk.Frame(self.root, relief=tk.FLAT, borderwidth=0, bg='#f0f0f0', height=35)
        button_toolbar.pack(side=tk.TOP, fill=tk.X)
        
        self.create_separator(button_toolbar, side=tk.LEFT, fill=tk.Y, padx=4, pady=3)
        
        small_icons_dir = resource_path("Resources/Small Icons")
        
        groups = [
            list(range(1, 15)),
            list(range(15, 18)),
            list(range(18, 27))
        ]
        
        for group_idx, group in enumerate(groups):
            if group_idx > 0:
                sep = tk.Frame(button_toolbar, width=2, bg="#f0f0f0")
                sep.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=2)
                tk.Frame(sep, width=1, bg="#A0A0A0").pack(side=tk.LEFT, fill=tk.Y)
                tk.Frame(sep, width=1, bg="#FDFDFD").pack(side=tk.LEFT, fill=tk.Y)
            
            for num in group:
                file_path = os.path.join(small_icons_dir, f"{num}.png")
                img = load_image_with_ratio(file_path, target_height=22)
                
                if img is None:
                    btn = tk.Button(button_toolbar, text=str(num), command=self.dummy_action_callback,
                                    relief=tk.RAISED, padx=4, pady=2,
                                    font=('Times New Roman', 8), bg='#e8e8e8', borderwidth=1)
                    btn.pack(side=tk.LEFT, padx=0, pady=3)
                else:
                    btn = tk.Button(button_toolbar, image=img, command=self.dummy_action_callback,
                                    relief=tk.FLAT, bg='#e8e8e8', borderwidth=0, highlightthickness=0)
                    btn.pack(side=tk.LEFT, padx=0, pady=3)
                    btn._img = img
                    self.button_toolbar_images[f"{num}.png"] = img
        
        # Separator under button toolbar
        sep_frame = tk.Frame(self.root, height=1)
        sep_frame.pack(side=tk.TOP, fill=tk.X)
        tk.Frame(sep_frame, height=0.5, bg="#A0A0A0").pack(fill=tk.X)
        tk.Frame(sep_frame, height=0.5, bg="#FDFDFD").pack(fill=tk.X)