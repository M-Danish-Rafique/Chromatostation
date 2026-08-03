# generators.py
# --- OpenSSL compatibility patch (Windows + ReportLab batch fix) ---
import hashlib

_original_md5 = hashlib.md5

def md5_compat(*args, **kwargs):
    # Remove unsupported keyword on some OpenSSL builds
    kwargs.pop("usedforsecurity", None)
    return _original_md5(*args, **kwargs)

hashlib.md5 = md5_compat
# ------------------------------------------------------------------

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

# IMPORTANT: Batch mode must not use Tk (TkAgg backend) because it can leak
# GUI resources and crash with pixmap allocation errors on large batches.
# Force a non-GUI backend BEFORE importing pyplot.
try:
    import matplotlib
    matplotlib.use("Agg")
except Exception:
    matplotlib = None

import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np
import os
import gc
try:
    from PIL import Image as PILImage
except Exception:
    PILImage = None

# Initialize font support flag
FONT_SUPPORT = False
pdfmetrics = None
TTFont = None

try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    FONT_SUPPORT = True
except ImportError:
    pass


class ChromatogramGenerator:
    """Generates realistic chromatogram plots based on peak area information."""

    @staticmethod
    def asymmetric_gaussian(x, amplitude, center, sigma_left, sigma_right):
        """
        Asymmetric Gaussian (BiGaussian) - stable model for chromatographic peaks.
        Uses different widths on left and right sides of the peak.
        
        Parameters:
        - amplitude: peak height
        - center: retention time (peak apex)
        - sigma_left: standard deviation on left side (before peak)
        - sigma_right: standard deviation on right side (after peak, larger for tailing)
        """
        result = np.zeros_like(x)
        
        # Left side (before peak center) - standard Gaussian
        left_mask = x <= center
        if np.any(left_mask):
            result[left_mask] = amplitude * np.exp(
                -((x[left_mask] - center) ** 2) / (2 * sigma_left ** 2)
            )
        
        # Right side (after peak center) - Gaussian with different width for tailing
        right_mask = x > center
        if np.any(right_mask):
            result[right_mask] = amplitude * np.exp(
                -((x[right_mask] - center) ** 2) / (2 * sigma_right ** 2)
            )
        
        return result

    @staticmethod
    def calculate_peak_width(retention_time, area, run_time, all_areas, width_factor=0.010):
        """
        Calculate realistic peak width (sigma) based on retention time AND peak area.
        
        In HPLC:
        1. Peak width increases with retention time (band broadening)
        2. Larger area peaks are typically broader than smaller area peaks
        
        Parameters:
        - retention_time: peak retention time in minutes
        - area: peak area
        - run_time: total run time
        - all_areas: list of all peak areas for normalization
        - width_factor: base width control (0.010-0.025 for typical HPLC)
        """
        # Base width from retention time (band broadening effect)
        base_width = retention_time * width_factor
        
        # Minimum width
        min_width = run_time * 0.006
        
        # Area-dependent scaling
        if all_areas and len(all_areas) > 0:
            max_area = max(all_areas)
            min_area = min(all_areas)
            
            if max_area > min_area:
                # Normalize area to range [0.6, 1.0]
                # Smaller peaks get 60% of base width, larger peaks get 100%
                area_ratio = (area - min_area) / (max_area - min_area)
                area_scale = 0.6 + (0.4 * area_ratio)
            else:
                area_scale = 1.0
        else:
            area_scale = 1.0
        
        # Combine retention time width with area scaling
        final_width = base_width * area_scale
        
        return max(min_width, final_width)

    @staticmethod
    def generate_chromatogram_data(peaks_info, run_time, width_factor=0.010, 
                                   tailing_ratio=1.3, resolution_points_per_min=200):
        """
        Generate realistic chromatogram data points with proper baseline return.

        Parameters:
        - peaks_info: list of dicts with 'retention_time', 'area', 'peak_name', 
                     optional 'tailing_base', 'peak_id'
        - run_time: total run time in minutes
        - width_factor: controls peak broadness (0.010 narrow, 0.015 medium, 0.020 broad)
        - tailing_ratio: ratio of right width to left width (>1 for tailing, 1.0-2.0 typical)
        - resolution_points_per_min: data points per minute
        
        Returns:
        - time_array: numpy array of time points
        - signal_array: numpy array of signal values (mV)
        - peak_details: list of dicts with peak metadata
        """
        try:
            run_time = float(run_time)
        except Exception:
            run_time = 10.0

        # Higher resolution for smooth peaks
        time_points = int(run_time * resolution_points_per_min)
        time_array = np.linspace(0, run_time, time_points)
        signal_array = np.zeros(time_points)

        # Realistic baseline and noise in mV
        baseline_mv = 0.0
        noise_level = 0.015  # mV
        noise = np.random.normal(0, noise_level, time_points)
        signal_array += baseline_mv + noise

        # Extract all areas for normalization
        all_areas = [float(p['area']) for p in peaks_info]

        peak_details = []

        for peak in peaks_info:
            center = float(peak['retention_time'])
            area = float(peak['area'])

            # Calculate realistic peak width based on BOTH retention time AND area
            sigma = ChromatogramGenerator.calculate_peak_width(
                center, area, run_time, all_areas, width_factor
            )

            # Get tailing factor from peak info or use default
            peak_tailing = float(peak.get('tailing_base', tailing_ratio))
            
            # Asymmetric Gaussian model (stable and returns to baseline properly)
            sigma_left = sigma
            sigma_right = sigma * peak_tailing  # Right side is wider for tailing
            
            # Calculate amplitude from area
            # For asymmetric Gaussian, area = amplitude * sqrt(2*pi) * (sigma_left + sigma_right) / 2
            total_sigma = (sigma_left + sigma_right) / 2
            amplitude_mv = area / (total_sigma * np.sqrt(2 * np.pi) * 1000.0)
            
            # Generate asymmetric Gaussian peak
            peak_signal = ChromatogramGenerator.asymmetric_gaussian(
                time_array, amplitude_mv, center, sigma_left, sigma_right
            )

            signal_array += peak_signal

            # Find actual peak height at retention time
            peak_idx = np.argmin(np.abs(time_array - center))
            peak_height = float(signal_array[peak_idx])

            # Calculate actual area under the generated peak for verification
            actual_area = np.trapz(peak_signal, time_array) * 1000.0  # convert back to original units

            # Calculate peak width at half height
            half_max = np.max(peak_signal) / 2
            above_half = peak_signal > half_max
            if np.any(above_half):
                indices = np.where(above_half)[0]
                width_at_half = (indices[-1] - indices[0]) / resolution_points_per_min
            else:
                width_at_half = 0.0

            peak_details.append({
                'name': peak.get('peak_name', 'Unknown'),
                'retention_time': float(center),
                'height': float(peak_height),
                'area': float(area),
                'actual_area': float(round(actual_area, 2)),
                'sigma': float(round(sigma, 4)),
                'width_at_half_height': float(round(width_at_half, 4)),
                'tailing_factor': float(round(peak_tailing, 3)),
                'peak_id': peak.get('peak_id', 0)
            })

        # Clean up temporary arrays to free memory
        del noise
        del all_areas
        del peak_signal

        return time_array, signal_array, peak_details

    @staticmethod
    def plot_chromatogram(time_array, signal_array, peak_details, fig=None, ax=None):
        """
        Plot chromatogram with proper formatting.
        
        Parameters:
        - time_array: time points array
        - signal_array: signal values array
        - peak_details: list of peak information dicts
        - fig, ax: optional matplotlib figure and axis objects
        
        Returns:
        - fig, ax: matplotlib figure and axis objects
        """
        if fig is None or ax is None:
            fig, ax = plt.subplots(figsize=(10, 4))

        ax.plot(time_array, signal_array, color='blue', linewidth=1)

        # Axis labels
        ax.set_xlabel('Time (min)')
        ax.set_ylabel('Voltage (mV)')
        ax.set_title('Chromatogram')

        # Annotate peaks
        for peak in peak_details:
            rt = peak['retention_time']
            h = peak.get('height', 0.0)
            name = peak.get('name', '')
            # annotate with peak name and height in mV
            ax.annotate(f"{name}\n{h:.3f} mV", 
                       xy=(rt, h), 
                       xytext=(rt, h + max(0.02, h * 0.08)),
                       ha='center', 
                       fontsize=8, 
                       arrowprops=dict(arrowstyle='->', lw=0.5))

        # Grid and tick divisions
        ax.grid(alpha=0.3)

        # X-axis: 10 equal divisions (11 ticks)
        x_min, x_max = 0.0, max(time_array) if len(time_array) else 1.0
        xticks = np.linspace(x_min, x_max, 11)
        ax.set_xticks(xticks)

        # Y-axis: 12 equal divisions (13 ticks) with scaled labels
        y_min = float(np.min(signal_array)) if len(signal_array) else 0.0
        y_max = float(np.max(signal_array)) if len(signal_array) else 1.0
        y_range = max(1e-6, y_max - y_min)
        margin = y_range * 0.06
        y_low = max(0, y_min - margin)  # Don't go below 0
        y_high = y_max + margin
        yticks = np.linspace(y_low, y_high, 13)
        ax.set_yticks(yticks)
        
        # Scale Y-axis labels by dividing by 100 (remove last two zeros)
        yticklabels = [f'{int(tick/100)}' if tick >= 100 else f'{tick:.1f}' for tick in yticks]
        ax.set_yticklabels(yticklabels)

        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_low, y_high)

        return fig, ax
    

class PDFReportGenerator:
    """Generates PDF reports for chromatography data with exact formatting."""
    
    # Class variable to track if fonts are registered
    _fonts_registered = False
    
    @staticmethod
    def _register_fonts():
        """Register Arial font (regular and bold) or use Helvetica as substitute."""
        if PDFReportGenerator._fonts_registered:
            return "Helvetica"
        
        if not FONT_SUPPORT:
            PDFReportGenerator._fonts_registered = True
            return "Helvetica"
        
        try:
            # Try to register Arial (regular and bold) from common font paths
            arial_regular_paths = [
                'C:\\Windows\\Fonts\\arial.ttf',
                'C:\\Windows\\Fonts\\Arial.ttf',
                '/usr/share/fonts/truetype/msttcorefonts/arial.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                '/System/Library/Fonts/Supplemental/Arial.ttf'
            ]
            
            arial_bold_paths = [
                'C:\\Windows\\Fonts\\arialbd.ttf',
                'C:\\Windows\\Fonts\\Arialbd.ttf',
                '/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
                '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
            ]
            
            regular_found = False
            bold_found = False
            
            # Register regular Arial
            for path in arial_regular_paths:
                if os.path.exists(path):
                    pdfmetrics.registerFont(TTFont('Arial', path))
                    regular_found = True
                    break
            
            # Register bold Arial
            for path in arial_bold_paths:
                if os.path.exists(path):
                    pdfmetrics.registerFont(TTFont('Arial-Bold', path))
                    bold_found = True
                    break
            
            if regular_found and bold_found:
                PDFReportGenerator._fonts_registered = True
                return "Arial"
            elif regular_found:
                # Only regular found, use it for both
                PDFReportGenerator._fonts_registered = True
                return "Arial"
            else:
                # If Arial not found, use Helvetica (built-in, always available)
                PDFReportGenerator._fonts_registered = True
                return "Helvetica"
            
        except Exception as e:
            PDFReportGenerator._fonts_registered = True
            return "Helvetica"
            
    @staticmethod
    def _wrap_text(text, max_width, canvas_obj, font_name, font_size):
        """Wrap text to fit within max_width."""
        canvas_obj.setFont(font_name, font_size)
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if canvas_obj.stringWidth(test_line, font_name, font_size) <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _create_chromatogram_image(chromatogram_data, width_inches=7, height_inches=4):
        """Create chromatogram plot and return as image with scaled Y-axis labels."""
        time_data, signal_data, peak_detections = chromatogram_data

        fig, ax = plt.subplots(figsize=(width_inches, height_inches))

        # Draw chromatogram
        ax.plot(time_data, signal_data, color='black', linewidth=0.6, antialiased=True, zorder=2)

        # Grid
        ax.grid(True, linestyle='--', alpha=0.45, color='gray', zorder=0)

        # Axis labels
        ax.set_xlabel('Time (min)', fontsize=10, family='sans-serif')
        ax.set_ylabel('Voltage (mV)', fontsize=10, family='sans-serif')

        # Compute Y limits and range
        y_min = min(signal_data) if min(signal_data) < 0 else 0.0
        y_max = max(signal_data) if len(signal_data) else 1.0
        y_range = max(1e-9, y_max - y_min)

        # SOLUTION 2: Set X limits to actual data range (no extension)
        # This eliminates the empty space by matching axis to data
        max_time = max(time_data)
        ax.set_xlim(0, max_time)

        # Initial Y limits leaving modest headroom
        plot_y_min = y_min - y_range * 0.02
        plot_y_max = y_max * 1.12
        ax.set_ylim(plot_y_min, plot_y_max)

        # X-axis divisions - 10 equal divisions from 0 to max_time
        x_ticks = np.linspace(0, max_time, 11)
        ax.set_xticks(x_ticks)
        # Format X-axis labels without decimal point if whole numbers
        ax.set_xticklabels([f'{int(x)}' if x == int(x) else f'{x:.1f}' for x in x_ticks])

        # Y-axis with scaled labels (divide by 100)
        yticks = ax.get_yticks()
        yticklabels = [f'{int(tick/100)}' if tick >= 100 else f'{tick:.1f}' for tick in yticks]

        ax.set_yticklabels(yticklabels)

        # Force a draw to obtain renderer/extent information
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

        # Pixel margins
        top_pixel_margin = 7.5
        bottom_pixel_margin = 15

        # Convert pixel margins to data units in Y using axes display bbox
        ax_bbox = ax.get_window_extent(renderer=renderer)
        height_pixels = ax_bbox.height if ax_bbox.height > 0 else 1.0
        data_units_per_pixel = (plot_y_max - plot_y_min) / height_pixels
        top_margin_data = top_pixel_margin * data_units_per_pixel
        bottom_margin_data = bottom_pixel_margin * data_units_per_pixel

        # Recompute allowed top/bottom with margins
        allowed_top = plot_y_max - top_margin_data
        allowed_bottom = plot_y_min + bottom_margin_data

        # Draw vertical peak labels
        if peak_detections and len(peak_detections) > 0:
            fontsize = 7
            for peak in peak_detections:
                if 'retention_time' in peak and 'height' in peak:
                    rt_val = float(peak['retention_time'])
                    peak_height = float(peak['height'])
                    peak_name = (peak.get('name') or peak.get('peak_name') or "").strip()

                    rt_str = f"{rt_val:.3f}"
                    display_text = f"{peak_name} - {rt_str}" if peak_name else rt_str

                    tmp = ax.text(
                        rt_val, peak_height, display_text,
                        rotation=90, verticalalignment='center', horizontalalignment='center',
                        fontsize=fontsize, family='sans-serif', color='black',
                        zorder=10, clip_on=False
                    )
                    fig.canvas.draw()
                    tbbox = tmp.get_window_extent(renderer=renderer)
                    tmp.remove()

                    bbox_h_pixels = tbbox.height if tbbox.height > 0 else 1.0
                    bbox_h_data = bbox_h_pixels * data_units_per_pixel

                    label_top_if_centered = peak_height + (bbox_h_data / 2.0)
                    if label_top_if_centered > allowed_top:
                        label_center_y = allowed_top - (bbox_h_data / 2.0)
                    else:
                        label_center_y = peak_height

                    label_bottom_if_centered = label_center_y - (bbox_h_data / 2.0)
                    if label_bottom_if_centered < allowed_bottom:
                        label_center_y = allowed_bottom + (bbox_h_data / 2.0)

                    ax_xlim = ax.get_xlim()
                    width_pixels = ax_bbox.width if ax_bbox.width > 0 else 1.0
                    data_units_per_pixel_x = (ax_xlim[1] - ax_xlim[0]) / width_pixels
                    offset_px = 10.0
                    x_offset = offset_px * data_units_per_pixel_x

                    x_pos = rt_val + x_offset
                    right_limit = ax_xlim[1] - (data_units_per_pixel_x * 2.0)
                    left_limit = ax_xlim[0] + (data_units_per_pixel_x * 2.0)

                    if x_pos > right_limit:
                        x_pos = rt_val - x_offset
                        if x_pos < left_limit:
                            x_pos = rt_val

                    ax.text(
                        x_pos, label_center_y, display_text,
                        rotation=90, verticalalignment='center', horizontalalignment='center',
                        fontsize=fontsize, family='sans-serif', color='black',
                        zorder=11, clip_on=True
                    )

        # Final layout adjustments
        fig.subplots_adjust(left=0.10, right=0.98, bottom=0.15, top=0.95)

        # Convert to image and return
        buf = io.BytesIO()
        try:
            canvas_obj = FigureCanvasAgg(fig)
            canvas_obj.print_png(buf)
            buf.seek(0)

            # IMPORTANT: ImageReader may keep a reference to the underlying stream.
            # To avoid retaining large in-memory buffers across many batch PDFs,
            # load into a PIL image first (decouples from BytesIO), then close buffer.
            if PILImage is not None:
                pil_img = PILImage.open(buf)
                pil_img.load()  # force decode; after this BytesIO can be closed
                img = ImageReader(pil_img)
                # Do NOT close pil_img here: ReportLab may still read from it during
                # drawImage(). It will be released when `img` is garbage-collected.
            else:
                img = ImageReader(buf)

            return img
        finally:
            try:
                buf.close()
            except Exception:
                pass
            plt.close(fig)  # Ensure figure is closed
    
    @staticmethod
    def generate_pdf(output_path, method_data, sample_info, peaks_data,
                     chromatogram_data, results_table):
        """
        Generate professional PDF report matching the reference format.
        
        Parameters:
        - output_path: Path to save the PDF
        - method_data: Dict with instrument, column_temp, column_part, detector, wavelength
        - sample_info: Dict with company_name, project_name, datetime, analyst, 
                       generation_time, data_file
        - peaks_data: Peak information (if needed)
        - chromatogram_data: Tuple of (time_array, signal_array, peak_detections)
        - results_table: DataFrame with columns: Peak No., Peak Name, Retention Time, 
                        Tailing Factor, Theoretical Plates, Resolution
        """
        # Register fonts and get the font name to use
        arial_font = PDFReportGenerator._register_fonts()
        
        # Determine bold font name
        if arial_font == "Arial":
            arial_bold = "Arial-Bold"
        elif arial_font == "Helvetica":
            arial_bold = "Helvetica-Bold"
        else:
            arial_bold = arial_font  # Fallback
        
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        # Margins
        left_margin = 0.75 * inch
        right_margin = width - 0.75 * inch
        top_margin = height - 0.5 * inch
        
        y_position = top_margin
        
        # 1. Company Name at top - Blue, Bold, Size 14
        c.setFillColor(colors.HexColor('#0000FF'))
        c.setFont(arial_bold, 14)
        c.drawString(left_margin, y_position, sample_info.get('company_name', 'N/A'))
        c.setFillColor(colors.black)
        y_position -= 0.08 * inch
        
        # 2. Separator line
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.5)
        c.line(left_margin, y_position, right_margin, y_position)
        y_position -= 0.35 * inch
        
        # 3. Project Name in Red
        c.setFillColor(colors.red)
        c.setFont(arial_bold, 16)
        project_name = sample_info.get('project_name', 'N/A')
        c.drawCentredString(width / 2, y_position, project_name)
        c.setFillColor(colors.black)
        y_position -= 0.35 * inch
        
        # 4. Two-column data section
        col1_x = left_margin
        col2_x = width / 2 + 0.5 * inch
        row_height = 0.18 * inch
        
        c.setFont(arial_font, 9)
        
        # Column 1
        y_pos_col1 = y_position
        c.drawString(col1_x, y_pos_col1, f"Date/Time: {sample_info.get('datetime', 'N/A')}")
        y_pos_col1 -= row_height
        
        # Data File - with wrapping
        data_file_label = "Data File: "
        c.drawString(col1_x, y_pos_col1, data_file_label)
        data_file = sample_info.get('data_file', 'N/A')
        label_width = c.stringWidth(data_file_label, arial_font, 9)
        max_file_width = (width / 2 - 0.5 * inch) - label_width - 0.1 * inch
        
        file_lines = PDFReportGenerator._wrap_text(data_file, max_file_width, c, arial_font, 9)
        c.drawString(col1_x + label_width, y_pos_col1, file_lines[0] if file_lines else '')
        for i, line in enumerate(file_lines[1:], 1):
            y_pos_col1 -= row_height
            c.drawString(col1_x + label_width, y_pos_col1, line)
        
        # Column 2
        y_pos_col2 = y_position
        c.drawString(col2_x, y_pos_col2, f"Analyst: {sample_info.get('analyst', 'N/A')}")
        y_pos_col2 -= row_height
        c.drawString(col2_x, y_pos_col2, "Quantification: Area/Area%")
        
        y_position = min(y_pos_col1, y_pos_col2) - 0.25 * inch
        
        # 5. Three-column instrument data section
        col1_x = left_margin
        col2_x = left_margin + 2.5 * inch
        col3_x = left_margin + 5 * inch
        
        y_pos_inst = y_position
        
        # Column 1
        c.drawString(col1_x, y_pos_inst, f"Type of Instrument: {method_data.get('instrument', 'N/A')}")
        y_pos_inst -= row_height
        c.drawString(col1_x, y_pos_inst, f"Column Temp: {method_data.get('column_temp', 'N/A')}")
        y_pos_inst -= row_height
        c.drawString(col1_x, y_pos_inst, f"Column Part No: {method_data.get('column_part', 'N/A')}")
        
        # Column 2
        y_pos_col2 = y_position
        c.drawString(col2_x, y_pos_col2, "Gradient: High Pressure")
        
        # Column 3
        y_pos_col3 = y_position
        c.drawString(col3_x, y_pos_col3, f"Detector: {method_data.get('detector', 'N/A')}")
        y_pos_col3 -= row_height
        c.drawString(col3_x, y_pos_col3, f"Wavelength (nm): {method_data.get('wavelength', 'N/A')}")
        
        y_position = y_pos_inst - 0.3 * inch
        
        # 6. Chromatogram graph
        try:
            chrom_img = PDFReportGenerator._create_chromatogram_image(chromatogram_data)
            img_width = 6.5 * inch
            img_height = 3.5 * inch
            c.drawImage(chrom_img, left_margin, y_position - img_height, 
                       width=img_width, height=img_height, preserveAspectRatio=True)
            y_position -= (img_height + 0.2 * inch)
        except Exception as e:
            c.setFont(arial_font, 10)
            c.drawString(left_margin, y_position, f"[Chromatogram generation error: {str(e)}]")
            y_position -= 0.5 * inch
        
        # 7. Results table
        c.setFont(arial_bold, 11)
        # Center "Results" text
        results_text = "Results"
        text_width = c.stringWidth(results_text, arial_bold, 11)
        c.drawString((width - text_width) / 2, y_position, results_text)
        y_position -= 0.2 * inch
        
        # Prepare table data
        headers = list(results_table.columns)
        table_data = [headers] + results_table.astype(str).values.tolist()
        
        # Create table - compute column widths dynamically based on number of columns
        num_cols = len(headers)
        available_width = (right_margin - left_margin)
        
        default_weights = []
        for h in headers:
            if h in ('Peak No.',):
                default_weights.append(0.6)
            elif h in ('Peak Name',):
                default_weights.append(1.6)
            elif h in ('Retention Time', 'Area'):
                default_weights.append(1.1)
            elif h in ('Tailing Factor',):
                default_weights.append(1.0)
            elif h in ('Theoretical Plates',):
                default_weights.append(1.2)
            elif h in ('Resolution',):
                default_weights.append(0.9)
            else:
                default_weights.append(1.0)

        total_weight = sum(default_weights) if sum(default_weights) > 0 else num_cols
        col_widths = [(w / total_weight) * available_width for w in default_weights]
        
        # Create table with Arial fonts and no background, only horizontal lines
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            # No background color for header
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), arial_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), arial_font),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
            # Only horizontal lines (top, bottom, and between rows)
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        # Draw table
        table_width, table_height = table.wrap(0, 0)
        table.drawOn(c, left_margin, y_position - table_height)
        
        # 8. Footer section
        footer_y = 0.75 * inch
        
        # Separator line at footer
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.5)
        c.line(left_margin, footer_y + 0.2 * inch, right_margin, footer_y + 0.2 * inch)
        
        # Footer text
        c.setFont(arial_font, 9)
        
        # Date on left side
        from datetime import datetime
        current_date = datetime.now().strftime("%B %d, %Y")
        c.drawString(left_margin, footer_y, current_date)
        
        # Quality Control Department on right side
        qc_text = "Quality Control Department"
        qc_width = c.stringWidth(qc_text, arial_font, 9)
        c.drawString(right_margin - qc_width, footer_y, qc_text)
        
        # Save PDF
        c.save()
        # Explicitly delete canvas to free memory
        del c
        gc.collect()


class ORGFileGenerator:
    """Generates .org files for storing chromatogram data."""

    @staticmethod
    def save_org_file(output_path, method_data, sample_info,
                      chromatogram_data, results_table):
        time_array, signal_array, peak_details = chromatogram_data

        org_data = {
            'version': '1.0',
            'type': 'chromatogram',
            'sample_info': sample_info,
            'method_data': method_data,
            'chromatogram': {
                'time': np.array(time_array).tolist(),
                'signal': np.array(signal_array).tolist(),
                'peaks': peak_details
            },
            'results': results_table.to_dict('records')
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(org_data, f, indent=2)