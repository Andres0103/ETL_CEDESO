
# Procesador de Paquetes Alimentarios — El Raizal

Herramienta integral para limpiar, estandarizar y consolidar archivos Excel mensuales de entregas de paquetes alimentarios, lista para subir a Power BI. Desarrollada para el Centro de Desarrollo Social El Raizal (Comuna 3, Medellín).

ETL profesional con Spark, PostgreSQL y Docker, Power BI

- Reestructura arquitectura ETL: extract, transform, spark_ops, load, pipeline con responsabilidades únicas
- Integra PySpark para deduplicación distribuida con fallback automático a pandas
- Reemplaza carga a Excel por inserción en PostgreSQL (acumulación histórica mes a mes)
- Agrega ORM con SQLAlchemy: modelos PaqueteAlimentario y CargaETL para auditoría
- Configura Alembic para migraciones versionadas del esquema de BD
- Dockeriza PostgreSQL y pgAdmin con volúmenes persistentes
- Centraliza configuración en config.py con carga desde .env
- Corrige imports relativos en toda la cadena ETL
- Resuelve conflicto de versiones Python 3.11/3.12 para workers de Spark
- Elimina run_pipeline duplicado y lógica de Spark en transform.py
- Pipeline devuelve stats completas al frontend incluyendo registros insertados en BD
- Graficas realizada coon power BI que se obtiene de datos de la base de datos de postgres al ser procesado por la ETL

---

## Tabla de Contenidos

- [Descripción General](#descripción-general)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Instalación y Uso](#instalación-y-uso)
  - [A. Generar el .exe (para coordinador)](#a-generar-el-exe-para-coordinador)
  - [B. Modo desarrollo](#b-modo-desarrollo)
- [Flujo de Procesamiento](#flujo-de-procesamiento)
- [Tecnologías y Dependencias](#tecnologías-y-dependencias)
- [Notas y Soporte](#notas-y-soporte)

---

## Descripción General

Esta herramienta permite procesar los reportes mensuales de entregas de paquetes alimentarios, consolidando y limpiando los datos para su análisis en Power BI. Automatiza la detección de encabezados, limpieza de texto, normalización de columnas y validación de datos críticos.

---

## Estructura del Proyecto

```
raizal_v2/
├── backend/
│   ├── api/
│   │   └── app.py           # Servidor Flask (rutas y arranque)
│   ├── db/                  # Modelos y sesión SQLAlchemy
│   └── etl/                 # Lógica ETL: extracción, transformación, carga
├── frontend/
│   └── public/              # Interfaz web (HTML, CSS, JS)
├── scripts/
│   └── build.py             # Script para generar el .exe
├── requirements.txt         # Dependencias Python
├── docker-compose.yml       # Servicios PostgreSQL y PgAdmin
├── config.py                # Configuración centralizada
└── README.md
```

---

## Instalación y Uso



### B. Modo desarrollo

1. Instalar dependencias:
	```bash
	pip install -r requirements.txt
	```
2. Iniciar el servidor:
	```bash
	python backend/api/app.py
	```
3. Abrir en el navegador: [http://localhost:5050](http://localhost:5050)

---



---

## Flujo de Procesamiento

| Paso         | Descripción                                                                 |
|--------------|-----------------------------------------------------------------------------|
| Detección    | Encuentra los encabezados reales aunque estén en fila 5, 6 o 7              |
| Selección    | De las columnas originales, extrae solo las necesarias                      |
| Limpieza     | Mayúsculas, sin espacios dobles, sin caracteres extraños                    |
| Género       | F / FEM → FEMENINO · M / MAS → MASCULINO                                    |
| Documentos   | Elimina decimales (39178633.0 → 39178633)                                   |
| Fechas       | Formato estándar YYYY-MM-DD                                                 |
| Consolidación| Apila todos los archivos del mes en uno solo                                |
| Power BI     | Agrega columnas AÑO, MES, DÍA, MES NOMBRE, ENTREGADO                       |
| Validación   | Alerta si faltan nombre, género o fecha de entrega                          |

---

## Tecnologías y Dependencias

**Backend:**
- Python 3.10+
- Flask (servidor web)
- flask-cors (CORS para frontend)
- pandas, numpy (procesamiento de datos)
- openpyxl (Excel)
- SQLAlchemy, Alembic (ORM y migraciones)
- psycopg2-binary (PostgreSQL)
- PyInstaller (solo para build .exe)
- pyspark (opcional, deduplicación avanzada)

**Frontend:**
- HTML5, CSS3 (DM Sans, DM Serif Display)
- JavaScript (manejo de archivos, UI)

**Base de datos:**
- PostgreSQL (docker-compose incluido)
- PgAdmin (opcional, para administración visual)

---

## Notas y Soporte

- La configuración de base de datos y variables sensibles se gestiona vía `.env` y `config.py`.
- Para desarrollo, puedes levantar PostgreSQL y PgAdmin con:
  ```bash
  docker-compose up -d
  ```
- El pipeline ETL es modular y fácilmente extensible.
- Para soporte o mejoras, contactar al equipo de desarrollo del Centro El Raizal.
