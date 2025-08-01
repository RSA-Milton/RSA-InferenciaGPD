# InferenciaGPD-RSA

Este proyecto implementa un sistema de inferencia de eventos sísmicos utilizando el modelo Generalized Phase Detection (GPD), desplegado en servidores de la Red Sísmica del Austro (RSA).

## Estructura del proyecto

InferenciaGPD-RSA/
├── configuracion/         # Archivos de configuración (JSON, YAML, etc.)
├── models/                # Modelos de IA (ej. .tflite, .h5)
├── scripts/               # Scripts del sistema
│   ├── setup/             # Instaladores y scripts de preparación
│   ├── inference/         # Scripts principales de inferencia
│   ├── utils/             # Funciones auxiliares reutilizables
│   └── menu.sh            # Menú interactivo para ejecutar el sistema
├── venv/                  # Entorno virtual de Python (no se sube al repo)
├── .env                   # Variables de entorno con rutas y configuraciones
├── .gitignore             # Exclusiones para Git (ignora venv/, logs, etc.)
├── requirements.txt       # Dependencias de Python para entorno virtual
└── README.md              # Documentación general del proyecto
