@echo off
title Smart City Traffic Management System
echo ===================================================
echo Smart City Traffic Management System - Dynamic Routing
echo Computer Networks PBL Project
echo ===================================================
echo.
echo Starting FastAPI application server on http://127.0.0.1:8000 ...
echo Press Ctrl+C in this terminal to stop the server.
echo.

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

pause
