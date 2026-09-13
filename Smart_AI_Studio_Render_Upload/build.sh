#!/usr/bin/env bash
set -o errexit
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p uploads temp_dubbing_files Downloaded_Videos Exported_Videos
