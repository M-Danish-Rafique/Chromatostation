"""Main application class"""
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
import tempfile
import shutil
from menu_bar import MenuBar
from toolbar import Toolbar
from tabs import TabBar
from chromatogram import ChromatogramViewer
from pdf_viewer import PDFViewer

try:
    from generators import PDFReportGenerator
except ImportError:
    PDFReportGenerator = None

class ChromatographyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("N2000 offline chromatostation")
        self.root.geometry("1400x800")
        self.root.state('zoomed')
        
        # Set application icon early (before other window operations) for better Windows compatibility
        from utils import resource_path
        icon_path = resource_path('Resources/Icon.ico')
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                # Silently fail if icon can't be loaded (some systems may not support .ico)
                pass
        
        # Store loaded ORG data
        self.org_data = None
        self.org_file_path = None
        self.generated_pdf_path = None
        self.current_pdf_path = None  # Track current PDF (generated or manually opened)
        self.temporary_files = set()  # Track temporary files for cleanup
        
        # Create menu bar with callbacks
        self.menu_bar = MenuBar(
            self.root,
            open_org_callback=self.open_org_file,
            open_pdf_callback=self.open_pdf_file,
            report_preview_callback=self.on_report_preview,
            report_print_callback=self.on_report_print,
            signal_save_callback=self.on_signal_save,
            signal_print_callback=self.on_signal_print,
            signal_exit_callback=self.on_signal_exit
        )
        
        # Create toolbars with callbacks
        self.toolbar = Toolbar(
            self.root,
            dummy_action_callback=self.dummy_action,
            open_callback=self.on_toolbar_open,
            load_callback=self.on_toolbar_load,
            save_callback=self.on_toolbar_save,
            save_as_callback=self.on_toolbar_save_as,
            print_callback=self.on_toolbar_print,
            preview_callback=self.on_toolbar_preview
        )
        
        # Create status bar
        self.create_status_bar()
        
        # Create tabs with frame creators and edit report callback
        self.tab_bar = TabBar(
            self.root,
            chromatogram_frame_creator=self.create_chromatogram_frame,
            edit_report_frame_creator=self.create_edit_report_frame,
            edit_report_callback=self.on_edit_report_tab_clicked
        )
        
        # Register cleanup handler for window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
            
    def create_chromatogram_frame(self, parent):
        """Create and return chromatogram frame"""
        self.chromatogram_viewer = ChromatogramViewer(parent)
        return self.chromatogram_viewer.frame
    
    def create_edit_report_frame(self, parent):
        """Create and return PDF viewer frame"""
        self.pdf_viewer = PDFViewer(parent)
        return self.pdf_viewer.frame
    
    def create_status_bar(self):
        status_frame = tk.Frame(self.root, relief=tk.SUNKEN, borderwidth=1, bg='#f0f0f0')
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        left_status = tk.Label(
            status_frame, text="",
            anchor=tk.W, padx=5,
            bg='#f0f0f0'
        )
        left_status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        right_status = tk.Label(
            status_frame, text="Zhejiang University, PRC.",
            anchor=tk.E, padx=5,
            bg='#f0f0f0'
        )
        right_status.pack(side=tk.RIGHT)
    
    def open_org_file(self):
        """Open ORG file and display chromatogram"""
        file_path = filedialog.askopenfilename(
            title="Open ORG File",
            filetypes=[("ORG Files", "*.org"), ("All Files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.org_data = json.load(f)
                self.org_file_path = file_path
                # Clean up old temporary PDF if it exists
                if self.generated_pdf_path and self.generated_pdf_path in self.temporary_files:
                    try:
                        if os.path.exists(self.generated_pdf_path):
                            os.remove(self.generated_pdf_path)
                        self.temporary_files.discard(self.generated_pdf_path)
                    except Exception:
                        pass  # Silently fail if can't delete
                # Reset generated PDF path when new ORG is loaded
                self.generated_pdf_path = None
                
                # Display chromatogram in Chromatogram tab
                self.chromatogram_viewer.load_org_data(self.org_data)
                
                # Switch to Chromatogram tab
                self.tab_bar.show_tab("Chromatogram")
                
                messagebox.showinfo("Success", "ORG file loaded successfully.\nChromatogram displayed in Chromatogram tab.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load ORG file:\n{str(e)}")
    
    def open_pdf_file(self):
        """Open PDF file and switch to Edit Report tab"""
        file_path = filedialog.askopenfilename(
            title="Open PDF File",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        
        if file_path:
            try:
                self.pdf_viewer.load_pdf_file(file_path)
                self.current_pdf_path = file_path
                self.generated_pdf_path = None  # Clear generated PDF flag if manually opened
                self.tab_bar.show_tab("Edit Report")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load PDF file:\n{str(e)}")
    
    def on_edit_report_tab_clicked(self):
        """
        Handle Edit Report tab click.
        If ORG data is loaded and no PDF has been generated yet, generate it from ORG.
        """
        if self.org_data and not self.generated_pdf_path:
            try:
                self.generate_pdf_from_org()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate PDF from ORG:\n{str(e)}")
    
    def generate_pdf_from_org(self):
        """Generate PDF from loaded ORG data and display it"""
        if not self.org_data:
            return  # No ORG data to process
        
        if PDFReportGenerator is None:
            messagebox.showerror("Error", "PDF generator not available. Make sure generators module is accessible.")
            return
        
        try:
            # Extract data from ORG
            sample_info = self.org_data.get('sample_info', {})
            method_data = self.org_data.get('method_data', {})
            chromatogram = self.org_data.get('chromatogram', {})
            results = self.org_data.get('results', [])
            
            # Convert chromatogram data to required format
            import numpy as np
            import pandas as pd
            
            time_array = np.array(chromatogram.get('time', []))
            signal_array = np.array(chromatogram.get('signal', []))
            peaks = chromatogram.get('peaks', [])
            
            chromatogram_data = (time_array, signal_array, peaks)
            
            # Convert results to DataFrame
            results_table = pd.DataFrame(results) if results else pd.DataFrame()
            
            # Generate temporary PDF file
            temp_pdf = os.path.join(tempfile.gettempdir(), 'temp_chromatogram.pdf')
            
            # Call PDF generator
            PDFReportGenerator.generate_pdf(
                temp_pdf,
                method_data,
                sample_info,
                peaks,
                chromatogram_data,
                results_table
            )
            
            # Mark that we've generated a PDF and load it for display
            self.generated_pdf_path = temp_pdf
            self.current_pdf_path = temp_pdf
            self.temporary_files.add(temp_pdf)  # Track for cleanup
            self.pdf_viewer.load_pdf_file(temp_pdf)
            
        except Exception as e:
            # Log the detailed error
            import traceback
            error_msg = f"Failed to generate PDF from ORG:\n{str(e)}\n\n{traceback.format_exc()}"
            messagebox.showerror("Error", error_msg)
    
    def dummy_action(self):
        """Placeholder action"""
        pass
    
    def get_active_tab(self):
        """Get the currently active tab name"""
        return self.tab_bar.active_tab
    
    def on_toolbar_open(self):
        """Handle Open button click - behavior depends on active tab"""
        active_tab = self.get_active_tab()
        if active_tab == "Chromatogram":
            self.open_org_file()
        elif active_tab == "Edit Report":
            self.open_pdf_file()
    
    def on_toolbar_load(self):
        """Handle Load button click - behavior depends on active tab"""
        active_tab = self.get_active_tab()
        if active_tab == "Chromatogram":
            self.open_org_file()
        elif active_tab == "Edit Report":
            self.open_pdf_file()
    
    def on_toolbar_save(self):
        """Handle Save button click - behavior depends on active tab"""
        active_tab = self.get_active_tab()
        if active_tab == "Chromatogram":
            if self.org_data and self.org_file_path:
                # Save to current file path
                self.save_org_file(self.org_file_path)
            elif self.org_data:
                # No current path, ask for save location
                self.save_org_file_as()
        elif active_tab == "Edit Report":
            if self.current_pdf_path:
                self.save_pdf_file(self.current_pdf_path)
    
    def on_toolbar_save_as(self):
        """Handle Save As button click - behavior depends on active tab"""
        active_tab = self.get_active_tab()
        if active_tab == "Chromatogram":
            if self.org_data:
                self.save_org_file_as()
        elif active_tab == "Edit Report":
            if self.current_pdf_path:
                self.save_pdf_file_as()
    
    def on_toolbar_print(self):
        """Handle Print button click - saves PDF if on Edit Report tab"""
        active_tab = self.get_active_tab()
        if active_tab == "Edit Report":
            if self.current_pdf_path:
                self.save_pdf_file_as()
    
    def on_toolbar_preview(self):
        """Handle Preview button click - switches to Edit Report tab"""
        active_tab = self.get_active_tab()
        if active_tab == "Chromatogram":
            # Switch to Edit Report tab (will trigger PDF generation if needed)
            self.tab_bar.on_edit_report_click()
    
    def save_org_file(self, file_path):
        """Save ORG data to specified file path"""
        if not self.org_data:
            messagebox.showwarning("Warning", "No ORG data to save")
            return False
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.org_data, f, indent=2, ensure_ascii=False)
            self.org_file_path = file_path
            messagebox.showinfo("Success", f"ORG file saved successfully:\n{file_path}")
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save ORG file:\n{str(e)}")
            return False
    
    def save_org_file_as(self):
        """Save ORG data with file dialog"""
        if not self.org_data:
            messagebox.showwarning("Warning", "No ORG data to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save ORG File As",
            defaultextension=".org",
            filetypes=[("ORG Files", "*.org"), ("All Files", "*.*")]
        )
        
        if file_path:
            self.save_org_file(file_path)
    
    def save_pdf_file(self, file_path):
        """Save PDF file to specified path (copy current PDF)"""
        if not self.current_pdf_path or not os.path.exists(self.current_pdf_path):
            messagebox.showwarning("Warning", "No PDF file to save")
            return False
        
        try:
            shutil.copy2(self.current_pdf_path, file_path)
            self.current_pdf_path = file_path
            # Note: Don't remove temp file from tracking yet - we'll clean it up on exit
            messagebox.showinfo("Success", f"PDF file saved successfully:\n{file_path}")
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PDF file:\n{str(e)}")
            return False
    
    def save_pdf_file_as(self):
        """Save PDF file with file dialog"""
        if not self.current_pdf_path or not os.path.exists(self.current_pdf_path):
            messagebox.showwarning("Warning", "No PDF file to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save PDF File As",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        
        if file_path:
            self.save_pdf_file(file_path)
            # Reload PDF viewer with new path
            self.pdf_viewer.load_pdf_file(file_path)
    
    def on_report_preview(self):
        """Handle Report -> Preview menu item"""
        active_tab = self.get_active_tab()
        if active_tab == "Chromatogram":
            # Switch to Edit Report tab (will trigger PDF generation if needed)
            self.tab_bar.on_edit_report_click()
    
    def on_report_print(self):
        """Handle Report -> Print menu item"""
        active_tab = self.get_active_tab()
        if active_tab == "Edit Report":
            if self.current_pdf_path:
                self.save_pdf_file_as()
            else:
                messagebox.showwarning("Warning", "No PDF file is currently open")
    
    def on_signal_save(self):
        """Handle Signal -> Save menu item"""
        active_tab = self.get_active_tab()
        if active_tab == "Chromatogram":
            if self.org_data and self.org_file_path:
                # Save to current file path
                self.save_org_file(self.org_file_path)
            elif self.org_data:
                # No current path, ask for save location
                self.save_org_file_as()
            else:
                messagebox.showwarning("Warning", "No ORG file is currently open")
        elif active_tab == "Edit Report":
            if self.current_pdf_path:
                self.save_pdf_file(self.current_pdf_path)
            else:
                messagebox.showwarning("Warning", "No PDF file is currently open")
    
    def on_signal_print(self):
        """Handle Signal -> Print menu item"""
        active_tab = self.get_active_tab()
        if active_tab == "Edit Report":
            if self.current_pdf_path:
                self.save_pdf_file_as()
            else:
                messagebox.showwarning("Warning", "No PDF file is currently open")
    
    def cleanup_temporary_files(self):
        """Clean up all temporary files created by the application"""
        for temp_file in list(self.temporary_files):
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                # Silently fail if file can't be deleted (might be in use)
                # Could log this in production but for now we'll just continue
                pass
    
    def on_window_close(self):
        """Handle window close event - cleanup and exit"""
        self.cleanup_temporary_files()
        self.root.quit()
        self.root.destroy()
    
    def on_signal_exit(self):
        """Handle Signal -> Exit menu item - closes the application"""
        self.cleanup_temporary_files()
        self.root.quit()
        self.root.destroy()