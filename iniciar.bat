@echo off
title Sistema Financeiro Automatizado
cd /d C:\Users\andre\financeiro
set PATH=C:\Users\andre\AppData\Local\Programs\Python\Python312;C:\Users\andre\AppData\Local\Programs\Python\Python312\Scripts;%PATH%
set PYTHONIOENCODING=utf-8
chcp 65001 >nul 2>&1
financeiro menu
pause
