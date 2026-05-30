@echo off
chcp 65001 > nul
cd /d C:\Users\gimatakumi\Documents\projects\NBA_news\backend
python monitor.py >> logs\monitor.log 2>&1
