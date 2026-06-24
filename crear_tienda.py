import pandas as pd
import sqlite3
import numpy as np
import os

print("1. Leyendo catálogo de Netflix...")

ruta_csv = "data/netflix_titles.csv"
df_catalogo = pd.read_csv(ruta_csv)

# Seleccionamos títulos aleatorios del catálogo
print("2. Generando historial de visualizaciones...")

df_netflix = (
    df_catalogo[['title', 'type']]
    .drop_duplicates()
    .sample(n=30, random_state=42)
)

# Simulamos cantidad de visualizaciones
df_netflix['visualizaciones'] = np.random.randint(
    1000,
    100000,
    size=len(df_netflix)
)

# Guardamos en SQLite
print("3. Guardando base de datos Netflix...")

db_path = os.path.join("data", "catalogo_netflix.db")

conn = sqlite3.connect(db_path)

df_netflix.to_sql(
    "historial_visualizaciones",
    conn,
    if_exists="replace",
    index=False
)

conn.close()

print("¡Listo! La base de datos 'catalogo_netflix.db' fue creada correctamente.")