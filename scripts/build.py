"""
build.py — Genera el .exe para Windows
Ejecutar desde la raíz del proyecto: python build.py
"""

import subprocess
import sys
import os
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # sube de scripts/ a raizal_v2/
BACKEND_DIR  = os.path.join(PROJECT_ROOT, 'backend')
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend', 'public')
DIST_DIR     = os.path.join(PROJECT_ROOT, 'dist')
BUILD_DIR    = os.path.join(PROJECT_ROOT, 'build')

APP_NAME = "PaquetesAlimentarios_Raizal"

def run(cmd, **kwargs):
    print(f"\n▶ {' '.join(cmd)}\n")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"\n❌ Error ejecutando: {' '.join(cmd)}")
        sys.exit(result.returncode)

def main():
    print("=" * 55)
    print("  Build — Procesador de Paquetes El Raizal")
    print("=" * 55)

    # 1. Instalar dependencias
    print("\n▶ Instalando dependencias...")
    run([sys.executable, '-m', 'pip', 'install', '-r',
         os.path.join(PROJECT_ROOT, 'requirements.txt'), '-q'])

    # 2. Construir con PyInstaller
    print("\n▶ Generando .exe con PyInstaller...")

    pyinstaller_args = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',                          # Un solo .exe
        '--noconsole',                        # Sin ventana de consola negra
        '--name', APP_NAME,
        '--distpath', DIST_DIR,
        '--workpath', BUILD_DIR,
        '--specpath', BUILD_DIR,
        # Incluir carpeta frontend completa dentro del .exe
        '--add-data', f'{FRONTEND_DIR}{os.pathsep}frontend',
        # Incluir pipeline.py como módulo
        '--add-data', f'{BACKEND_DIR}{os.pathsep}backend',
        # Imports ocultos que PyInstaller a veces no detecta
        '--hidden-import', 'flask',
        '--hidden-import', 'pandas',
        '--hidden-import', 'openpyxl',
        '--hidden-import', 'numpy',
        '--hidden-import', 'openpyxl.styles',
        '--hidden-import', 'openpyxl.utils',
        os.path.join(BACKEND_DIR, 'app.py'),
    ]

    run(pyinstaller_args)

    # 3. Resultado
    exe_path = os.path.join(DIST_DIR, f'{APP_NAME}.exe')
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n{'='*55}")
        print(f"  ✅ .exe generado exitosamente")
        print(f"  📁 Ubicación : {exe_path}")
        print(f"  📦 Tamaño    : {size_mb:.1f} MB")
        print(f"{'='*55}")
        print("\n  Entrega este archivo al coordinador.")
        print("  Solo necesita hacer doble clic para abrir la app.\n")
    else:
        print("\n❌ No se encontró el .exe generado. Revisa los errores arriba.")
        sys.exit(1)

if __name__ == '__main__':
    main()
