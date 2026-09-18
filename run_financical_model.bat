@echo off
cd /d "C:\Rons Documents\Rons Personal Stuff\gitRepos\repo-programs\financialModel"

call .venv\Scripts\activate.bat

python -m src.gui.app

