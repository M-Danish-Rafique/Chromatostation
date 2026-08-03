"""PDF preview functionality"""
import tkinter as tk
from tkinter import messagebox
import os
from utils import _HAS_PYMUPDF

class PDFViewer:
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.pdf_path = None
        self.photo_image = None
        self.frame = None
        self.canvas = None
        self.scrollbar_y = None
        self.inner_frame = None
        self.pdf_border_frame = None
        self.create_pdf_area()

    def create_pdf_area(self):
        """Create the PDF display area with a vertical scrollbar, outer sunken border,
        centered PDF and a thin black border around the PDF image."""
        # Main frame for the tab (light gray background)
        self.frame = tk.Frame(self.parent_frame, bg='#F0F0F0')

        # Outer sunken border (restore tab border)
        outer_border = tk.Frame(self.frame, relief='sunken', borderwidth=2, bg='#F0F0F0')
        outer_border.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Canvas + vertical scrollbar inside outer_border
        self.canvas = tk.Canvas(outer_border, bg='#F0F0F0', highlightthickness=0, relief=tk.FLAT)
        self.scrollbar_y = tk.Scrollbar(outer_border, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set)

        # Place canvas and vertical scrollbar (no horizontal scrollbar)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.scrollbar_y.grid(row=0, column=1, sticky='ns')

        outer_border.grid_rowconfigure(0, weight=1)
        outer_border.grid_columnconfigure(0, weight=1)

        # Create inner_frame inside the canvas. We'll make it expand to canvas width
        self.inner_frame = tk.Frame(self.canvas, bg='#F0F0F0')
        self.canvas_window = self.canvas.create_window(0, 0, window=self.inner_frame, anchor='nw')

        # When canvas is resized, set the inner window width so inner_frame fills canvas width.
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(self.canvas_window, width=e.width))

        # Make inner_frame use 3-column grid so we can center content in the middle column
        self.inner_frame.grid_columnconfigure(0, weight=1)
        self.inner_frame.grid_columnconfigure(1, weight=0)
        self.inner_frame.grid_columnconfigure(2, weight=1)

        # Placeholder control
        self.canvas_widget = tk.Label(
            self.inner_frame,
            text="PDF Preview Area\nNo PDF loaded",
            bg='#F0F0F0',
            fg='gray',
            font=('Times New Roman', 12),
            justify=tk.CENTER
        )
        # Put placeholder in middle column to be centered
        self.canvas_widget.grid(row=0, column=1, padx=10, pady=10)

        # Keep scrollregion updated when inner_frame contents change
        self.inner_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))

        # Mouse wheel scrolling
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)   # Windows/mac
        self.canvas.bind_all('<Button-4>', self._on_mousewheel)     # Linux scroll up
        self.canvas.bind_all('<Button-5>', self._on_mousewheel)     # Linux scroll down

        return self.frame

    def _on_mousewheel(self, event):
        """Vertical scroll with mouse wheel."""
        try:
            if hasattr(event, 'delta'):
                # Windows / Mac
                if event.delta < 0:
                    self.canvas.yview_scroll(3, 'units')
                else:
                    self.canvas.yview_scroll(-3, 'units')
            else:
                # X11
                if event.num == 5:
                    self.canvas.yview_scroll(3, 'units')
                elif event.num == 4:
                    self.canvas.yview_scroll(-3, 'units')
        except Exception:
            pass

    def load_pdf_file(self, file_path):
        """Load PDF file and render preview."""
        try:
            if not os.path.exists(file_path):
                messagebox.showerror("Error", f"File not found: {file_path}")
                return False
            self.pdf_path = file_path
            self.display_preview()
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load PDF file:\n{str(e)}")
            return False

    def display_preview(self):
        """Render the PDF (first page) into the inner_frame and center it."""
        if not self.pdf_path:
            messagebox.showwarning("Warning", "No PDF file loaded")
            return

        try:
            if _HAS_PYMUPDF:
                self._display_with_pymupdf()
            else:
                self._display_fallback()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to display PDF:\n{str(e)}")

    def _display_with_pymupdf(self):
        """Render PDF page with PyMuPDF and show centered with thin black border."""
        try:
            import fitz
            from PIL import Image, ImageTk
            import io

            doc = fitz.open(self.pdf_path)
            page = doc[0]

            # Render at reasonable zoom for clarity
            zoom = 1.5
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("ppm")))

            # Keep reference to PhotoImage to avoid GC
            self.photo_image = ImageTk.PhotoImage(img)

            # Clear current inner_frame children
            for w in self.inner_frame.winfo_children():
                w.destroy()

            # Create a centered container (middle column) and add a thin black border frame
            content_holder = tk.Frame(self.inner_frame, bg='#F0F0F0')
            content_holder.grid(row=0, column=1, sticky='n')

            # Thin black border: create a 1px black frame and place the white image inside
            self.pdf_border_frame = tk.Frame(
                content_holder,
                bg='black',
                padx=1,
                pady=1
            )
            self.pdf_border_frame.pack(padx=10, pady=20)

            # PDF image placed inside border frame with white background
            self.canvas_widget = tk.Label(self.pdf_border_frame, image=self.photo_image, bg='white')
            self.canvas_widget.pack()

            # Update scrollregion and reset to top
            self.inner_frame.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))
            self.canvas.yview_moveto(0)

            doc.close()
        except Exception as e:
            # fallback if anything fails
            self._display_fallback()

    def _display_fallback(self):
        """Fallback message when PyMuPDF not available."""
        filename = os.path.basename(self.pdf_path) if self.pdf_path else "N/A"
        msg = f"PDF Loaded: {filename}\n\nPyMuPDF not installed for preview.\nInstall with: pip install PyMuPDF\n\nFile: {self.pdf_path}"
        for w in self.inner_frame.winfo_children():
            w.destroy()
        self.canvas_widget = tk.Label(self.inner_frame, text=msg, bg='#F0F0F0', fg='black',
                                     font=('Times New Roman', 10), justify=tk.CENTER)
        self.canvas_widget.grid(row=0, column=1, padx=10, pady=10)
        self.inner_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        self.canvas.yview_moveto(0)
