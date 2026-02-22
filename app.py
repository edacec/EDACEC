"""
EDACEC — Public Utility Mode (Hugging Face / Streamlit entrypoint)

This file exists so hosting platforms can run:
  streamlit run app.py

It intentionally delegates to the existing Streamlit UI in:
  interface_playground/instrument_app.py
"""

import os
from pathlib import Path

# Flag the UI as "public mode" (interface layer may use this to simplify UI)
os.environ["EDACEC_PUBLIC_MODE"] = "1"

# Execute the existing Streamlit app file as the main program.
# This avoids requiring any refactor of your current UI file structure.
APP_PATH = Path(__file__).resolve().parent / "interface_playground" / "instrument_app.py"
code = APP_PATH.read_text(encoding="utf-8")
exec(compile(code, str(APP_PATH), "exec"), {"__name__": "__main__"})
