"""Utility functions and constants"""
import os
import sys

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Check for optional dependencies
try:
    from PIL import Image, ImageTk
    _HAS_PIL = True
except Exception:
    Image = None
    ImageTk = None
    _HAS_PIL = False

try:
    import fitz  # PyMuPDF
    _HAS_PYMUPDF = True
except Exception:
    _HAS_PYMUPDF = False

# Constants
DEFAULT_WINDOW_GEOMETRY = "1400x800"
COLORS = {
    "menu_bg": "#F9F9F9",
    "menu_hover": "#F0F0F0",
    "toolbar_bg": "#f0f0f0",
    "separator_light": "#FDFDFD",
    "separator_dark": "#A0A0A0",
    "white": "#FFFFFF",
    "tab_bg": "#F0F0F0",
    "status_bg": "#f0f0f0",
    "plot_bg": "white"
}

FONTS = {
    "menu": ("Times New Roman", 11),
    "tab": ("Times New Roman", 11),
    "label": ("Times New Roman", 9),
    "small": ("Times New Roman", 8)
}

def load_image_with_ratio(path, target_height=55):
    """Load image and resize maintaining aspect ratio"""
    if not os.path.exists(path):
        return None
    
    if not _HAS_PIL:
        return None
    
    try:
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
    except Exception:
        return None

def get_resources_dir(resource_type="Icons"):
    """Get path to resources directory"""
    return resource_path(os.path.join("Resources", resource_type))