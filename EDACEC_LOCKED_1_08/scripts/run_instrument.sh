#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/../interface_playground"
python3 -m streamlit run instrument_app.py
