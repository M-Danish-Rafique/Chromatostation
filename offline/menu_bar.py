"""Menu bar creation and management"""
import tkinter as tk

class MenuBar:
    def __init__(self, root, open_org_callback, open_pdf_callback, 
                 report_preview_callback=None, report_print_callback=None,
                 signal_save_callback=None, signal_print_callback=None, signal_exit_callback=None):
        self.root = root
        self.open_org_callback = open_org_callback
        self.open_pdf_callback = open_pdf_callback
        self.report_preview_callback = report_preview_callback
        self.report_print_callback = report_print_callback
        self.signal_save_callback = signal_save_callback
        self.signal_print_callback = signal_print_callback
        self.signal_exit_callback = signal_exit_callback
        self.create_menu_bar()
    
    def create_menu_bar(self):
        menubar = tk.Menu(
            self.root,
            bg="#F9F9F9",
            tearoff=0,
            bd=2,
            activeborderwidth=0
        )
        self.root.config(menu=menubar)
        
        self._add_signal_menu(menubar)
        self._add_method_menu(menubar)
        self._add_clipboard_menu(menubar)
        self._add_integrate_menu(menubar)
        self._add_report_menu(menubar)
        self._add_compare_menu(menubar)
        self._add_calibration_menu(menubar)
        self._add_help_menu(menubar)
    
    def _new_menu(self, parent):
        return tk.Menu(
            parent,
            tearoff=0,
            bg="#F9F9F9",
            activebackground="#F0F0F0",
            bd=1,
            relief="solid",
            activeforeground="black",
            foreground="black"
        )
    
    def _add_item(self, menu, label, **kwargs):
        menu.add_command(
            label=label,
            activebackground="#F0F0F0",
            background="#F9F9F9",
            compound="left",
            **kwargs
        )
    
    def _add_signal_menu(self, menubar):
        signal_menu = self._new_menu(menubar)
        menubar.add_cascade(label="Signal", menu=signal_menu)
        
        send_to_menu = self._new_menu(signal_menu)
        self._add_item(send_to_menu, "Bitmap File")
        self._add_item(send_to_menu, "Bitmap Clipboard")
        self._add_item(send_to_menu, "Vector Clipboard")
        self._add_item(send_to_menu, "Text File")
        
        # Open submenu for selecting ORG or PDF
        open_menu = self._new_menu(signal_menu)
        self._add_item(open_menu, "ORG File", command=self.open_org_callback)
        self._add_item(open_menu, "PDF File", command=self.open_pdf_callback)
        
        signal_menu.add_cascade(label="Open", menu=open_menu)
        self._add_item(signal_menu, "Save", 
                      command=self.signal_save_callback if self.signal_save_callback else None)
        signal_menu.add_separator()
        signal_menu.add_cascade(label="Send to ...", menu=send_to_menu)
        self._add_item(signal_menu, "Print",
                      command=self.signal_print_callback if self.signal_print_callback else None)
        signal_menu.add_separator()
        self._add_item(signal_menu, "Exit",
                      command=self.signal_exit_callback if self.signal_exit_callback else None)
    
    def _add_method_menu(self, menubar):
        method_menu = self._new_menu(menubar)
        menubar.add_cascade(label="Method", menu=method_menu)
        
        self._add_item(method_menu, "Load")
        self._add_item(method_menu, "Default")
        self._add_item(method_menu, "Save As")
    
    def _add_clipboard_menu(self, menubar):
        clipboard_menu = self._new_menu(menubar)
        menubar.add_cascade(label="Clipboard", menu=clipboard_menu)
        
        self._add_item(clipboard_menu, "Analytical Results")
        self._add_item(clipboard_menu, "Integration Table")
        self._add_item(clipboard_menu, "Time Table")
        self._add_item(clipboard_menu, "Ingredient Table")
    
    def _add_integrate_menu(self, menubar):
        integrate_menu = self._new_menu(menubar)
        menubar.add_cascade(label="Integrate", menu=integrate_menu)
        
        self._add_item(integrate_menu, "Auto")
        self._add_item(integrate_menu, "Manual")
        self._add_item(integrate_menu, "Record Manual Event")
        integrate_menu.add_separator()
        
        disabled_items = [
            "Draw Baseline", "Single Peak", "Overlapping/Merged Peaks",
            "Tailing Peak", "Change Start Time", "Change End Time",
            "Seperate Peaks", "Merge Peaks", "Add peaks", "Delete peaks",
            "Forward horizontal baseline", "Backward horizontal baseline",
            "Add negative peak", "Delete negative peak"
        ]
        
        for item in disabled_items:
            self._add_item(integrate_menu, item, state="disabled")
    
    def _add_report_menu(self, menubar):
        report_menu = self._new_menu(menubar)
        menubar.add_cascade(label="Report", menu=report_menu)
        
        self._add_item(report_menu, "Print", 
                      command=self.report_print_callback if self.report_print_callback else None)
        self._add_item(report_menu, "Preview",
                      command=self.report_preview_callback if self.report_preview_callback else None)
        report_menu.add_separator()
        self._add_item(report_menu, "Set Printer")
    
    def _add_compare_menu(self, menubar):
        compare_menu = self._new_menu(menubar)
        menubar.add_cascade(label="Compare", menu=compare_menu)
        
        self._add_item(compare_menu, "Open a new signal for comparison")
        self._add_item(compare_menu, "Set an Alignment Reference Point")
        self._add_item(compare_menu, "Align Multiple Signals")
        self._add_item(compare_menu, "Reset the Alignment of Signals")
        self._add_item(compare_menu, "Add Signals")
        self._add_item(compare_menu, "Subtract Signals")
        self._add_item(compare_menu, "Append Signals")
        self._add_item(compare_menu, "Display Signals overlaid")
        self._add_item(compare_menu, "Display Signals Seperately", state="disabled")
        
        compare_send_to = self._new_menu(compare_menu)
        self._add_item(compare_send_to, "Bitmap File")
        self._add_item(compare_send_to, "Bitmap Clipboard")
        self._add_item(compare_send_to, "Vector Clipboard")
        
        compare_menu.add_cascade(label="Send to ...", menu=compare_send_to)
    
    def _add_calibration_menu(self, menubar):
        calibration_menu = self._new_menu(menubar)
        menubar.add_cascade(label="Calibration", menu=calibration_menu)
        
        self._add_item(calibration_menu, "Print Clib Curve")
        self._add_item(calibration_menu, "Save Curve")
        self._add_item(calibration_menu, "Clipboard")
    
    def _add_help_menu(self, menubar):
        help_menu = self._new_menu(menubar)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self._add_item(help_menu, "About")
        self._add_item(help_menu, "www.54pc.com")