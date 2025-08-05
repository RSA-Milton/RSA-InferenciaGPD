#!/usr/bin/env python3
"""
GUI para selección y visualización de eventos de un archivo miniSEED,
con resampleo a 100 Hz, selección de canal, hora de inicio basada en metadata,
rango completo de tiempos, desplazamiento en segundos, y lectura de posición del mouse.
"""
import os
import sys
from datetime import datetime, timedelta, time as dt_time
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

# --- Variables globales ---
resampled_stream = None
file_starttime = None
fig, ax = None, None
canvas = None

# --- Cierre seguro ---
def cerrar():
    ventana.quit()
    ventana.destroy()
    sys.exit(0)

# --- Funcción de movimiento del mouse ---
def on_mouse_move(event):
    if event.inaxes and event.xdata is not None:
        x = event.xdata
        lbl_pos.config(text=f"Posición: {x:.3f} s")
    else:
        lbl_pos.config(text="Posición: --")

# --- Abrir archivo y cargar metadata ---
def abrir_archivo():
    global resampled_stream, file_starttime
    fn = filedialog.askopenfilename(
        title="Selecciona un mseed",
        initialdir=os.path.join(PROJECT_LOCAL_ROOT, "resultados", "mseed"),
        filetypes=[("MiniSEED","*.mseed"),("Todos","*.*")]
    )
    if not fn:
        return
    entry_archivo.delete(0, tk.END)
    entry_archivo.insert(0, fn)
    try:
        s = read(fn)
        s.resample(100.0)
        resampled_stream = s
        st = s[0].stats.starttime
        et = s[0].stats.endtime
        file_starttime = st
        date = st.date
        start_str = st.datetime.strftime('%H:%M:%S')
        end_str = et.datetime.strftime('%H:%M:%S')
        lbl_fecha.config(text=f"Fecha: {date}   Inicio: {start_str}   Fin: {end_str}")
        entry_hora.delete(0, tk.END)
        entry_hora.insert(0, start_str)
        entry_shift.delete(0, tk.END)
        entry_shift.insert(0, "0")
    except Exception as e:
        messagebox.showerror("Error apertura", str(e))
        resampled_stream = None

# --- Previsualizar evento seleccionado ---
def previsualizar():
    global resampled_stream, file_starttime, fig, ax, canvas
    if resampled_stream is None:
        messagebox.showwarning("Aviso", "Primero abre un archivo mseed.")
        return
    raw_hora = entry_hora.get()
    # Parse hora con opcional milisegundos
    try:
        if ',' in raw_hora:
            main, ms = raw_hora.split(',')
            t = datetime.strptime(main, '%H:%M:%S').time()
            micro = int(ms) * 1000
            hora_dt = dt_time(t.hour, t.minute, t.second, micro)
        else:
            hora_dt = datetime.strptime(raw_hora, '%H:%M:%S').time()
    except Exception:
        messagebox.showerror("Error", "Formato de hora inicio inválido. Use hh:mm:ss o hh:mm:ss,ms")
        return
    try:
        dur = float(spin_duracion.get())
        shift_sec = float(entry_shift.get())
    except ValueError:
        messagebox.showerror("Error", "Duración o desplazamiento no válidos.")
        return
    shift_delta = timedelta(seconds=shift_sec)
    canal = channel_var.get()

    try:
        date = file_starttime.date
        base_dt = datetime.combine(date, hora_dt)
        full_dt = base_dt + shift_delta
        t0 = UTCDateTime(full_dt)
        t1 = t0 + dur
        segment = resampled_stream.slice(starttime=t0, endtime=t1)
        segment = segment.select(channel=canal)
    except Exception as e:
        messagebox.showerror("Error lectura/recorte", str(e))
        return

    if len(segment) == 0:
        messagebox.showwarning("Sin datos", "No hay datos en el intervalo especificado.")
        return

    # Actualizar hora inicio y reset desplazamiento
    new_str = full_dt.strftime('%H:%M:%S') + f",{int(full_dt.microsecond/1000):03d}"
    entry_hora.delete(0, tk.END)
    entry_hora.insert(0, new_str)
    entry_shift.delete(0, tk.END)
    entry_shift.insert(0, "0")

    # Limpiar área de gráfico
    for w in frame_plot.winfo_children():
        w.destroy()

    # Graficar traza
    fig, ax = plt.subplots(figsize=(6,3))
    for tr in segment:
        times = tr.times()
        ax.plot(times, tr.data, label=tr.stats.channel)
    center = dur / 2
    ax.axvline(center, color='r')
    center_time = t0 + center
    dtc = center_time.datetime
    centro_str = dtc.strftime('%H:%M:%S') + f",{int(dtc.microsecond/1000):03d}"
    lbl_centro.config(text=f"Centro: {centro_str}")
    ax.set_title(os.path.basename(entry_archivo.get()))
    ax.set_xlabel('Tiempo (s)')
    ax.set_ylabel('Amplitud')
    ax.set_xlim(0, dur)
    ax.legend(loc='upper right', fontsize='small')

    # Incrustar canvas y conectar evento de mouse
    canvas = FigureCanvasTkAgg(fig, master=frame_plot)
    canvas.get_tk_widget().pack(fill="both", expand=True)
    canvas.mpl_connect('motion_notify_event', on_mouse_move)
    canvas.draw()

# --- Configurar ventana ---
ventana = tk.Tk()
ventana.title("Extracción de Eventos - GPD")
ventana.geometry("800x600")
ventana.protocol("WM_DELETE_WINDOW", cerrar)

# --- Frame archivo ---
frame_file = tk.Frame(ventana)
frame_file.pack(fill="x", pady=5)

import tkinter as _tk

tk.Label(frame_file, text="Archivo mseed:").pack(side="left", padx=5)
entry_archivo = tk.Entry(frame_file, width=50)
entry_archivo.pack(side="left", padx=5)
btn_abrir = tk.Button(frame_file, text="Abrir…", command=abrir_archivo)
btn_abrir.pack(side="left", padx=5)

lbl_fecha = tk.Label(frame_file, text="Fecha: --   Inicio: --   Fin: --")
lbl_fecha.pack(side="left", padx=10)

# --- Frame parámetros ---
frame_param = tk.Frame(ventana)
frame_param.pack(fill="x", pady=5)

tk.Label(frame_param, text="Hora inicio (hh:mm:ss):").grid(row=0, column=0, padx=5, sticky="e")
entry_hora = tk.Entry(frame_param, width=14)
entry_hora.grid(row=0, column=1, padx=5)

tk.Label(frame_param, text="Duración (s):").grid(row=0, column=2, padx=5, sticky="e")
spin_duracion = tk.Spinbox(frame_param, from_=0.1, to=600, increment=0.1, width=6)
spin_duracion.grid(row=0, column=3, padx=5)

tk.Label(frame_param, text="Desplazamiento (s):").grid(row=1, column=0, padx=5, sticky="e")
entry_shift = tk.Entry(frame_param, width=6)
entry_shift.insert(0, "0")
entry_shift.grid(row=1, column=1, padx=5, sticky="w")

tk.Label(frame_param, text="Canal:").grid(row=1, column=2, padx=5, sticky="e")
channel_var = tk.StringVar(value="ENT")
drop_channel = tk.OptionMenu(frame_param, channel_var, "ENT", "ENR", "ENV")
drop_channel.grid(row=1, column=3, padx=5, sticky="w")

# --- Frame acciones ---
frame_actions = tk.Frame(ventana)
frame_actions.pack(pady=10)
btn_previsualizar = tk.Button(frame_actions, text="Previsualizar", command=previsualizar)
btn_previsualizar.pack(side="left", padx=10)
btn_salir = tk.Button(frame_actions, text="Salir", command=cerrar, fg="white", bg="red")
btn_salir.pack(side="left", padx=10)
lbl_centro = tk.Label(frame_actions, text="Centro: --")
lbl_centro.pack(side="left", padx=10)
lbl_pos = tk.Label(frame_actions, text="Posición: --")
lbl_pos.pack(side="left", padx=10)

# --- Frame plot ---
frame_plot = tk.Frame(ventana)
frame_plot.pack(fill="both", expand=True, pady=5)

ventana.mainloop()
