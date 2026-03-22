#!/bin/bash
# =======================================================
# Bashi Voice Factory v3.0 - Linux/macOS Launcher (VENV)
# - Creates/uses .venv in the app folder
# - Installs requirements.txt into that venv
# - Runs the app with the venv Python
# =======================================================

echo "============================================"
echo " Bashi Voice Factory v3.0 (venv launcher)"
echo "============================================"
echo ""

# Change to the script's directory
cd "$(dirname "$0")" || exit 1

# --- Find Python 3 ---
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python 3 not found."
    echo "Please install Python 3.8 or newer."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macOS: Download from https://www.python.org/downloads/mac-osx/"
    else
        echo "Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    fi
    exit 1
fi

# Note: many Linux distros require the python3-venv package (which provides ensurepip)
if ! $PYTHON_CMD -c "import venv, ensurepip" &> /dev/null; then
    echo "[WARNING] Python 'venv' or 'ensurepip' module is missing. This is required to run the app."
    
    # Try to auto-install on Debian/Ubuntu/Mint
    if command -v apt &> /dev/null; then
        # Get exact python minor version (e.g. 3.10, 3.12)
        PY_VER=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        VENV_PKG="python${PY_VER}-venv"
        
        echo ""
        echo "It seems you are on a Debian/Ubuntu-based system."
        read -p "Would you like to automatically install '${VENV_PKG}'? (Requires sudo password) [y/N]: " auto_install
        
        if [[ "$auto_install" =~ ^[Yy]$ ]]; then
            echo "[INFO] Running: sudo apt update && sudo apt install -y ${VENV_PKG}"
            sudo apt update && sudo apt install -y "${VENV_PKG}"
            
            # Verify if installation succeeded
            if ! $PYTHON_CMD -c "import venv, ensurepip" &> /dev/null; then
                echo "[ERROR] Auto-installation failed or was cancelled."
                echo "Please install it manually: sudo apt install ${VENV_PKG}"
                exit 1
            fi
            echo "[INFO] Successfully installed ${VENV_PKG}!"
            echo ""
        else
            echo "[ERROR] Cannot continue without ${VENV_PKG}. Exiting."
            exit 1
        fi
    else
        echo "[ERROR] python3-venv module is not installed."
        echo "Please install it manually via your package manager (e.g. dnf, yum, pacman)."
        exit 1
    fi
fi

# --- Create Virtual Environment if missing ---
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating virtual environment in .venv ..."
    $PYTHON_CMD -m venv .venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment."
        rm -rf .venv  # Clean up the broken stub so the next run triggers correctly
        exit 1
    fi
fi

# --- Path to venv Python ---
PYTHON_VENV=".venv/bin/python"

# Check if pip is available inside venv
if [ ! -f "$PYTHON_VENV" ]; then
    echo "[ERROR] Sub-python inside .venv not found. Venv creation might have failed."
    exit 1
fi

# --- Check if dependencies already installed ---
$PYTHON_VENV -c "import flask, edge_tts, imageio_ffmpeg" >/dev/null 2>&1
if [ $? -eq 0 ]; then
    # Already installed
    true
else
    echo "[INFO] Installing / updating dependencies..."
    
    # 1. Fallback: If pip is missing from the venv (common in Debian/Ubuntu split packages), try to bootstrap it
    if ! $PYTHON_VENV -m pip --version >/dev/null 2>&1; then
        echo "[INFO] pip is missing in venv. Bootstrapping via ensurepip..."
        $PYTHON_VENV -m ensurepip --upgrade >/dev/null 2>&1
    fi

    # 2. Use python -m pip to bypass missing "pip" executable links
    $PYTHON_VENV -m pip install --upgrade pip
    $PYTHON_VENV -m pip install -r requirements.txt
    
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install dependencies."
        echo "If pip is completely missing, try: sudo apt install python3-pip python3-venv"
        echo "Then delete the .venv folder and restart this script."
        exit 1
    fi
    echo "[INFO] Dependencies installed successfully."
fi

# --- Run the App ---
echo ""
echo "========================================================"
echo "DO YOU WANT TO ALLOW OTHER DEVICES ON YOUR NETWORK TO ACCESS THIS SERVER?"
echo "是否允许局域网内其他设备（如手机、平板）访问本服务器？"
echo "[y] Yes / 允许 (Host on 0.0.0.0)"
echo "[n] No / 拒绝 (Host on 127.0.0.1 - Default / 默认)"
echo "Will default to [n] in 10 seconds. / 10秒后默认选择[n]"
echo "========================================================"

read -t 10 -p "Select / 请选择 [y/N]: " allow_network

HOST="127.0.0.1"
if [[ "$allow_network" =~ ^[Yy]$ ]]; then
    HOST="0.0.0.0"
fi

if [ "$HOST" = "0.0.0.0" ]; then
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -z "$LOCAL_IP" ]; then
        LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null) # macOS fallback
    fi
    if [ -z "$LOCAL_IP" ]; then
        LOCAL_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7}')
    fi
    if [ -z "$LOCAL_IP" ]; then
        LOCAL_IP="YOUR_LOCAL_IP"
    fi
    echo ""
    echo "--------------------------------------------------------"
    echo "Server is accessible from other devices at:"
    echo "可以从局域网其他设备访问此地址:"
    echo "http://$LOCAL_IP:5050"
    echo ""
    echo "* Note: If your phone warns 'Not Secure' (non-HTTPS),"
    echo "  please ignore it. It's safe on your local Wi-Fi."
    echo "* 提示: 手机浏览器若提示'不安全/非HTTPS'，"
    echo "  请放心忽略并点继续，本地局域网连接是安全的。"
    echo "--------------------------------------------------------"
else
    echo ""
    echo "--------------------------------------------------------"
    echo "Server is running locally. Access it at:"
    echo "服务器运行在本地模式。请访问:"
    echo "http://127.0.0.1:5050"
    echo "--------------------------------------------------------"
fi

echo "[INFO] Press CTRL+C to quit."
echo "============================================"
echo ""

$PYTHON_VENV app.py --host "$HOST"
