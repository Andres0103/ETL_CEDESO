# test_transform.py

from backend.etl.transform import process_file

with open("RUTA_DE_UN_EXCEL_REAL.xlsx", "rb") as f:
    df, report = process_file(f.read())

print("Filas:", len(df))
print(df.head())