@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

REM =========================================================
REM Bashi Voice Factory v3.1 - USB Portable Launcher
REM =========================================================

cd /d "%~dp0"

REM Log all output for debugging
set "LOGFILE=%~dp0launch_log.txt"
echo [%date% %time%] Launcher started > "%LOGFILE%"
echo Working directory: %CD% >> "%LOGFILE%"

set "EMBED_DIR=python-3.12.10-embed-amd64"
set "PYTHON_EXE=%EMBED_DIR%\python.exe"

echo ========================================================
echo  Bashi Voice Factory v3.1 (USB Portable Edition)
echo  Bashi Voice Factory v3.1  便携版
echo ========================================================

REM 1. Check if the embedded Python folder exists
echo [CHECK] Looking for: %PYTHON_EXE% >> "%LOGFILE%"
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Portable Python environment not found!
    echo         找不到便携版 Python 环境！
    echo Please make sure the folder "%EMBED_DIR%" is in the same directory as this script.
    echo 请确保 "%EMBED_DIR%" 文件夹与此脚本在同一目录下。
    echo [ERROR] Python not found at %PYTHON_EXE% >> "%LOGFILE%"
    pause
    exit /b 1
)
echo [OK] Python found >> "%LOGFILE%"

REM 2. Patch ._pth file to enable 'import site' (required for pip packages)
powershell -NoProfile -Command "$pth='%EMBED_DIR%\python312._pth'; if (Test-Path $pth) { $text=(Get-Content $pth) -replace '^#import site', 'import site'; Set-Content $pth -Value $text }"

REM 3. Bootstrap pip if not installed
if not exist "%EMBED_DIR%\Scripts\pip.exe" (
    echo.
    echo [INFO] First-time setup: Initializing pip downloader...
    echo [INFO] 首次运行: 正在为您下载并配置便携版 pip 组件 [需网络连接]... 
    echo.
    powershell -NoProfile -Command "$ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py' -UseBasicParsing -ErrorAction Stop"
    if errorlevel 1 (
        echo [ERROR] Failed to download get-pip.py. Please check your internet connection.
        echo         下载 get-pip.py 失败，请检查网络连接。
        pause
        exit /b 1
    )
    
    "%PYTHON_EXE%" get-pip.py --no-warn-script-location
    if errorlevel 1 (
        echo [ERROR] Failed to install pip.
        echo         pip 安装失败。
        pause
        exit /b 1
    )
    del get-pip.py
)

REM 4. Install Dependencies
echo.
echo [INFO] Checking dependencies [edge-tts, flask, etc.]...
echo       正在检查依赖组件...
echo.
echo [STEP] Installing dependencies... >> "%LOGFILE%"
"%PYTHON_EXE%" -m pip install -r requirements.txt --no-warn-script-location 2>> "%LOGFILE%"
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies from requirements.txt.
    echo         依赖组件安装失败。
    echo Please check your internet connection.
    echo 请检查网络连接。
    echo [ERROR] pip install failed >> "%LOGFILE%"
    pause
    exit /b 1
)
echo [OK] Dependencies installed >> "%LOGFILE%"

REM 5. Check if ASR model needs downloading
if exist "models\sensevoice-small-int8\model.int8.onnx" goto :skip_model_download

echo.
echo ========================================================
echo  FIRST TIME SETUP: ASR Model Download
echo  首次运行：语音识别模型下载
echo ========================================================
echo.
echo The Speech-to-Text feature requires a ~244 MB model download.
echo 语音转文字功能需要下载约 244 MB 的语音识别模型。
echo.
echo [Y] Download now / 立即下载
echo [N] Skip - you can download later from the app / 跳过
echo ========================================================
choice /C YN /T 30 /D N /M "Select / 请选择:"
if errorlevel 2 goto :skip_model_download

echo Downloading ASR model...
echo 正在下载语音识别模型...
"%PYTHON_EXE%" download_model.py
echo.

:skip_model_download

echo.
echo ========================================================
echo DO YOU WANT TO ALLOW OTHER DEVICES ON YOUR NETWORK TO ACCESS THIS SERVER?
echo 是否允许局域网内其他设备（如手机、平板）访问本服务器？ 
echo [Y] Yes / 允许 (Host on 0.0.0.0)
echo [N] No / 拒绝 (Host on 127.0.0.1 - Default / 默认)
echo ========================================================
choice /C YN /T 10 /D N /M "Select / 请选择:"
if errorlevel 2 (
    set "HOST=127.0.0.1"
) else (
    set "HOST=0.0.0.0"
)

echo.
echo Starting Bashi Voice Factory...
echo 正在启动 Bashi Voice Factory...

if "!HOST!"=="0.0.0.0" (
    set "LOCAL_IP="
    for /f "usebackq tokens=*" %%a in (`powershell -NoProfile -Command "(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null -and $_.NetAdapter.Status -eq 'Up' } | Select-Object -ExpandProperty IPv4Address | Select-Object -First 1).IPAddress" 2^>nul`) do set "LOCAL_IP=%%a"
    if not defined LOCAL_IP (
        for /f "tokens=2 delims=:" %%a in ('ipconfig ^| find "IPv4"') do if not defined LOCAL_IP set "LOCAL_IP=%%a"
        if not defined LOCAL_IP for /f "tokens=2 delims=:" %%a in ('ipconfig ^| find "IPv4 地址"') do if not defined LOCAL_IP set "LOCAL_IP=%%a"
        if defined LOCAL_IP set "LOCAL_IP=!LOCAL_IP: =!"
    )
    
    echo.
    echo --------------------------------------------------------
    echo Server is accessible from other devices at:
    echo 可以从局域网其他设备访问此地址: 
    if defined LOCAL_IP (
        echo http://!LOCAL_IP!:5050
    ) else (
        echo http://YOUR_LOCAL_IP:5050
    )
    echo.
    echo * Note: If your phone warns "Not Secure" ^(non-HTTPS^),
    echo   please ignore it. It's safe on your local Wi-Fi.
    echo * 提示: 手机浏览器若提示“不安全/非HTTPS”，
    echo   请放心忽略并点继续，本地局域网连接是安全的。
    echo --------------------------------------------------------
    echo.
) else (
    echo.
    echo --------------------------------------------------------
    echo Server is running locally. Access it at:
    echo 服务器运行在本地模式。请访问: 
    echo http://127.0.0.1:5050
    echo --------------------------------------------------------
    echo.
)

echo Press Ctrl+C to stop the server.
echo 按 Ctrl+C 可停止服务器。
echo.

REM Start the Python server
echo [STEP] Starting app.py with host=!HOST! >> "%LOGFILE%"
"%PYTHON_EXE%" app.py --host "!HOST!" 2>> "%LOGFILE%"
set "EXIT_CODE=!ERRORLEVEL!"
echo [DONE] app.py exited with code !EXIT_CODE! >> "%LOGFILE%"

echo.
echo App exited. (Exit code: !EXIT_CODE!)
echo 程序已退出。（退出代码: !EXIT_CODE!）
echo.
echo If the app crashed, check launch_log.txt for details.
echo 如果程序异常退出，请查看 launch_log.txt 了解详情。
pause
