# Procesador de Paquetes Alimentarios — El Raizal

Herramienta interna para limpiar, estandarizar y consolidar
los archivos Excel mensuales de entregas de paquetes alimentarios,
listos para subir a Power BI.

---

## Estructura del proyecto

```
raizal_v2/
├── backend/
│   ├── app.py          # Servidor Flask (rutas y arranque)
│   └── pipeline.py     # Lógica ETL: limpieza y estandarización
├── frontend/
│   └── public/
│       ├── index.html  # Interfaz visual
│       ├── style.css   # Estilos
│       └── app.js      # Lógica del navegador
├── scripts/
│   └── build.py        # Genera el .exe para Windows
├── requirements.txt    # Dependencias Python
└── README.md
```

---

## Opción A — Generar el .exe (para entregar al coordinador)

### Requisitos
- Windows 10 / 11
- Python 3.10+ instalado con "Add to PATH" marcado

### Pasos
```bash
# 1. Abrir terminal en la carpeta raizal_v2/
# 2. Ejecutar:
python scripts/build.py
```

El `.exe` quedará en `dist/PaquetesAlimentarios_Raizal.exe`.

Ese único archivo es todo lo que necesita el coordinador.
**No requiere Python instalado, no requiere nada más.**

---

## Opción B — Correr en modo desarrollo

```bash
# Instalar dependencias
pip install -r requirements.txt

# Iniciar el servidor
python backend/app.py
```

Luego abrir: http://localhost:5050

---

## Uso (coordinador)

1. Doble clic en `PaquetesAlimentarios_Raizal.exe`
2. El navegador se abre automáticamente
3. Seleccionar mes y año
4. Arrastrar los archivos Excel del mes (1–4 archivos)
5. Clic en **"Procesar y consolidar archivos"**
6. Revisar advertencias si las hay
7. Descargar el Excel consolidado y subirlo a Power BI

---

## Qué hace el procesamiento (Python)

| Paso | Descripción |
|------|-------------|
| Detección | Encuentra los encabezados reales aunque vengan en fila 5, 6 o 7 |
| Selección | De las 42 columnas del raw, extrae solo las 20 necesarias |
| Limpieza de texto | Mayúsculas, sin espacios dobles, sin caracteres extraños |
| Género | F / FEM → FEMENINO · M / MAS → MASCULINO |
| Documentos | Elimina decimales (39178633.0 → 39178633) |
| Fechas | Formato estándar YYYY-MM-DD |
| Consolidación | Apila todos los archivos del mes en uno solo |
| Power BI | Agrega columnas AÑO, MES, DÍA, MES NOMBRE, ENTREGADO |
| Validación | Alerta si faltan nombre, género o fecha de entrega |

---

## Dependencias

| Librería | Uso |
|----------|-----|
| Flask | Servidor web local |
| flask-cors | Permite llamadas desde el navegador |
| pandas | Procesamiento de datos |
| openpyxl | Lectura/escritura de Excel con formato |
| numpy | Manejo de valores nulos |
| PyInstaller | Empaquetado como .exe (solo para build) |
