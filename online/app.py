# app.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
import json
import pickle
import pandas as pd
from functools import partial

from method_manager import MethodManager
from batch_processor import BatchProcessor
from utils import resource_path
from audit_report import create_professional_audit_pdf

try:
    from tkcalendar import DateEntry
    _HAS_TKCAL = True
except Exception:
    DateEntry = None
    _HAS_TKCAL = False

try:
    from PIL import Image, ImageTk
    _HAS_PIL = True
except Exception:
    Image = None
    ImageTk = None
    _HAS_PIL = False

class ChromatographyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("N2000 online chromatostation")
        self.root.geometry("1400x800")
        try:
            self.root.state("zoomed")
        except Exception:
            pass
        
        # Set application icon
        icon_path = resource_path(os.path.join("Resources", "Icon.ico"))
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                # Silently fail if icon can't be loaded (some systems may not support .ico)
                pass

        self.current_method_path = None
        self.peak_entries = []

        self.create_menu_bar()
        self.create_toolbar()
        self.create_tabs()

    # --- Audit trail helpers (support legacy + streaming formats) ------------
    def _iter_audit_entries(self):
        """
        Yield audit entries from `_internal/audit_data/audit.trl`.

        Supports:
        - Legacy format: single pickled list of entries
        - Streaming format: append-only pickle stream of entry dicts
        """
        audit_dir = os.path.join('_internal', 'audit_data')
        audit_file = os.path.join(audit_dir, 'audit.trl')
        if not os.path.exists(audit_file):
            return

        try:
            with open(audit_file, 'rb') as f:
                try:
                    first = pickle.load(f)
                except EOFError:
                    return

                # Legacy: a single pickled list
                if isinstance(first, list):
                    for entry in first:
                        if isinstance(entry, dict):
                            yield entry
                    return

                # Streaming: first is already an entry
                if isinstance(first, dict):
                    yield first

                while True:
                    try:
                        entry = pickle.load(f)
                    except EOFError:
                        break
                    except Exception:
                        # Corruption: stop scanning to avoid infinite loops
                        break
                    if isinstance(entry, dict):
                        yield entry
        except Exception:
            return

    def create_menu_bar(self):
        menubar = tk.Menu(
            self.root,
            bg="#F9F9F9",
            tearoff=0,
            bd=2,
            activeborderwidth=0
        )
        self.root.config(menu=menubar)

        # Helper: creates a menu with improved padding & border color
        def new_menu(parent):
            return tk.Menu(
                parent,
                tearoff=0,
                bg="#F9F9F9",
                activebackground="#F0F0F0",
                bd=1,
                relief="solid",
                activeforeground="black",
                foreground="black",
            )

        # Helper to add menu items
        def add_item(menu, label, **kwargs):
            menu.add_command(
                label=label,
                activebackground="#F0F0F0",
                background="#F9F9F9",
                compound="left",
                **kwargs
            )

        # ----------------------------------------------------------------------
        # SIGNAL
        # ----------------------------------------------------------------------
        signal_menu = new_menu(menubar)
        menubar.add_cascade(label="Signal", menu=signal_menu)

        send_to_menu = new_menu(signal_menu)
        add_item(send_to_menu, "Bitmap File")
        add_item(send_to_menu, "Bitmap Clipboard")
        add_item(send_to_menu, "Vector Clipboard")
        add_item(send_to_menu, "Text File")

        add_item(signal_menu, "Open", command=self.load_method)
        add_item(signal_menu, "Save", command=self.save_method)
        signal_menu.add_separator()
        signal_menu.add_cascade(label="Send to ...", menu=send_to_menu)
        add_item(signal_menu, "Print")
        signal_menu.add_separator()
        add_item(signal_menu, "Exit", command=self.on_signal_exit)

        # ----------------------------------------------------------------------
        # METHOD
        # ----------------------------------------------------------------------
        method_menu = new_menu(menubar)
        menubar.add_cascade(label="Method", menu=method_menu)

        # Bind Load/Open and Save As to our handlers
        add_item(method_menu, "Load", command=self.load_method)
        add_item(method_menu, "Default")
        add_item(method_menu, "Save As", command=self.save_method)

        # ----------------------------------------------------------------------
        # CLIPBOARD
        # ----------------------------------------------------------------------
        clipboard_menu = new_menu(menubar)
        menubar.add_cascade(label="Clipboard", menu=clipboard_menu)

        add_item(clipboard_menu, "Analytical Results")
        add_item(clipboard_menu, "Integration Table")
        add_item(clipboard_menu, "Time Table")
        add_item(clipboard_menu, "Ingredient Table")

        # ----------------------------------------------------------------------
        # INTEGRATE
        # ----------------------------------------------------------------------
        integrate_menu = new_menu(menubar)
        menubar.add_cascade(label="Integrate", menu=integrate_menu)

        add_item(integrate_menu, "Auto")
        add_item(integrate_menu, "Manual")
        add_item(integrate_menu, "Record Manual Event")
        integrate_menu.add_separator()

        disabled_items = [
            "Draw Baseline",
            "Single Peak",
            "Overlapping/Merged Peaks",
            "Tailing Peak",
            "Change Start Time",
            "Change End Time",
            "Seperate Peaks",
            "Merge Peaks",
            "Add peaks",
            "Delete peaks",
            "Forward horizontal baseline",
            "Backward horizontal baseline",
            "Add negative peak",
            "Delete negative peak"
        ]

        for item in disabled_items:
            add_item(integrate_menu, item, state="disabled")

        # ----------------------------------------------------------------------
        # REPORT
        # ----------------------------------------------------------------------
        report_menu = new_menu(menubar)
        menubar.add_cascade(label="Report", menu=report_menu)

        add_item(report_menu, "Print")
        add_item(report_menu, "Preview")
        report_menu.add_separator()
        add_item(report_menu, "Set Printer")

        # ----------------------------------------------------------------------
        # COMPARE
        # ----------------------------------------------------------------------
        compare_menu = new_menu(menubar)
        menubar.add_cascade(label="Compare", menu=compare_menu)

        add_item(compare_menu, "Open a new signal for comparison")
        add_item(compare_menu, "Set an Alignment Reference Point")
        add_item(compare_menu, "Align Multiple Signals")
        add_item(compare_menu, "Reset the Alignment of Signals")
        add_item(compare_menu, "Add Signals")
        add_item(compare_menu, "Subtract Signals")
        add_item(compare_menu, "Append Signals")
        add_item(compare_menu, "Display Signals overlaid")
        add_item(compare_menu, "Display Signals Seperately", state="disabled")

        compare_send_to = new_menu(compare_menu)
        add_item(compare_send_to, "Bitmap File")
        add_item(compare_send_to, "Bitmap Clipboard")
        add_item(compare_send_to, "Vector Clipboard")

        compare_menu.add_cascade(label="Send to ...", menu=compare_send_to)

        # ----------------------------------------------------------------------
        # CALIBRATION
        # ----------------------------------------------------------------------
        calibration_menu = new_menu(menubar)
        menubar.add_cascade(label="Calibration", menu=calibration_menu)

        add_item(calibration_menu, "Print Clib Curve")
        add_item(calibration_menu, "Save Curve")
        add_item(calibration_menu, "Clipboard")

        # ----------------------------------------------------------------------
        # HELP
        # ----------------------------------------------------------------------
        help_menu = new_menu(menubar)
        menubar.add_cascade(label="Help", menu=help_menu)

        add_item(help_menu, "About")
        add_item(help_menu, "www.54pc.com")

    def create_separator(self, parent, c1="#FFFFFF", c2="#F0F0F0", c3="#A0A0A0", **pack_opts):
        """
        Creates a vertical separator with width=3px and height based on parent.
        Pattern:
            Top row:       c1-c1-c3
            Middle rows:   c1-c2-c3  (repeated automatically)
            Bottom row:    c1-c3-c3
        """

        # Fixed 3px wide separator
        sep = tk.Frame(parent, width=3)
        sep.pack_propagate(False)
        sep.pack(
            side=pack_opts.pop("side", tk.LEFT),
            fill=pack_opts.pop("fill", tk.Y),
            **pack_opts
        )

        # Create 3 columns (each 1px wide)
        cols = []
        for _ in range(3):
            col = tk.Frame(sep, width=1)
            col.pack(side=tk.LEFT, fill=tk.Y)
            col.pack_propagate(False)
            cols.append(col)

        # ---- TOP ROW ----
        top = (c1, c1, c3)
        for col_index, color in enumerate(top):
            tk.Frame(
                cols[col_index],
                height=1,
                bg=color
            ).pack(side=tk.TOP, fill=tk.X)

        # ---- MIDDLE AREA (expands) ----
        middle = (c1, c2, c3)
        for col_index, color in enumerate(middle):
            tk.Frame(
                cols[col_index],
                bg=color
            ).pack(
                side=tk.TOP,
                fill=tk.BOTH,
                expand=True   # This takes all remaining height
            )

        # ---- BOTTOM ROW ----
        bottom = (c1, c3, c3)
        for col_index, color in enumerate(bottom):
            tk.Frame(
                cols[col_index],
                height=1,
                bg=color
            ).pack(side=tk.BOTTOM, fill=tk.X)

        return sep

    def create_toolbar(self):
        # directory for icons and line image
        icons_dir = resource_path(os.path.join("Resources", "Icons"))

        # --- Separator under menu bar ---
        sep_frame = tk.Frame(self.root, height=1)
        sep_frame.pack(side=tk.TOP, fill=tk.X)

        tk.Frame(sep_frame, height=0.5, bg="#A0A0A0").pack(fill=tk.X)
        tk.Frame(sep_frame, height=0.5, bg="#FDFDFD").pack(fill=tk.X)

        # Now create toolbar (buttons use full images from Icons/)
        toolbar_frame = tk.Frame(self.root, relief=tk.RAISED, borderwidth=0, bg='#f0f0f0')
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)

        # Add a vertical "start" separator inside the toolbar (dark then light)
        self.create_separator(toolbar_frame, side=tk.LEFT, fill=tk.Y, padx=4, pady=2)

        # Define groups
        groups = [
            ["Open.png", "Save.png"],  # Group 1
            ["Default.png", "Load.png", "Save as.png"],  # Group 2
            ["Auto.png", "Manual.png", "Record.png"],  # Group 3
            ["Print.png", "Preview.png"],  # Group 4
            ["Calendar.png", "Peak Info.png"]  # Group 5
        ]

        # Keep references so PhotoImage objects are not garbage collected
        self.toolbar_images = {}
        self.toolbar_active_images = {}

        def load_image_keep_ratio(path, target_height=55):
            if not os.path.exists(path):
                return None
            if _HAS_PIL:
                img = Image.open(path).convert("RGBA")
                w, h = img.size
                ratio = float(target_height) / float(h)
                new_w = max(1, int(w * ratio))
                try:
                    resample_filter = Image.Resampling.LANCZOS
                except AttributeError:
                    resample_filter = getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", Image.NEAREST))
                img = img.resize((new_w, target_height), resample_filter)
                return ImageTk.PhotoImage(img)
            else:
                try:
                    return tk.PhotoImage(file=path)
                except Exception:
                    return None

        for group_idx, group in enumerate(groups):
            # Add separator before each group (except the first)
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

                img = load_image_keep_ratio(file_path, target_height=55)
                img_active = load_image_keep_ratio(active_path, target_height=55) or img

                # Map toolbar buttons to appropriate commands
                button_command = self.dummy_action
                if name == "Open.png" or name == "Load.png":
                    button_command = self.load_method
                elif name == "Save.png" or name == "Save as.png":
                    button_command = self.save_method

                if img is None:
                    btn = tk.Button(toolbar_frame, text=base, command=button_command,
                                    relief=tk.RAISED, padx=6, pady=4,
                                    font=('Times New Roman', 12), bg='#e8e8e8', borderwidth=1)
                    btn.pack(side=tk.LEFT, padx=3, pady=3)
                    continue

                btn = tk.Button(toolbar_frame, image=img, command=button_command,
                                relief=tk.FLAT, bg='#f0f0f0', borderwidth=0, highlightthickness=0)
                btn.pack(side=tk.LEFT, padx=3, pady=3)

                btn._img_normal = img
                btn._img_active = img_active
                self.toolbar_images[name] = img
                self.toolbar_active_images[name] = img_active

                def _on_enter(event, b=btn):
                    if getattr(b, "_img_active", None):
                        b.config(image=b._img_active)

                def _on_leave(event, b=btn):
                    if getattr(b, "_img_normal", None):
                        b.config(image=b._img_normal)

                btn.bind("<Enter>", _on_enter)
                btn.bind("<Leave>", _on_leave)

        # --- Separator under toolbar ---
        sep_frame = tk.Frame(self.root, height=1)
        sep_frame.pack(side=tk.TOP, fill=tk.X)

        tk.Frame(sep_frame, height=0.5, bg="#A0A0A0").pack(fill=tk.X)
        tk.Frame(sep_frame, height=0.5, bg="#FDFDFD").pack(fill=tk.X)

    # -- Tabs --
    def create_tabs(self):
        tab_frame = tk.Frame(self.root, bg='#F0F0F0')
        tab_frame.pack(side=tk.TOP, fill=tk.X)

        tabs = ["Sample Info", "Method", "Acquire Data", "Audit Trail"]
        self.tabs = {}
        for i, t in enumerate(tabs):
            btn = tk.Button(tab_frame, text=t, command=lambda n=t: self.switch_tab(n),
                            relief=tk.SUNKEN if i == 0 else tk.FLAT, font=("Times New Roman", 11))
            btn.pack(side=tk.LEFT)
            self.tabs[t] = btn
            # small separator
            sep = tk.Frame(tab_frame, width=2, bg="#F0F0F0")
            sep.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=1)
            tk.Frame(sep, width=1, bg="#A0A0A0").pack(side=tk.LEFT, fill=tk.Y)
            tk.Frame(sep, width=1, bg="#FDFDFD").pack(side=tk.LEFT, fill=tk.Y)

        # main pane
        self.main_pane = tk.Frame(self.root)
        self.main_pane.pack(fill=tk.BOTH, expand=True)
        self.inner_border = tk.Frame(self.main_pane, relief='sunken', borderwidth=2)
        self.inner_border.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.content_frame = tk.Frame(self.inner_border)
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # create tab frames
        self.create_sample_info_tab()
        self.create_method_tab()
        self.create_acquire_tab()
        self.create_audit_tab()

        self.switch_tab("Sample Info")

    def switch_tab(self, name):
        for n, btn in self.tabs.items():
            btn.config(relief=tk.SUNKEN if n == name else tk.FLAT)
        for f in (self.sample_frame, self.method_frame, self.acquire_frame, self.audit_frame):
            f.pack_forget()
        if name == "Sample Info":
            self.sample_frame.pack(fill=tk.BOTH, expand=True)
        elif name == "Method":
            self.method_frame.pack(fill=tk.BOTH, expand=True)
        elif name == "Acquire Data":
            self.acquire_frame.pack(fill=tk.BOTH, expand=True)
        elif name == "Audit Trail":
            self.audit_frame.pack(fill=tk.BOTH, expand=True)
            self.update_selected_company()

    def setup_navigation(self, widgets):
        """Set up arrow key navigation for a list of widgets"""
        for i, widget in enumerate(widgets):
            if isinstance(widget, (tk.Entry, tk.Text, ttk.Combobox, tk.Spinbox)):
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

    def create_sample_info_tab(self):
        self.sample_frame = tk.Frame(self.content_frame)
        self.sample_frame.grid_rowconfigure(5, weight=1)
        self.sample_frame.grid_columnconfigure(1, weight=1)
        self.sample_frame.grid_columnconfigure(2, weight=2)

        font_lbl = ("Times New Roman", 12)
        font_ent = ("Times New Roman", 12)
        self.sample_entries = {}

        tk.Label(self.sample_frame, text="Project Name", font=font_lbl).grid(row=0, column=0, sticky="w", padx=10, pady=6)
        self.sample_entries["project_name"] = tk.Entry(self.sample_frame, font=font_ent, relief=tk.SUNKEN, bd=2)
        self.sample_entries["project_name"].grid(row=0, column=1, columnspan=2, sticky="ew", padx=10, pady=6)

        tk.Label(self.sample_frame, text="Analyst Name", font=font_lbl).grid(row=1, column=0, sticky="w", padx=10, pady=6)
        self.sample_entries["analyst"] = tk.Entry(self.sample_frame, font=font_ent, relief=tk.SUNKEN, bd=2)
        self.sample_entries["analyst"].grid(row=1, column=1, sticky="ew", padx=(10, 5), pady=6)

        # Date/time container
        datetime_container = tk.Frame(self.sample_frame, bg=self.sample_frame.cget("bg"))
        datetime_container.grid(row=1, column=2, sticky="ew", padx=10, pady=6)
        tk.Label(datetime_container, text="Date / Time", font=font_lbl, bg=self.sample_frame.cget("bg")).pack(side=tk.LEFT, padx=(0, 10))
        if _HAS_TKCAL and DateEntry is not None:
            self.sample_entries["date"] = DateEntry(datetime_container, font=font_ent, date_pattern="dd/mm/yyyy", relief=tk.SUNKEN, bd=2, width=12)
            self.sample_entries["date"].pack(side=tk.LEFT, padx=(0, 10))
            tf = tk.Frame(datetime_container, bg=self.sample_frame.cget("bg")); tf.pack(side=tk.LEFT)
            self.sample_entries["hour"] = tk.Spinbox(tf, from_=0, to=23, width=3, font=font_ent, format="%02.0f")
            self.sample_entries["hour"].pack(side=tk.LEFT)
            tk.Label(tf, text=":", font=font_lbl, bg=self.sample_frame.cget("bg")).pack(side=tk.LEFT)
            self.sample_entries["minute"] = tk.Spinbox(tf, from_=0, to=59, width=3, font=font_ent, format="%02.0f")
            self.sample_entries["minute"].pack(side=tk.LEFT)
        else:
            self.sample_entries["datetime"] = tk.Entry(datetime_container, font=font_ent, relief=tk.SUNKEN, bd=2)
            self.sample_entries["datetime"].pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.sample_entries["datetime"].insert(0, datetime.now().strftime("%d/%m/%Y %H:%M"))

        tk.Label(self.sample_frame, text="Company Name", font=font_lbl).grid(row=2, column=0, sticky="w", padx=10, pady=6)
        self.sample_entries["company"] = tk.Entry(self.sample_frame, font=font_ent, relief=tk.SUNKEN, bd=2)
        self.sample_entries["company"].grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=6)

        tk.Label(self.sample_frame, text="Current Method", font=font_lbl).grid(row=3, column=0, sticky="w", padx=10, pady=6)
        self.current_method_label = tk.Label(self.sample_frame, text="Default", font=font_ent, anchor="w", relief=tk.SUNKEN, bd=2, bg="#F0F0F0")
        self.current_method_label.grid(row=3, column=1, columnspan=2, sticky="ew", padx=10, pady=6)

        tk.Label(self.sample_frame, text="Sample Description", font=font_lbl).grid(row=4, column=0, sticky="nw", padx=10, pady=6)
        self.sample_description = tk.Text(self.sample_frame, font=font_ent, relief=tk.SUNKEN, bd=2, wrap="word")
        self.sample_description.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))

        tk.Button(self.sample_frame, text="Save Method", font=font_lbl, width=14, relief=tk.RAISED, bd=2, command=self.save_method).grid(row=6, column=2, sticky="e", padx=10, pady=10)

        # Set up navigation
        nav_widgets = [self.sample_entries["project_name"], self.sample_entries["analyst"]]
        if _HAS_TKCAL:
            nav_widgets.extend([self.sample_entries["date"], self.sample_entries["hour"], self.sample_entries["minute"]])
        else:
            nav_widgets.append(self.sample_entries["datetime"])
        nav_widgets.extend([self.sample_entries["company"], self.sample_description])
        self.setup_navigation(nav_widgets)

    def create_method_tab(self):
        self.method_frame = tk.Frame(self.content_frame)
        self.method_frame.grid_columnconfigure(1, weight=1)
        font_lbl = ("Times New Roman", 12)
        font_ent = ("Times New Roman", 12)
        style = ttk.Style()
        style.configure("TCombobox", font=font_ent)
        self.method_frame.option_add("*TCombobox*Listbox*Font", font_ent)
        self.method_fields = {}

        form = [
            ("Instrument Type", "instrument", ["LC", "GC"]),
            ("Model No", "model", None),
            ("Column Temperature (°C)", "column_temp", None),
            ("Column Part No", "column_part", None),
            ("Detector Type", "detector", ["UV", "Fluorescence", "ECD"]),
            ("Wavelength (nm)", "wavelength", None),
            ("Run Time (min)", "runtime", None),
            ("No of Peaks", "num_peaks", None),
        ]

        for row, (label, key, options) in enumerate(form):
            tk.Label(self.method_frame, text=label, font=font_lbl).grid(row=row, column=0, sticky="w", padx=10, pady=6)
            if options:
                var = tk.StringVar()
                box = ttk.Combobox(self.method_frame, values=options, textvariable=var, state="readonly", font=font_ent, style="TCombobox")
                box.grid(row=row, column=1, sticky="ew", padx=10, pady=6)
                self.method_fields[key] = var
            else:
                entry = tk.Entry(self.method_frame, font=font_ent, relief=tk.SUNKEN, bd=2, width=40)
                entry.grid(row=row, column=1, sticky="ew", padx=10, pady=6)
                self.method_fields[key] = entry

        # Configure Peaks button
        tk.Button(self.method_frame, text="Configure Peaks", font=font_lbl, width=16, relief=tk.RAISED, bd=2, command=self.configure_peaks_table).grid(row=row + 1, column=1, sticky="e", padx=10, pady=10)

        title_lbl = tk.Label(self.method_frame, text="Peak Configuration", font=("Times New Roman", 12, "bold"), anchor="nw")
        title_lbl.grid(row=row + 2, column=0, sticky="nw", padx=10, pady=(0, 6))

        self.peaks_table_container = tk.Frame(self.method_frame, relief="groove", bd=2, bg="#FFFFFF")
        self.peaks_table_container.grid(row=row + 2, column=1, sticky="nsew", padx=10, pady=(0, 10))
        self.method_frame.grid_rowconfigure(row + 2, weight=1)
        self.peaks_table_frame = None

        tk.Button(self.method_frame, text="Save Method", font=font_lbl, width=14, relief=tk.RAISED, bd=2, command=self.save_method).grid(row=row + 3, column=1, sticky="e", padx=10, pady=15)

        # Set up navigation
        self.setup_navigation(list(self.method_fields.values()))

    def configure_peaks_table(self):
        # Clear existing
        for w in self.peaks_table_container.winfo_children():
            w.destroy()
        self.peak_entries = []
        num_field = self.method_fields.get("num_peaks")
        if not num_field:
            return
        try:
            num_peaks = int(num_field.get())
            if num_peaks <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Invalid", "Please enter positive integer for No of Peaks")
            return

        font_lbl = ("Times New Roman", 12, "bold")
        font_ent = ("Times New Roman", 11)

        canvas = tk.Canvas(self.peaks_table_container, borderwidth=0, highlightthickness=0, bg=self.peaks_table_container.cget("bg"))
        v_scroll = tk.Scrollbar(self.peaks_table_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=v_scroll.set)
        scrollable = tk.Frame(canvas, bg=self.peaks_table_container.cget("bg"))
        win = canvas.create_window((0, 0), window=scrollable, anchor="nw")

        def on_c(e):
            canvas.itemconfigure(win, width=e.width)
        canvas.bind("<Configure>", on_c)
        def on_f(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        scrollable.bind("<Configure>", on_f)

        canvas.pack(side="left", fill="both", expand=True)

        headers = ["Peak #", "Peak Name", "Avg Retention Time (min)", "Tailing Factor", "Theoretical Plates (≥5000)"]
        widths = [8, 20, 25, 15, 25]
        for ci, w in enumerate(widths):
            scrollable.grid_columnconfigure(ci, weight=w)

        for col, (h, w) in enumerate(zip(headers, widths)):
            tk.Label(scrollable, text=h, font=font_lbl, relief=tk.RIDGE, bd=2, bg="#E0E0E0", width=w, anchor="center").grid(row=0, column=col, sticky="ew", padx=2, pady=2)

        for i in range(num_peaks):
            tk.Label(scrollable, text=str(i + 1), font=font_ent, relief=tk.SUNKEN, bd=1, bg="#F5F5F5", width=widths[0]).grid(row=i + 1, column=0, sticky="ew", padx=2, pady=2)
            e_name = tk.Entry(scrollable, font=font_ent, relief=tk.SUNKEN, bd=2); e_name.grid(row=i + 1, column=1, sticky="ew", padx=2, pady=2)
            e_rt = tk.Entry(scrollable, font=font_ent, relief=tk.SUNKEN, bd=2); e_rt.grid(row=i + 1, column=2, sticky="ew", padx=2, pady=2)
            e_tail = tk.Entry(scrollable, font=font_ent, relief=tk.SUNKEN, bd=2); e_tail.grid(row=i + 1, column=3, sticky="ew", padx=2, pady=2)
            e_plates = tk.Entry(scrollable, font=font_ent, relief=tk.SUNKEN, bd=2); e_plates.grid(row=i + 1, column=4, sticky="ew", padx=2, pady=2)
            self.peak_entries.append({
                'peak_name': e_name,
                'retention_time': e_rt,
                'tailing_factor': e_tail,
                'theoretical_plates': e_plates
            })

        self.peaks_table_container.update_idletasks()
        bbox = canvas.bbox("all")
        content_h = (bbox[3] - bbox[1]) if bbox else 0
        cont_h = self.peaks_table_container.winfo_height() or self.peaks_table_container.winfo_reqheight()
        if content_h > cont_h:
            v_scroll.pack(side="right", fill="y")
            canvas.config(height=cont_h)
        else:
            try:
                v_scroll.pack_forget()
            except Exception:
                pass
            canvas.config(height=max(80, content_h))

        # bind wheel to canvas only
        def on_wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind("<Enter>", lambda ev: canvas.focus_set())
        canvas.bind("<MouseWheel>", on_wheel)
        scrollable.bind("<MouseWheel>", on_wheel)

    def create_acquire_tab(self):
        self.acquire_frame = tk.Frame(self.content_frame)
        font_lbl = ("Times New Roman", 12)
        font_ent = ("Times New Roman", 12)

        input_group = tk.LabelFrame(self.acquire_frame, text="Input Files", font=("Times New Roman", 11, "bold"))
        input_group.pack(fill=tk.X, padx=12, pady=8)

        def make_browse_row(parent, label_text, browse_cmd, var_attr):
            row = tk.Frame(parent)
            row.pack(fill=tk.X, padx=8, pady=6)
            tk.Label(row, text=label_text, font=font_lbl, width=18, anchor="w").pack(side=tk.LEFT)
            ent = tk.Entry(row, font=font_ent, relief=tk.SUNKEN, bd=2)
            ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))
            btn = tk.Button(row, text="...", width=4, relief=tk.RIDGE, command=lambda e=ent: browse_cmd(e))
            btn.pack(side=tk.LEFT)
            setattr(self, var_attr, ent)

        def browse_method(entry_widget):
            path = filedialog.askopenfilename(filetypes=[("Method Files", "*.mtd"), ("JSON", "*.json"), ("All", "*.*")])
            if path:
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, path)
                self.current_method_path = path
                try:
                    md = MethodManager.load_method(path)
                    si = md.get('sample_info', {})
                    if 'project_name' in si and 'project_name' in self.sample_entries:
                        self.sample_entries['project_name'].delete(0, tk.END)
                        self.sample_entries['project_name'].insert(0, si.get('project_name', ''))
                    if 'analyst' in si and 'analyst' in self.sample_entries:
                        self.sample_entries['analyst'].delete(0, tk.END)
                        self.sample_entries['analyst'].insert(0, si.get('analyst', ''))
                    if 'company' in si and 'company' in self.sample_entries:
                        self.sample_entries['company'].delete(0, tk.END)
                        self.sample_entries['company'].insert(0, si.get('company', ''))
                except Exception:
                    pass

        def browse_excel(entry_widget):
            path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx;*.xls;*.csv"), ("All files", "*.*")])
            if path:
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, path)

        make_browse_row(input_group, "Method File (.mtd):", browse_method, "acq_method_entry")
        make_browse_row(input_group, "Excel File:", browse_excel, "acq_excel_entry")

        output_group = tk.LabelFrame(self.acquire_frame, text="Output Locations", font=("Times New Roman", 11, "bold"))
        output_group.pack(fill=tk.X, padx=12, pady=8)

        def browse_folder(entry_widget):
            path = filedialog.askdirectory()
            if path:
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, path)

        make_browse_row(output_group, "ORG Output Folder:", browse_folder, "acq_org_entry")
        make_browse_row(output_group, "PDF Output Folder:", browse_folder, "acq_pdf_entry")

        ctrl_frame = tk.Frame(self.acquire_frame)
        ctrl_frame.pack(fill=tk.X, padx=12, pady=12)

        self.acq_status_var = tk.StringVar(value="")
        tk.Label(ctrl_frame, textvariable=self.acq_status_var, font=font_ent, anchor="w")\
            .pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(ctrl_frame, text="Start Processing", font=font_lbl, width=16, command=self.start_processing)\
            .pack(side=tk.RIGHT, padx=10)

        # Set up navigation
        nav_widgets = [self.acq_method_entry, self.acq_excel_entry, self.acq_org_entry, self.acq_pdf_entry]
        self.setup_navigation(nav_widgets)

    def start_processing(self):
        method_path = self.acq_method_entry.get().strip()
        excel_path = self.acq_excel_entry.get().strip()
        org_dir = self.acq_org_entry.get().strip()
        pdf_dir = self.acq_pdf_entry.get().strip()

        if not method_path or not os.path.exists(method_path):
            messagebox.showerror("Missing Method", "Please select a valid .mtd method file.")
            return
        if not excel_path or not os.path.exists(excel_path):
            messagebox.showerror("Missing Excel", "Please select a valid Excel/CSV file.")
            return
        if not org_dir:
            messagebox.showerror("Missing ORG folder", "Please select ORG output folder.")
            return
        if not pdf_dir:
            messagebox.showerror("Missing PDF folder", "Please select PDF output folder.")
            return

        self.acq_status_var.set("Processing...")
        self.root.update_idletasks()

        try:
            success, errors = BatchProcessor.process_excel_file(
                excel_path, method_path, org_dir, pdf_dir,
                status_callback=lambda msg: self._update_status(msg)
            )
            if errors:
                self.acq_status_var.set(f"Completed with {len(errors)} errors.")
                messagebox.showwarning("Processing completed with errors", f"Processed {success} samples. Errors:\n" + "\n".join(errors))
            else:
                self.acq_status_var.set("Completed successfully.")
                messagebox.showinfo("Processing completed", f"Successfully processed {success} samples.")
        except Exception as e:
            self.acq_status_var.set(f"Critical error: {e}")
            messagebox.showerror("Processing failed", f"An unexpected error occurred: {e}")
        finally:
            self.acq_status_var.set("")

    def _update_status(self, msg):
        """Update the status label and force a UI refresh."""
        self.acq_status_var.set(msg)
        self.root.update_idletasks()

    def create_audit_tab(self):
        self.audit_frame = tk.Frame(self.content_frame)
        self.audit_frame.grid_columnconfigure(1, weight=1)
        
        font_lbl = ("Times New Roman", 12)
        font_ent = ("Times New Roman", 12)

        # Title section
        title_frame = tk.Frame(self.audit_frame)
        title_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(10, 15))
        tk.Label(title_frame, text="Audit Report Generator", 
                font=("Times New Roman", 14, "bold")).pack(anchor="w")
        
        # Company selection (read-only, shows selected company)
        tk.Label(self.audit_frame, text="Company:", font=font_lbl)\
            .grid(row=1, column=0, sticky="w", padx=12, pady=6)
        self.audit_company_var = tk.StringVar()
        self.audit_company_entry = tk.Entry(self.audit_frame, textvariable=self.audit_company_var, 
                                            font=font_ent, relief=tk.SUNKEN, bd=2, state="readonly")
        self.audit_company_entry.grid(row=1, column=1, sticky="ew", padx=12, pady=6)

        # Audit period frame
        period_frame = tk.LabelFrame(self.audit_frame, text="Audit Period", 
                                    font=("Times New Roman", 11, "bold"))
        period_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=12)
        period_frame.grid_columnconfigure(1, weight=1)

        # Start date/time
        tk.Label(period_frame, text="Start Date/Time:", font=font_lbl)\
            .grid(row=0, column=0, sticky="w", padx=10, pady=8)
        
        start_container = tk.Frame(period_frame)
        start_container.grid(row=0, column=1, sticky="ew", padx=10, pady=8)
        
        if _HAS_TKCAL and DateEntry is not None:
            self.audit_start_date = DateEntry(start_container, font=font_ent, 
                                             date_pattern="dd/mm/yyyy", relief=tk.SUNKEN, bd=2, width=12)
            self.audit_start_date.pack(side=tk.LEFT, padx=(0, 10))
            
            time_frame = tk.Frame(start_container)
            time_frame.pack(side=tk.LEFT)
            self.audit_start_hour = tk.Spinbox(time_frame, from_=0, to=23, width=3, 
                                              font=font_ent, format="%02.0f")
            self.audit_start_hour.pack(side=tk.LEFT)
            self.audit_start_hour.delete(0, tk.END)
            self.audit_start_hour.insert(0, "00")
            
            tk.Label(time_frame, text=":", font=font_lbl).pack(side=tk.LEFT)
            
            self.audit_start_minute = tk.Spinbox(time_frame, from_=0, to=59, width=3, 
                                                font=font_ent, format="%02.0f")
            self.audit_start_minute.pack(side=tk.LEFT)
            self.audit_start_minute.delete(0, tk.END)
            self.audit_start_minute.insert(0, "00")
        else:
            self.audit_start_datetime = tk.Entry(start_container, font=font_ent, relief=tk.SUNKEN, bd=2)
            self.audit_start_datetime.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.audit_start_datetime.insert(0, datetime.now().strftime("%d/%m/%Y %H:%M"))

        # End date/time
        tk.Label(period_frame, text="End Date/Time:", font=font_lbl)\
            .grid(row=1, column=0, sticky="w", padx=10, pady=8)
        
        end_container = tk.Frame(period_frame)
        end_container.grid(row=1, column=1, sticky="ew", padx=10, pady=8)
        
        if _HAS_TKCAL and DateEntry is not None:
            self.audit_end_date = DateEntry(end_container, font=font_ent, 
                                           date_pattern="dd/mm/yyyy", relief=tk.SUNKEN, bd=2, width=12)
            self.audit_end_date.pack(side=tk.LEFT, padx=(0, 10))
            
            time_frame = tk.Frame(end_container)
            time_frame.pack(side=tk.LEFT)
            self.audit_end_hour = tk.Spinbox(time_frame, from_=0, to=23, width=3, 
                                            font=font_ent, format="%02.0f")
            self.audit_end_hour.pack(side=tk.LEFT)
            self.audit_end_hour.delete(0, tk.END)
            self.audit_end_hour.insert(0, "23")
            
            tk.Label(time_frame, text=":", font=font_lbl).pack(side=tk.LEFT)
            
            self.audit_end_minute = tk.Spinbox(time_frame, from_=0, to=59, width=3, 
                                              font=font_ent, format="%02.0f")
            self.audit_end_minute.pack(side=tk.LEFT)
            self.audit_end_minute.delete(0, tk.END)
            self.audit_end_minute.insert(0, "59")
        else:
            self.audit_end_datetime = tk.Entry(end_container, font=font_ent, relief=tk.SUNKEN, bd=2)
            self.audit_end_datetime.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.audit_end_datetime.insert(0, datetime.now().strftime("%d/%m/%Y %H:%M"))

        # Output location
        tk.Label(self.audit_frame, text="Save PDF As:", font=font_lbl)\
            .grid(row=3, column=0, sticky="w", padx=12, pady=8)
        
        save_frame = tk.Frame(self.audit_frame)
        save_frame.grid(row=3, column=1, sticky="ew", padx=12, pady=8)
        
        self.audit_save_var = tk.StringVar()
        save_entry = tk.Entry(save_frame, textvariable=self.audit_save_var, 
                            font=font_ent, relief=tk.SUNKEN, bd=2)
        save_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(save_frame, text="...", width=4, relief=tk.RIDGE, 
                 command=self.browse_audit_save).pack(side=tk.LEFT)

        # Generate button
        btn_frame = tk.Frame(self.audit_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, sticky="e", padx=12, pady=20)
        tk.Button(btn_frame, text="Generate Audit PDF", font=font_lbl, width=20, 
                 relief=tk.RAISED, bd=2, command=self.generate_audit_pdf).pack()

        # Set up navigation
        nav_widgets = [self.audit_company_entry]
        if _HAS_TKCAL:
            nav_widgets.extend([self.audit_start_date, self.audit_start_hour, self.audit_start_minute, self.audit_end_date, self.audit_end_hour, self.audit_end_minute])
        else:
            nav_widgets.extend([self.audit_start_datetime, self.audit_end_datetime])
        nav_widgets.append(save_entry)
        self.setup_navigation(nav_widgets)

    def get_audit_data_path(self):
        """Get the path to the audit data directory inside _internal folder"""
        audit_dir = os.path.join('_internal', 'audit_data')
        os.makedirs(audit_dir, exist_ok=True)
        return audit_dir

    def update_selected_company(self):
        """Update the company field with the company having the highest number of occurrences"""
        from collections import Counter
        company_counts = Counter(
            entry.get('company_name', '')
            for entry in self._iter_audit_entries()
            if entry.get('company_name')
        )
        
        if not company_counts:
            self.audit_company_var.set("")
            return
        
        company = company_counts.most_common(1)[0][0]
        self.audit_company_var.set(company)

    def browse_audit_save(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if path:
            self.audit_save_var.set(path)

    def generate_audit_pdf(self):
        save_path = self.audit_save_var.get().strip()

        if not save_path:
            messagebox.showerror("Error", "Please specify a save location for the audit PDF.")
            return

        # Get dates and times
        try:
            if _HAS_TKCAL:
                start_date = self.audit_start_date.get_date()
                start_hour = int(self.audit_start_hour.get())
                start_minute = int(self.audit_start_minute.get())
                start_datetime = datetime.combine(start_date, datetime.min.time().replace(hour=start_hour, minute=start_minute))
                
                end_date = self.audit_end_date.get_date()
                end_hour = int(self.audit_end_hour.get())
                end_minute = int(self.audit_end_minute.get())
                end_datetime = datetime.combine(end_date, datetime.min.time().replace(hour=end_hour, minute=end_minute))
            else:
                start_datetime = datetime.strptime(self.audit_start_datetime.get().strip(), '%d/%m/%Y %H:%M')
                end_datetime = datetime.strptime(self.audit_end_datetime.get().strip(), '%d/%m/%Y %H:%M')
        except Exception as e:
            messagebox.showerror("Error", f"Invalid date/time format. {e}")
            return

        if start_datetime > end_datetime:
            messagebox.showerror("Error", "Start date/time cannot be after end date/time.")
            return

        # Load audit data (streaming-safe)
        audit_dir = self.get_audit_data_path()
        audit_file = os.path.join(audit_dir, 'audit.trl')
        if not os.path.exists(audit_file):
            # Log critical event
            syslog_file = os.path.join(audit_dir, '.syslog')
            try:
                with open(syslog_file, 'ab') as f:                    
                    event = f"[{datetime.now().isoformat()}] CRITICAL: Audit file missing or deleted\n"
                    f.write(event.encode('utf-8'))
            except Exception:
                pass
            messagebox.showerror("Error", "Audit file missing or deleted. This is a critical audit event.")
            return

        # Read entries without loading the entire file into memory
        entries = list(self._iter_audit_entries())
        if not entries:
            messagebox.showwarning("No Data", "No audit data found in the audit log.")
            return

        from collections import Counter
        company_counts = Counter(entry.get('company_name', '') for entry in entries if entry.get('company_name'))
        
        if not company_counts:
            messagebox.showwarning("No Data", "No audit data found in the audit log.")
            return
        
        # Select company with highest occurrences
        company = company_counts.most_common(1)[0][0]

        # Update the company field in UI
        self.audit_company_var.set(company)

        # Filter data by selected company and date/time range
        filtered = []
                
        for entry in entries:
            if entry['company_name'] == company:
                try:
                    # Parse the date string format: MM/DD/YYYY HH:MM:SS AM/PM PKT
                    date_str = entry['date_acquired'].replace(' PKT', '').strip()
                    acquired_datetime = datetime.strptime(date_str, '%d/%m/%Y %I:%M:%S %p')
                                                            
                    # Compare only date and time
                    if start_datetime <= acquired_datetime <= end_datetime:
                        filtered.append(entry)
                except Exception as e:
                    print(f"Error parsing date for entry: {e}, date_str: {entry.get('date_acquired', 'N/A')}")
                    continue
        
        if not filtered:
            messagebox.showwarning("No Data", f"No audit data found for company '{company}' in the selected date/time range.")
            return

        # Generate professional PDF (delegated to audit_report module)
        create_professional_audit_pdf(save_path, company, start_datetime, end_datetime, filtered)
        messagebox.showinfo("Success", f"Audit PDF generated successfully for company '{company}'.\n\nTotal records: {len(filtered)}")

    # -- Save / Load method --
    def validate_peaks(self):
        """
        Validates peak configuration:
        1. Theoretical Plates: Not Less than 5000
        2. Tailing Factor: Not More than 2.0
        3. Resolution (where two or more peaks): Not Less than 3.0
        Returns: (is_valid, error_message)
        """
        if not self.peak_entries:
            return True, ""

        errors = []
        
        for i, row in enumerate(self.peak_entries):
            peak_num = i + 1
            peak_name = row['peak_name'].get().strip()
            display_name = peak_name if peak_name else f"Peak {peak_num}"
            
            # Validate Theoretical Plates (>= 5000)
            try:
                plates_str = row['theoretical_plates'].get().strip()
                if plates_str:
                    plates = float(plates_str)
                    if plates < 5000:
                        errors.append(f"{display_name}: Theoretical Plates must be >= 5000 (got {plates})")
            except ValueError:
                if row['theoretical_plates'].get().strip():
                    errors.append(f"{display_name}: Theoretical Plates must be a valid number")
            
            # Validate Tailing Factor (<= 2.0)
            try:
                tail_str = row['tailing_factor'].get().strip()
                if tail_str:
                    tail = float(tail_str)
                    if tail > 2.0:
                        errors.append(f"{display_name}: Tailing Factor must be <= 2.0 (got {tail})")
            except ValueError:
                if row['tailing_factor'].get().strip():
                    errors.append(f"{display_name}: Tailing Factor must be a valid number")
        
        # Validate Resolution (>= 3.0) for 2+ peaks
        peaks_with_rt = []
        for i, row in enumerate(self.peak_entries):
            rt_str = row['retention_time'].get().strip()
            peak_name = row['peak_name'].get().strip()
            display_name = peak_name if peak_name else f"Peak {i + 1}"
            if rt_str:
                try:
                    rt = float(rt_str)
                    peaks_with_rt.append((i, rt, display_name))
                except ValueError:
                    errors.append(f"{display_name}: Retention Time must be a valid number")
        
        if len(peaks_with_rt) >= 2:
            for j in range(len(peaks_with_rt) - 1):
                idx1, rt1, name1 = peaks_with_rt[j]
                idx2, rt2, name2 = peaks_with_rt[j + 1]
                if rt2 <= rt1:
                    errors.append(f"Resolution: {name2} retention time must be greater than {name1}")
        
        if errors:
            return False, "\n".join(errors)
        return True, ""

    def save_method(self):
        # Validate peaks first
        is_valid, error_msg = self.validate_peaks()
        if not is_valid:
            messagebox.showerror("Validation Error", f"Peak configuration errors:\n\n{error_msg}")
            return
        
        filepath = filedialog.asksaveasfilename(defaultextension=".mtd", filetypes=[("Method Files", "*.mtd")])
        if not filepath:
            return

        dt_value = "N/A"
        if _HAS_TKCAL and "date" in self.sample_entries:
            date_part = self.sample_entries["date"].get()
            hour = self.sample_entries.get("hour").get() if self.sample_entries.get("hour") is not None else "00"
            minute = self.sample_entries.get("minute").get() if self.sample_entries.get("minute") is not None else "00"
            # format to 12-hour with AM/PM for saved method
            try:
                from datetime import datetime
                dt = datetime.strptime(f"{date_part} {hour}:{minute}", "%d/%m/%Y %H:%M")
                dt_value = dt.strftime("%d/%m/%Y %I:%M %p")
            except Exception:
                dt_value = f"{date_part} {hour}:{minute}"
        elif "datetime" in self.sample_entries:
            dt_value = self.sample_entries["datetime"].get() or "N/A"

        peaks_data = []
        for i, row in enumerate(self.peak_entries):
            peaks_data.append({
                "peak_number": i + 1,
                "peak_name": row['peak_name'].get(),
                "retention_time": row['retention_time'].get(),
                "tailing_factor": row['tailing_factor'].get(),
                "theoretical_plates": row['theoretical_plates'].get()
            })

        data = {
            "sample_info": {
                "project_name": self.sample_entries.get("project_name").get() if isinstance(self.sample_entries.get("project_name"), tk.Entry) else "",
                "analyst": self.sample_entries.get("analyst").get() if isinstance(self.sample_entries.get("analyst"), tk.Entry) else "",
                "company": self.sample_entries.get("company").get() if isinstance(self.sample_entries.get("company"), tk.Entry) else "",
                "description": self.sample_description.get("1.0", tk.END).strip(),
                "datetime": dt_value,
                "saved_on": datetime.now().isoformat()
            },
            "method": {k: (v.get() if hasattr(v, "get") else "") for k, v in self.method_fields.items()},
            "peaks": peaks_data
        }

        try:
            MethodManager.save_method(data, filepath)
            self.current_method_path = filepath
            messagebox.showinfo("Saved", "Method saved.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save method: {e}")

    def load_method(self):
        path = filedialog.askopenfilename(filetypes=[("Method Files", "*.mtd"), ("JSON", "*.json"), ("All", "*.*")])
        if not path:
            return
        try:
            data = MethodManager.load_method(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load method: {e}")
            return

        self.current_method_path = path

        si = data.get('sample_info', {})
        if 'project_name' in si and 'project_name' in self.sample_entries:
            self.sample_entries['project_name'].delete(0, tk.END)
            self.sample_entries['project_name'].insert(0, si.get('project_name', ''))
        if 'analyst' in si and 'analyst' in self.sample_entries:
            self.sample_entries['analyst'].delete(0, tk.END)
            self.sample_entries['analyst'].insert(0, si.get('analyst', ''))
        if 'company' in si and 'company' in self.sample_entries:
            self.sample_entries['company'].delete(0, tk.END)
            self.sample_entries['company'].insert(0, si.get('company', ''))
        self.sample_description.delete("1.0", tk.END)
        self.sample_description.insert("1.0", si.get('description', ''))

        for k, v in data.get('method', {}).items():
            fld = self.method_fields.get(k)
            if fld is None:
                continue
            if hasattr(fld, 'set'):
                try:
                    fld.set(v)
                except Exception:
                    pass
            elif hasattr(fld, 'delete'):
                try:
                    fld.delete(0, tk.END)
                    fld.insert(0, v)
                except Exception:
                    pass

        peaks = data.get('peaks', [])
        if peaks:
            num_field = self.method_fields.get("num_peaks")
            if num_field and hasattr(num_field, "delete"):
                num_field.delete(0, tk.END); num_field.insert(0, str(len(peaks)))
            self.configure_peaks_table()
            for i, p in enumerate(peaks):
                if i < len(self.peak_entries):
                    row = self.peak_entries[i]
                    try:
                        row['peak_name'].delete(0, tk.END); row['peak_name'].insert(0, p.get('peak_name', ''))
                        row['retention_time'].delete(0, tk.END); row['retention_time'].insert(0, p.get('retention_time', ''))
                        row['tailing_factor'].delete(0, tk.END); row['tailing_factor'].insert(0, p.get('tailing_factor', ''))
                        row['theoretical_plates'].delete(0, tk.END); row['theoretical_plates'].insert(0, p.get('theoretical_plates', ''))
                    except Exception:
                        pass
        messagebox.showinfo("Loaded", "Method loaded successfully.")

    def on_signal_exit(self):
        """Handle Signal -> Exit menu item - kills the application process"""
        self.root.quit()
        self.root.destroy()
        os._exit(0)  # Force kill the process

    def dummy_action(self):
        pass