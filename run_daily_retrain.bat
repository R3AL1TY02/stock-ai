@echo off
cd /d "C:\Users\zachi\OneDrive\Desktop\stock_ai"
python daily_retrain.py >> "outputs\daily_retrain_log.txt" 2>&1
