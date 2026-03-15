"""
FinSight — Streamlit Cloud Entrypoint
======================================
Streamlit Cloud expects the main file at the repo root.
This file simply re-exports app/Home.py by adding the project
root to sys.path and executing the page.

Deploy setting on Streamlit Cloud:
  Main file path: streamlit_app.py
"""

import sys
from pathlib import Path

# Ensure all project modules are importable
sys.path.insert(0, str(Path(__file__).parent))

# Execute the actual home page
exec(open("app/Home.py").read())  # noqa: S102
