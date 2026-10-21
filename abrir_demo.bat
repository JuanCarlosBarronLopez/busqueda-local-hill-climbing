@echo off
rem Lanzador de la demostracion: abre la interfaz grafica de Hill Climbing.
rem Funciona con doble clic desde el Explorador de Windows.
cd /d "%~dp0"
echo Iniciando la interfaz grafica...
py run_gui.py
if errorlevel 1 (
    echo.
    echo No se pudo abrir. Comprueba que Python este instalado:
    echo     py --version
    echo y que las dependencias esten instaladas:
    echo     py -m pip install -r requirements.txt
    pause
)
