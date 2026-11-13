@echo off
rem Doble clic: abre el formulario "Registrar venta" del Taller 2 en el navegador.
rem Requiere Python 3.10 o superior. La primera vez instala las dependencias (~1 minuto).
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 iniciar.py
) else (
    python iniciar.py
)
if errorlevel 1 (
    echo.
    echo No se pudo iniciar. Verifique que Python 3.10 o superior este instalado: https://www.python.org/downloads/
    pause
)
