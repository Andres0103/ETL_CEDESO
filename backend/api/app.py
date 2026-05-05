# coding: utf-8
"""
app.py
------
Responsabilidad única: servidor Flask.
Rutas HTTP, manejo de errores y CORS.
Sin lógica de negocio — todo se delega a pipeline.run_pipeline().
"""

import logging
import os
import sys
import threading
import traceback
import webbrowser

from flask import Flask, jsonify, request, send_file, send_from_directory

logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Directorios
# ---------------------------------------------------------------------------

if getattr(sys, "frozen", False):
    # Ejecutable empaquetado con PyInstaller
    BASE_DIR = sys._MEIPASS
    FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    FRONTEND_DIR = os.path.abspath(
        os.path.join(BASE_DIR, "..", "..", "frontend", "public")
    )

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

TMP_DIR = os.path.join(os.path.expanduser("~"), ".raizal_tmp")
os.makedirs(TMP_DIR, exist_ok=True)

log.info("BASE_DIR     : %s", BASE_DIR)
log.info("FRONTEND_DIR : %s", FRONTEND_DIR)
log.info("TMP_DIR      : %s", TMP_DIR)

# ---------------------------------------------------------------------------
# Importar pipeline (separado para capturar errores en arranque)
# ---------------------------------------------------------------------------

PIPELINE_ERROR = None
try:
    from backend.etl.pipeline import run_pipeline
    log.info("pipeline.py importado OK")
except Exception:
    PIPELINE_ERROR = traceback.format_exc()
    log.error("ERROR importando pipeline.py:\n%s", PIPELINE_ERROR)

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB


@app.errorhandler(Exception)
def handle_any(e):
    log.error("Error no capturado:\n%s", traceback.format_exc())
    return jsonify({"error": str(e), "detalle": traceback.format_exc()}), 500


@app.after_request
def add_cors(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    r.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return r


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/test")
def test():
    """Diagnóstico rápido: visita http://localhost:5050/test"""
    return jsonify({
        "servidor": "OK",
        "python": sys.version,
        "base_dir": BASE_DIR,
        "frontend_dir": FRONTEND_DIR,
        "frontend_existe": os.path.exists(FRONTEND_DIR),
        "tmp_dir": TMP_DIR,
        "pipeline_ok": PIPELINE_ERROR is None,
        "pipeline_error": PIPELINE_ERROR,
    })


@app.route("/procesar", methods=["POST", "OPTIONS"])
def procesar():
    if request.method == "OPTIONS":
        return "", 204

    if PIPELINE_ERROR:
        return jsonify({
            "error": "pipeline.py no pudo importarse",
            "detalle": PIPELINE_ERROR,
        }), 500

    log.info("=== /procesar ===")
    log.info("Archivos : %s", list(request.files.keys()))
    log.info("Form     : %s", dict(request.form))

    try:
        files = []
        for key in request.files:
            files.extend(request.files.getlist(key))

        if not files:
            return jsonify({"error": "No se recibieron archivos."}), 400

        mes = request.form.get("mes", "01")
        anio = request.form.get("anio", "2025")

        result = run_pipeline(files, mes, anio, TMP_DIR)
        return jsonify({"status": "ok", **result})

    except Exception as e:
        tb = traceback.format_exc()
        log.error("ERROR en pipeline:\n%s", tb)
        return jsonify({"error": str(e), "detalle": tb}), 500


@app.route("/descargar/<filename>")
def descargar(filename):
    safe = os.path.basename(filename)
    path = os.path.join(TMP_DIR, safe)
    if not os.path.exists(path):
        return jsonify({"error": "Archivo no encontrado"}), 404
    return send_file(
        path,
        as_attachment=True,
        download_name=safe,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ---------------------------------------------------------------------------
# Entrada principal
# ---------------------------------------------------------------------------

def _open_browser():
    import time
    time.sleep(1.5)
    webbrowser.open("http://localhost:5050")


if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  Procesador de Paquetes — El Raizal")
    print("=" * 55)
    print("  App  : http://localhost:5050")
    print("  Test : http://localhost:5050/test")
    print("  Temp : " + TMP_DIR)
    print("=" * 55 + "\n")
    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host="127.0.0.1", port=5050, debug=False, use_reloader=False)
