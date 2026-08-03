import tkinter as tk
from app import ChromatographyApp

def main():
    root = tk.Tk()
    app = ChromatographyApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()