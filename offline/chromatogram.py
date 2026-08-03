"""Chromatogram plotting and management with automatic scrollbars"""
import tkinter as tk
from tkinter import messagebox
import numpy as np
import math
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MultipleLocator
import json
 
class ChromatogramViewer:
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.org_data = None
        self.figure = None
        self.ax = None
        self.canvas = None
        self.frame = None
        self._last_time = None
        self._last_signal = None
        self.canvas_frame = None
        self.h_scrollbar = None
        self.v_scrollbar = None
        self.create_chromatogram_area()

    def create_chromatogram_area(self):
        # Main container frame - minimal padding
        self.frame = tk.Frame(self.parent_frame, bg='#f0f0f0')
        
        # Inner frame with sunken border - reduced padding
        inner_border = tk.Frame(self.frame, relief='sunken', borderwidth=2, bg='#e0e0e0')
        inner_border.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # White content frame for the plot - minimal padding
        content_frame = tk.Frame(inner_border, bg='white', bd=0)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Create a canvas with scrollbars
        # Canvas that will contain the matplotlib figure
        self.canvas_frame = tk.Canvas(content_frame, bg='white', highlightthickness=0)
        
        # Scrollbars
        self.h_scrollbar = tk.Scrollbar(content_frame, orient=tk.HORIZONTAL, command=self.canvas_frame.xview)
        self.v_scrollbar = tk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.canvas_frame.yview)
        
        # Configure canvas to use scrollbars
        self.canvas_frame.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)
        
        # Grid layout for canvas and scrollbars
        self.canvas_frame.grid(row=0, column=0, sticky='nsew')
        self.h_scrollbar.grid(row=1, column=0, sticky='ew')
        self.v_scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Configure grid weights
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        
        # Frame inside canvas to hold the matplotlib widget
        plot_container = tk.Frame(self.canvas_frame, bg='white')
        self.canvas_frame.create_window((0, 0), window=plot_container, anchor='nw', tags='plot_container')
        
        # Create matplotlib figure with reasonable initial size
        self.figure = Figure(figsize=(12, 6), dpi=100, facecolor='white')
        self.ax = self.figure.add_subplot(111)
        
        # Set up the chromatogram plot
        self.setup_chromatogram()
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.figure, plot_container)
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # Initial draw
        self.canvas.draw()
        
        # Bind configure for resize handling
        canvas_widget.bind('<Configure>', self._on_resize)
        plot_container.bind('<Configure>', self._update_scrollregion)
        
        # Hide scrollbars initially
        self._check_scrollbars()

        return self.frame

    def _update_scrollregion(self, event=None):
        """Update the scroll region to encompass the plot"""
        self.canvas_frame.update_idletasks()
        self.canvas_frame.configure(scrollregion=self.canvas_frame.bbox('all'))
        self._check_scrollbars()

    def _check_scrollbars(self):
        """Show or hide scrollbars based on content size vs visible size"""
        self.canvas_frame.update_idletasks()
        
        # Get the bbox of all items in the canvas
        bbox = self.canvas_frame.bbox('all')
        if not bbox:
            return
        
        # Get canvas dimensions
        canvas_width = self.canvas_frame.winfo_width()
        canvas_height = self.canvas_frame.winfo_height()
        
        # Content dimensions
        content_width = bbox[2] - bbox[0]
        content_height = bbox[3] - bbox[1]
        
        # Show/hide horizontal scrollbar
        if content_width > canvas_width and canvas_width > 1:
            self.h_scrollbar.grid()
        else:
            self.h_scrollbar.grid_remove()
        
        # Show/hide vertical scrollbar
        if content_height > canvas_height and canvas_height > 1:
            self.v_scrollbar.grid()
        else:
            self.v_scrollbar.grid_remove()

    def _on_resize(self, event):
        """Handle window resize - update layout to maximize space usage"""
        if not self.figure:
            return
        
        # Update subplots_adjust to maximize space usage
        self.figure.subplots_adjust(
            left=0.07,
            right=0.999,
            top=0.96,
            bottom=0.22
        )
        
        # Update ticks if we have data
        if self._last_time is not None:
            self._update_xticks()
        
        # Redraw
        try:
            self.canvas.draw_idle()
        except:
            self.canvas.draw()
        
        # Update scroll region after resize
        self.canvas_frame.after(100, self._update_scrollregion)

    def setup_chromatogram(self):
        self.ax.clear()

        # Labels
        self.ax.set_xlabel('Time (min)', fontsize=9, family='Times New Roman')
        self.ax.set_ylabel('Voltage (mV)', fontsize=9, family='Times New Roman')

        # Limits
        self.ax.set_xlim(0, 80)
        self.ax.set_ylim(0, 1)

        # Ticks
        x_ticks = list(range(0, 81))
        self.ax.set_xticks(x_ticks)
        self.ax.set_xticklabels(['0'] * len(x_ticks), fontsize=6, family='Times New Roman')

        y_ticks = [i/20 for i in range(21)]
        self.ax.set_yticks(y_ticks)
        self.ax.set_yticklabels(['0'] * len(y_ticks), fontsize=6, family='Times New Roman')
        
        # Styling
        self.ax.grid(False)
        for spine in self.ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(1)

        self.ax.set_facecolor('white')
        self.figure.patch.set_facecolor('white')
        
        # Initial subplots_adjust
        self.figure.subplots_adjust(
            left=0.07,
            right=0.999,
            top=0.96,
            bottom=0.22
        )

    def load_org_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.org_data = json.load(f)
            self.plot_chromatogram()
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ORG file:\n{str(e)}")
            return False

    def load_org_data(self, org_data):
        try:
            self.org_data = org_data
            self.plot_chromatogram()
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to plot chromatogram:\n{str(e)}")
            return False

    def _update_xticks(self):
        if self._last_time is None or len(self._last_time) == 0:
            return

        x_max = float(self._last_time[-1])
        try:
            widget = self.canvas.get_tk_widget()
            width_px = widget.winfo_width()
        except:
            width_px = 1000

        approx_label_px = 50
        max_labels = max(2, width_px // approx_label_px)
        desired_labels = min(25, max_labels)
        major_interval = max(1, math.ceil(x_max / desired_labels))

        self.ax.xaxis.set_major_locator(MultipleLocator(major_interval))
        self.ax.xaxis.set_minor_locator(MultipleLocator(1))

        try:
            self.canvas.draw_idle()
        except:
            self.canvas.draw()

    def plot_chromatogram(self):
        if not self.org_data:
            messagebox.showwarning("Warning", "No ORG data loaded")
            return

        try:
            chromatogram = self.org_data.get("chromatogram", {})
            time_data = np.array(chromatogram.get("time", []))
            signal_data = np.array(chromatogram.get("signal", []))
            peaks = chromatogram.get("peaks", [])

            # Divide signal data by 100 to scale Y-axis values
            if len(signal_data) > 0:
                signal_data = signal_data / 100.0

            self._last_time = time_data
            self._last_signal = signal_data

            self.ax.clear()

            # Labels
            self.ax.set_xlabel('Time (min)', fontsize=9, family='Times New Roman')
            self.ax.set_ylabel('Voltage (mV)', fontsize=9, family='Times New Roman')

            # Plot data with dark blue color and thin sharp line
            if len(time_data) > 0 and len(signal_data) > 0:
                self.ax.plot(time_data, signal_data, color='#003366', 
                           linewidth=0.6, antialiased=True, zorder=2, solid_capstyle='round')

            # X limits
            if len(time_data) > 0:
                x_max = float(time_data[-1])
                self.ax.set_xlim(0, x_max * 1.02)
            else:
                self.ax.set_xlim(0, 80)

            # Y limits
            if len(signal_data) > 0:
                y_min = float(np.min(signal_data))
                y_max = float(np.max(signal_data))
            else:
                y_min, y_max = 0.0, 1.0

            y_range = max(1e-6, y_max - y_min)
            bottom = min(0.0, y_min) - y_range * 0.02
            top = y_max * 1.12
            self.ax.set_ylim(bottom, top)

            # Ticks
            self._update_xticks()
            self.ax.xaxis.set_minor_locator(MultipleLocator(1))

            self.ax.tick_params(axis='both', which='major', labelsize=8, 
                               width=1.2, length=5, direction='out')
            self.ax.tick_params(axis='both', which='minor', labelsize=7, 
                               width=0.8, length=3, direction='out')

            # Grid
            self.ax.grid(True, which='major', linestyle='--', alpha=0.45, color='gray', zorder=0)
            self.ax.grid(True, which='minor', linestyle=':', alpha=0.2, linewidth=0.3)

            # Spines
            for spine in self.ax.spines.values():
                spine.set_color('black')
                spine.set_linewidth(1)

            # Force draw to get renderer
            self.canvas.draw()
            renderer = self.canvas.get_renderer()

            # Pixel margins
            top_pixel_margin = 7.5
            bottom_pixel_margin = 15

            # Get axes bbox for pixel-to-data conversion
            ax_bbox = self.ax.get_window_extent(renderer=renderer)
            height_pixels = ax_bbox.height if ax_bbox.height > 0 else 1.0
            width_pixels = ax_bbox.width if ax_bbox.width > 0 else 1.0
            
            # Convert pixel margins to data units
            data_units_per_pixel_y = (top - bottom) / height_pixels
            top_margin_data = top_pixel_margin * data_units_per_pixel_y
            bottom_margin_data = bottom_pixel_margin * data_units_per_pixel_y

            # Allowed boundaries
            allowed_top = top - top_margin_data
            allowed_bottom = bottom + bottom_margin_data

            # X-axis pixel-to-data conversion
            ax_xlim = self.ax.get_xlim()
            data_units_per_pixel_x = (ax_xlim[1] - ax_xlim[0]) / width_pixels

            # Peak labels - displayed vertically on the side of peaks
            if peaks and len(time_data) > 0:
                fontsize = 7
                offset_px = 10.0  # Horizontal offset in pixels
                x_offset = offset_px * data_units_per_pixel_x
                
                for peak in peaks:
                    peak_name = peak.get("name", "")
                    rt = peak.get("retention_time", 0)

                    if len(time_data) == 0:
                        continue
                    
                    idx = int(np.argmin(np.abs(time_data - rt)))
                    if idx < len(signal_data):
                        peak_height = float(signal_data[idx])
                        
                        # Format label: "Peak Name - RT" with 3 decimal places
                        rt_str = f"{rt:.3f}"
                        display_text = f"{peak_name} - {rt_str}" if peak_name else rt_str

                        # Create temporary text to measure bbox
                        tmp = self.ax.text(
                            rt, peak_height, display_text,
                            rotation=90,
                            verticalalignment='center',
                            horizontalalignment='center',
                            fontsize=fontsize,
                            family='sans-serif',
                            color='black',
                            zorder=10,
                            clip_on=False
                        )
                        self.canvas.draw()
                        tbbox = tmp.get_window_extent(renderer=renderer)
                        tmp.remove()

                        # Convert bbox height to data units
                        bbox_h_pixels = tbbox.height if tbbox.height > 0 else 1.0
                        bbox_h_data = bbox_h_pixels * data_units_per_pixel_y

                        # Center label at peak apex
                        label_center_y = peak_height

                        # Check if label would exceed top margin
                        label_top_if_centered = label_center_y + (bbox_h_data / 2.0)
                        if label_top_if_centered > allowed_top:
                            # Shift down so top hits allowed_top
                            label_center_y = allowed_top - (bbox_h_data / 2.0)

                        # Check if label would go below bottom margin
                        label_bottom_if_centered = label_center_y - (bbox_h_data / 2.0)
                        if label_bottom_if_centered < allowed_bottom:
                            # Shift up so bottom equals allowed_bottom
                            label_center_y = allowed_bottom + (bbox_h_data / 2.0)

                        # Calculate horizontal position (to the right of peak)
                        x_pos = rt + x_offset

                        # Define boundaries
                        right_limit = ax_xlim[1] - (data_units_per_pixel_x * 2.0)
                        left_limit = ax_xlim[0] + (data_units_per_pixel_x * 2.0)

                        # If label would exceed right boundary, try left side
                        if x_pos > right_limit:
                            x_pos = rt - x_offset
                            if x_pos < left_limit:
                                # Fallback to peak apex if still out of bounds
                                x_pos = rt

                        # Draw final label without border
                        self.ax.text(
                            x_pos,
                            label_center_y,
                            display_text,
                            rotation=90,
                            verticalalignment='center',
                            horizontalalignment='center',
                            fontsize=fontsize,
                            family='sans-serif',
                            color='black',
                            zorder=11,
                            clip_on=True
                        )

            # Styling
            self.ax.set_facecolor('white')
            self.figure.patch.set_facecolor('white')
            
            # Update subplots_adjust to maximize space usage
            self.figure.subplots_adjust(
                left=0.07,
                right=0.999,
                top=0.96,
                bottom=0.23
            )
            
            self.canvas.draw()
            
            # Update scroll region after plotting
            self.canvas_frame.after(100, self._update_scrollregion)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to plot chromatogram:\n{str(e)}")