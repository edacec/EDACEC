#!/bin/bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
streamlit run interface_playground/instrument_app.py
