#!/usr/bin/env python3
"""
GUI para selección y visualización de eventos de un archivo miniSEED,
con resampleo a 100 Hz, selección de canal, hora de inicio basada en metadata,
rango completo de tiempos, desplazamiento en segundos, lectura de posición del mouse,
funcionalidad centrado de evento sin línea auxiliar.
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
fig, ax, canvas = None, None, None
centrar_mode = False

# --- Funciones de la GUI ---
def cerrar():
    ventana.quit(); ventana.destroy(); sys.exit(0)

def toggle_centrar():
    global centrar_mode
    centrar_mode = not centrar_mode
    if centrar_mode:
        btn_centrar.config(relief=tk.SUNKEN, text='Centrar: ON')
        lbl_pos.config(text='Δ: --')
    else:
        btn_centrar.config(relief=tk.RAISED, text='Centrar: OFF')
        lbl_pos.config(text='Posición: --')

# Evento clic para centrar un punto (sin dibujar línea)
def on_click(event):
    if not centrar_mode or event.inaxes is None:
        return
    x_click = event.xdata
    dur = float(spin_duracion.get()); center = dur/2.0
    delta = x_click - center
    entry_shift.delete(0, tk.END)
    entry_shift.insert(0, f"{delta:.3f}")
    toggle_centrar()

# Movimiento del mouse: mostrar delta o posición
def on_mouse_move(event):
    if centrar_mode and event.inaxes and event.xdata is not None:
        dur = float(spin_duracion.get()); center = dur/2.0
        delta = event.xdata - center
        lbl_pos.config(text=f"Δ: {delta:+.3f} s")
    elif event.inaxes and event.xdata is not None:
        lbl_pos.config(text=f"Posición: {event.xdata:.3f} s")
    else:
        lbl_pos.config(text="Posición: --")

# Abrir archivo y resamplear a 100 Hz
def abrir_archivo():
    global resampled_stream, file_starttime
    fn = filedialog.askopenfilename(
        title="Selecciona un mseed",
        initialdir=os.path.join(PROJECT_LOCAL_ROOT, "resultados", "mseed"),
        filetypes=[("MiniSEED","*.mseed"),("Todos","*.*")]
    )
    if not fn: return
    entry_archivo.delete(0, tk.END); entry_archivo.insert(0, fn)
    try:
        s = read(fn); s.resample(100.0); resampled_stream = s
        st = s[0].stats.starttime; et = s[0].stats.endtime; file_starttime = st
        date = st.date; start_str = st.datetime.strftime('%H:%M:%S'); end_str = et.datetime.strftime('%H:%M:%S')
        lbl_fecha.config(text=f"Fecha: {date}   Inicio: {start_str}   Fin: {end_str}")
        entry_hora.delete(0, tk.END); entry_hora.insert(0, start_str)
        entry_shift.delete(0, tk.END); entry_shift.insert(0, "0")
    except Exception as e:
        messagebox.showerror("Error apertura", str(e)); resampled_stream = None

# Previsualizar con desplazamiento vigente
def previsualizar():
    global fig, ax, canvas, centrar_mode
    if resampled_stream is None:
        messagebox.showwarning("Aviso", "Primero abre un archivo mseed."); return
    raw_hora = entry_hora.get().split(',')[0]
    try: hora_dt = datetime.strptime(raw_hora, '%H:%M:%S').time()
    except: messagebox.showerror("Error", "Formato de hora inicio inválido."); return
    try:
        dur = float(spin_duracion.get()); shift_sec = float(entry_shift.get())
    except ValueError:
        messagebox.showerror("Error", "Duración o desplazamiento no válidos."); return
    shift_delta = timedelta(seconds=shift_sec)
    canal = channel_var.get()
    base_dt = datetime.combine(file_starttime.date, hora_dt) + shift_delta
    t0 = UTCDateTime(base_dt); t1 = t0 + dur
    segment = resampled_stream.slice(starttime=t0, endtime=t1).select(channel=canal)
    if not segment:
        messagebox.showwarning("Sin datos","No hay datos en el intervalo especificado."); return
    # actualizar hora inicio y reset desplazamiento
    new_str = base_dt.strftime('%H:%M:%S') + f",{int(base_dt.microsecond/1000):03d}"
    entry_hora.delete(0, tk.END); entry_hora.insert(0, new_str)
    entry_shift.delete(0, tk.END); entry_shift.insert(0, "0")
    centrar_mode = False; btn_centrar.config(relief=tk.RAISED, text='Centrar: OFF'); lbl_pos.config(text='Posición: --')
    # limpiar gráfico anterior
    for w in frame_plot.winfo_children(): w.destroy()
    fig, ax = plt.subplots(figsize=(6,3))
    for tr in segment: ax.plot(tr.times(), tr.data, label=tr.stats.channel)
    center = dur/2.0; ax.axvline(center, color='r')
    dtc = (t0 + center).datetime
    lbl_centro.config(text=f"Centro: {dtc.strftime('%H:%M:%S')},{int(dtc.microsecond/1000):03d}")
    ax.set_xlabel('Tiempo (s)'); ax.set_ylabel('Amplitud'); ax.set_title(os.path.basename(entry_archivo.get()))
    ax.set_xlim(0, dur); ax.legend(loc='upper right', fontsize='small')
    canvas = FigureCanvasTkAgg(fig, master=frame_plot)
    canvas.get_tk_widget().pack(fill='both', expand=True)
    canvas.mpl_connect('motion_notify_event', on_mouse_move)
    canvas.mpl_connect('button_press_event', on_click)
    canvas.draw()

# --- Configuración de la ventana ---
ventana = tk.Tk(); ventana.title("Extracción de Eventos - GPD"); ventana.geometry("800x600"); ventana.protocol("WM_DELETE_WINDOW", cerrar)
# Frame archivo
frame_file = tk.Frame(ventana); frame_file.pack(fill='x', pady=5)
# Widgets selección de archivo
tk.Label(frame_file,text="Archivo mseed:").pack(side='left',padx=5)
entry_archivo=tk.Entry(frame_file,width=50); entry_archivo.pack(side='left',padx=5)
btn_abrir=tk.Button(frame_file,text="Abrir…",command=abrir_archivo); btn_abrir.pack(side='left',padx=5)
lbl_fecha=tk.Label(frame_file,text="Fecha: --   Inicio: --   Fin: --"); lbl_fecha.pack(side='left',padx=10)
# Frame parámetros
frame_param=tk.Frame(ventana); frame_param.pack(fill='x',pady=5)
tk.Label(frame_param,text="Hora inicio (hh:mm:ss):").grid(row=0,column=0,padx=5,sticky='e')
entry_hora=tk.Entry(frame_param,width=14); entry_hora.grid(row=0,column=1,padx=5)
tk.Label(frame_param,text="Duración (s):").grid(row=0,column=2,padx=5,sticky='e')
spin_duracion=tk.Spinbox(frame_param,from_=0.1,to=600,increment=0.1,width=6); spin_duracion.grid(row=0,column=3,padx=5)
tk.Label(frame_param,text="Desplazamiento (s):").grid(row=1,column=0,padx=5,sticky='e')
entry_shift=tk.Entry(frame_param,width=6); entry_shift.insert(0,"0"); entry_shift.grid(row=1,column=1,padx=5,sticky='w')
tk.Label(frame_param,text="Canal:").grid(row=1,column=2,padx=5,sticky='e')
channel_var=tk.StringVar(value="ENT"); tk.OptionMenu(frame_param,channel_var,"ENT","ENR","ENV").grid(row=1,column=3,padx=5,sticky='w')
# Frame acciones
frame_actions=tk.Frame(ventana); frame_actions.pack(pady=10)
btn_previsualizar=tk.Button(frame_actions,text="Previsualizar",command=previsualizar); btn_previsualizar.pack(side='left',padx=10)
btn_centrar=tk.Button(frame_actions,text="Centrar: OFF",command=toggle_centrar); btn_centrar.pack(side='left',padx=10)
btn_salir=tk.Button(frame_actions,text="Salir",command=cerrar,fg='white',bg='red'); btn_salir.pack(side='left',padx=10)
lbl_centro=tk.Label(frame_actions,text="Centro: --"); lbl_centro.pack(side='left',padx=10)
lbl_pos=tk.Label(frame_actions,text="Posición: --"); lbl_pos.pack(side='left',padx=10)
# Frame plot
frame_plot=tk.Frame(ventana); frame_plot.pack(fill='both',expand=True,pady=5)
ventana.mainloop()
