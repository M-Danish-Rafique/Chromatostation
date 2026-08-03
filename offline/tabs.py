"""Tab creation and management"""
import tkinter as tk

class TabBar:
    def __init__(self, root, chromatogram_frame_creator, edit_report_frame_creator, edit_report_callback=None):
        """
        Initialize tab bar with frame creators (callables that return tk.Frame)
        and optional edit report callback
        """
        self.root = root
        self.tab_buttons = {}
        self.tab_frames = {}
        self.chromatogram_frame_creator = chromatogram_frame_creator
        self.edit_report_frame_creator = edit_report_frame_creator
        self.edit_report_callback = edit_report_callback
        self.active_tab = "Chromatogram"
        self.create_tabs()
    
    def create_tabs(self):
        """Create tab bar and content container"""
        # Tab button frame
        tab_frame = tk.Frame(self.root, relief=tk.FLAT, borderwidth=0, bg='#F0F0F0')
        tab_frame.pack(side=tk.TOP, fill=tk.X)
        
        tabs = [
            ("Chromatogram", self.on_chromatogram_click),
            ("Integration Method", None),
            ("Ingredient Table", None),
            ("Edit Report", self.on_edit_report_click),
            ("Graph Display", None),
            ("Compare Signals", None),
            ("Events Table", None)
        ]
        
        tab_font = ('Times New Roman', 11)
        
        for i, (tab_name, callback) in enumerate(tabs):
            btn_relief = tk.SUNKEN if i == 0 else tk.FLAT
            
            # Create button with tab switch callback
            cmd = callback if callback else lambda: None
            
            btn = tk.Button(
                tab_frame, text=tab_name, command=cmd,
                relief=btn_relief, padx=2, pady=0, borderwidth=2,
                font=tab_font, bg='#F0F0F0'
            )
            btn.pack(side=tk.LEFT, padx=0, pady=0)
            self.tab_buttons[tab_name] = btn
            
            # Separator
            sep = tk.Frame(tab_frame, width=2, bg="#F0F0F0")
            sep.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=1)
            tk.Frame(sep, width=1, bg="#A0A0A0").pack(side=tk.LEFT, fill=tk.Y)
            tk.Frame(sep, width=1, bg="#FDFDFD").pack(side=tk.LEFT, fill=tk.Y)
        
        # Content frame (will hold the actual tab content)
        self.content_frame = tk.Frame(self.root, bg='white')
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create frames for each tab
        self.tab_frames['Chromatogram'] = self.chromatogram_frame_creator(self.content_frame)
        self.tab_frames['Edit Report'] = self.edit_report_frame_creator(self.content_frame)
        
        # Show initial tab
        self.show_tab("Chromatogram")
    
    def on_chromatogram_click(self):
        """Handle Chromatogram tab click"""
        self.show_tab("Chromatogram")
    
    def on_edit_report_click(self):
        """Handle Edit Report tab click"""
        # Call the edit report callback if provided
        if self.edit_report_callback:
            self.edit_report_callback()
        self.show_tab("Edit Report")
    
    def show_tab(self, tab_name):
        """Show a specific tab and hide others"""
        # Hide all tabs
        for frame in self.tab_frames.values():
            frame.pack_forget()
        
        # Show selected tab
        if tab_name in self.tab_frames:
            self.tab_frames[tab_name].pack(fill=tk.BOTH, expand=True)
        
        # Update button appearance
        for name, btn in self.tab_buttons.items():
            if name == tab_name:
                btn.config(relief=tk.SUNKEN)
                self.active_tab = tab_name
            else:
                btn.config(relief=tk.FLAT)