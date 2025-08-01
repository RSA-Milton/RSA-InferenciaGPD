#!/home/rsa/git/RSA-InferenciaGPD/venv/bin/python
"""
Script para visualizar una ventana de tiempo específica de un archivo miniSEED,
utilizando las rutas definidas en el archivo .env del proyecto.

Uso:
    python visualizar_evento.py <archivo_mseed> <inicio_iso8601> <duracion_segundos>
Ejemplo:
    python visualizar_evento.py evento_20230705_123456.mseed 2024-07-29T03:45:12 60
"""

import os
import sys

# Validar si tkinter está disponible antes de importar matplotlib y obspy
def verificar_tkinter():
    try:
        import tkinter
    except ImportError:
        print(
            "ERROR: No se encontró el módulo 'tkinter'.\n"
            "Por favor, instale 'python3-tk' usando:\n"
            "  sudo apt install python3-tk\n"
            "y vuelva a ejecutar este script."
        )
        sys.exit(1)

verificar_tkinter()

from dotenv import load_dotenv, find_dotenv
from obspy import read, UTCDateTime

# 1. Leer variables de entorno
env_file = find_dotenv()
if not env_file:
    print("ERROR: Archivo .env no encontrado en la raíz del proyecto.")
    sys.exit(1)
load_dotenv(env_file)

PROJECT_LOCAL_ROOT = os.getenv("PROJECT_LOCAL_ROOT")
if not PROJECT_LOCAL_ROOT:
    print("ERROR: PROJECT_LOCAL_ROOT no definido en el archivo .env.")
    sys.exit(1)

# 2. Leer parámetros de entrada
if len(sys.argv) != 4:
    print("Uso: python visualizar_evento.py <archivo_mseed> <inicio_iso8601> <duracion_segundos>")
    sys.exit(1)

nombre_archivo = sys.argv[1]
timestamp_inicio = sys.argv[2]
duracion = float(sys.argv[3])

# 3. Construir ruta completa al archivo mseed
ruta_mseed = os.path.join(PROJECT_LOCAL_ROOT, "resultados", "mseed", nombre_archivo)
if not os.path.isfile(ruta_mseed):
    print(f"ERROR: El archivo mseed no existe: {ruta_mseed}")
    sys.exit(1)

# 4. Leer archivo y recortar al intervalo deseado
try:
    stream = read(ruta_mseed)
    inicio = UTCDateTime(timestamp_inicio)
    fin = inicio + duracion
    stream_recortado = stream.slice(starttime=inicio, endtime=fin)
except Exception as e:
    print(f"ERROR al leer o recortar el archivo: {e}")
    sys.exit(1)

# 5. Depuración y visualización
print(f"Mostrando segmento: {stream_recortado}")
if len(stream_recortado) == 0:
    print("No se encontraron datos en el intervalo especificado.")
    sys.exit(1)

# Importar matplotlib después de la verificación de tkinter
import matplotlib
matplotlib.use('TkAgg')

stream_recortado.plot()
