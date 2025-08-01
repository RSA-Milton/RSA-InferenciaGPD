#!/usr/bin/env python3
"""
GUI para selección y visualización de eventos de un archivo miniSEED,
con selección de canal y hora de inicio basada en metadata.
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
import tkinter as tk
from tkinter import filedialog, messagebox
from obspy import read, UTCDateTime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

# --- Leer variables de entorno ---
load_dotenv(find_dotenv())
PROJECT_LOCAL_ROOT = os.getenv("PROJECT_LOCAL_ROOT")
if not PROJECT_LOCAL_ROOT:
    print("ERROR: PROJECT_LOCAL_ROOT no definido en .env")
    sys.exit(1)

# --- Función de cierre seguro ---
def cerrar():
    ventana.quit()
    ventana.destroy()
    sys.exit(0)

# --- Función Abrir archivo ---
def abrir_archivo():
    fn = filedialog.askopenfilename(
        title="Selecciona un mseed",
        initialdir=os.path.join(PROJECT_LOCAL_ROOT, "resultados", "mseed"),
        filetypes=[("MiniSEED","*.mseed"),("Todos","*.*")]
    )
    if fn:
        entry_archivo.delete(0, tk.END)
        entry_archivo.insert(0, fn)
        # Obtener fecha de metadata
        try:
            s = read(fn)
            date = s[0].stats.starttime.date
            entry_hora.delete(0, tk.END)
            entry_hora.insert(0, "00:00:00")
            lbl_fecha.config(text=f"Fecha: {date}")
        except:
            lbl_fecha.config(text="Fecha: desconocida")

# --- Función Previsualizar evento ---
def previsualizar():
    archivo = entry_archivo.get()
    hora_str = entry_hora.get()
    dur = float(spin_duracion.get())
    shift_ms = int(entry_shift.get())
    shift = shift_ms / 1000.0
    canal = channel_var.get()

    if not os.path.isfile(archivo):
        messagebox.showerror("Error", f"Archivo no encontrado:\n{archivo}")
        return

    try:
        stream = read(archivo)
        # Fecha de metadata
        date = stream[0].stats.starttime.date
        # Construir timestamp completo
        full_ts = f"{date.isoformat()}T{hora_str}"
        t0 = UTCDateTime(full_ts) + shift
        t1 = t0 + dur
        segment = stream.slice(starttime=t0, endtime=t1)
        # Filtrar canal
        segment = segment.select(channel=canal)
    except Exception as e:
        messagebox.showerror("Error lectura/recorte", str(e))
        return

    if len(segment) == 0:
        messagebox.showwarning("Sin datos", "No hay datos en el intervalo especificado.")
        return

    # limpiar área de plot
    for widget in frame_plot.winfo_children():
        widget.destroy()

    # graficar
    fig, ax = plt.subplots(figsize=(6,3))
    for tr in segment:
        times = tr.times()  # segundos relativos
        ax.plot(times, tr.data, label=tr.stats.channel)
    # línea central
    center = dur / 2
    ax.axvline(center, color='r')
    ax.set_title(os.path.basename(archivo))
    ax.set_xlabel('Tiempo (s)')
    ax.set_ylabel('Amplitud')
    ax.legend(loc='upper right', fontsize='small')

    canvas = FigureCanvasTkAgg(fig, master=frame_plot)
    canvas.get_tk_widget().pack(fill="both", expand=True)
    canvas.draw()

# --- Crear ventana principal ---
ventana = tk.Tk()
ventana.title("Extracción de Eventos - GPD")
ventana.geometry("800x600")
ventana.protocol("WM_DELETE_WINDOW", cerrar)

# --- Frame de selección de archivo ---
frame_file = tk.Frame(ventana)
frame_file.pack(fill="x", pady=5)

tk.Label(frame_file, text="Archivo mseed:").pack(side="left", padx=5)
entry_archivo = tk.Entry(frame_file, width=50)
entry_archivo.pack(side="left", padx=5)
btn_abrir = tk.Button(frame_file, text="Abrir…", command=abrir_archivo)
btn_abrir.pack(side="left", padx=5)

lbl_fecha = tk.Label(frame_file, text="Fecha: --")
lbl_fecha.pack(side="left", padx=10)

# --- Frame de parámetros de evento ---
frame_param = tk.Frame(ventana)
frame_param.pack(fill="x", pady=5)

tk.Label(frame_param, text="Hora inicio (hh:mm:ss):").grid(row=0, column=0, padx=5, sticky="e")
entry_hora = tk.Entry(frame_param, width=10)
entry_hora.grid(row=0, column=1, padx=5)

# Duración (s)
tk.Label(frame_param, text="Duración (s):").grid(row=0, column=2, padx=5, sticky="e")
spin_duracion = tk.Spinbox(frame_param, from_=0.1, to=600, increment=0.1, width=6)
spin_duracion.grid(row=0, column=3, padx=5)

# Desplazamiento (ms)
tk.Label(frame_param, text="Desplazamiento (ms):").grid(row=1, column=0, padx=5, sticky="e")
entry_shift = tk.Entry(frame_param, width=6)
entry_shift.insert(0, "0")
entry_shift.grid(row=1, column=1, padx=5, sticky="w")

# Canal a visualizar
tk.Label(frame_param, text="Canal:").grid(row=1, column=2, padx=5, sticky="e")
channel_var = tk.StringVar(value="ENT")
drop_channel = tk.OptionMenu(frame_param, channel_var, "ENT", "ENR", "ENV")
drop_channel.grid(row=1, column=3, padx=5, sticky="w")

# --- Frame de acciones ---
frame_actions = tk.Frame(ventana)
frame_actions.pack(pady=10)
btn_previsualizar = tk.Button(frame_actions, text="Previsualizar", command=previsualizar)
btn_previsualizar.pack(side="left", padx=10)
btn_salir = tk.Button(frame_actions, text="Salir", command=cerrar, fg="white", bg="red")
btn_salir.pack(side="left", padx=10)

# --- Frame para plot ---
frame_plot = tk.Frame(ventana)
frame_plot.pack(fill="both", expand=True, pady=5)

# --- Iniciar bucle de la GUI ---
ventana.mainloop()
