# N2000 Chromatostation

![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![CI](https://github.com/your-username/your-repo/actions/workflows/python-ci.yml/badge.svg)

A polished desktop application for chromatogram analysis, report viewing, and PDF report generation. This project includes two variants:

- Offline workflow for local analysis and report generation
- Online workflow for browser-assisted processing and reporting

## ✨ Highlights

- Load and inspect ORG data files
- Visualize chromatogram signals and peaks
- Generate and preview PDF reports
- Save, print, and manage report outputs
- Built with Python, Tkinter, Matplotlib, Pandas, and PyMuPDF

## 📁 Project Structure

- offline/ — desktop offline application
- online/ — online-enabled application variant
- build/ — packaged build outputs
- requirements.txt — dependency list for each app variant

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone <your-github-repo-url>
cd Software
```

### 2. Create a virtual environment

On Windows:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

For the offline app:

```bash
cd offline
pip install -r requirements.txt
```

For the online app:

```bash
cd ../online
pip install -r requirements.txt
```

### 4. Run the application

```bash
cd offline
py app.py
```

or

```bash
cd online
py app.py
```

## 🧱 Build Executable

To build a standalone Windows executable with PyInstaller:

```bash
cd offline
py -m PyInstaller build_exe.spec
```

```bash
cd online
py -m PyInstaller build_exe.spec
```

## 🖼️ Showcase the Project on GitHub

To make the repository look impressive:

1. Add a good project banner or screenshot in the repository root
2. Write a short demo video or GIF
3. Add a clear architecture summary in this README
4. Use release notes for important versions
5. Keep the codebase tidy and documented

## 🛠️ Tech Stack

- Python 3.8+
- Tkinter
- Pillow
- NumPy
- Pandas
- Matplotlib
- ReportLab
- PyMuPDF
- PyInstaller

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
