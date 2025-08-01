#!/bin/bash
set -e

PROJECT_DIR=~/git/InferenciaGPD-RSA
ENV_DIR="$PROJECT_DIR/venv"

echo "Instalando paquetes del sistema..."
sudo apt update && sudo apt install -y python3-venv python3-pip python3-dev \
    build-essential libatlas-base-dev libopenblas-dev gfortran \
    libproj-dev proj-data proj-bin

echo "Creando entorno virtual en $ENV_DIR"
python3 -m venv "$ENV_DIR"
source "$ENV_DIR/bin/activate"

echo "Instalando dependencias desde requirements.txt"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

echo "Entorno configurado. ObsPy versión:"
python -c "import obspy; print(obspy.__version__)"
