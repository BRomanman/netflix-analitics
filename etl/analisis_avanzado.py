"""
analisis_avanzado.py
====================================================
Transformaciones Avanzadas de Datos - Netflix Analytics Dashboard
Evaluación Final Transversal - SCY1101

Este módulo demuestra explícitamente las técnicas de transformación
avanzada de Pandas/NumPy requeridas por la pauta de evaluación
(indicador IEE 1.2.1): pivot, reshape (melt), procesamiento por
chunks (para volúmenes grandes) y vectorización/broadcasting con NumPy.

No reemplaza al pipeline ETL principal (etl/peliculas_etl.py); es un
análisis complementario que se ejecuta sobre el catálogo completo de
Netflix para generar tablas y métricas adicionales de negocio.

Salidas (en docs/):
    - tabla_pivot_decada_rating.csv   -> tabla pivote (decada x rating)
    - tabla_reshape_larga.csv         -> la misma tabla en formato largo (melt)
    - resumen_chunking.json           -> resultado de procesar el CSV por lotes
    - resumen_popularidad.csv         -> score de popularidad normalizado (broadcasting)
"""

import json
import logging
import os
import time

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, "..")

CSV_PATH = os.path.join(PROJECT_ROOT, "data", "netflix_titles.csv")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")

OUT_PIVOT = os.path.join(DOCS_DIR, "tabla_pivot_decada_rating.csv")
OUT_MELT = os.path.join(DOCS_DIR, "tabla_reshape_larga.csv")
OUT_CHUNKING = os.path.join(DOCS_DIR, "resumen_chunking.json")
OUT_POPULARIDAD = os.path.join(DOCS_DIR, "resumen_popularidad.csv")

RATINGS_VALIDOS = {
    "TV-MA", "TV-14", "TV-PG", "R", "PG-13", "TV-Y7", "TV-Y",
    "PG", "TV-G", "NR", "G", "TV-Y7-FV", "NC-17", "UR",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("analisis_avanzado")


# ==========================================================
# 1. PIVOT — tabla pivote década de lanzamiento x rating
# ==========================================================
def generar_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construye una tabla pivote que cruza década de lanzamiento (filas)
    con clasificación de audiencia (columnas), contando títulos.

    Demuestra pd.pivot_table con agregación (count) y relleno de
    combinaciones vacías con 0, en lugar de NaN.
    """
    log.info("Generando tabla pivote (década x rating)...")

    data = df.copy()
    data["rating"] = data["rating"].where(data["rating"].isin(RATINGS_VALIDOS), "Unknown")
    data["rating"] = data["rating"].fillna("Unknown")
    data["decada"] = (data["release_year"] // 10) * 10

    pivot = pd.pivot_table(
        data,
        index="decada",
        columns="rating",
        values="show_id",
        aggfunc="count",
        fill_value=0,
        margins=True,
        margins_name="Total",
    )

    pivot.to_csv(OUT_PIVOT)
    log.info("Tabla pivote guardada en '%s' (shape=%s).", OUT_PIVOT, pivot.shape)
    return pivot


# ==========================================================
# 2. RESHAPE — de formato ancho (pivot) a formato largo (melt)
# ==========================================================
def generar_reshape(pivot: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte la tabla pivote (formato ancho) de vuelta a formato largo
    con pd.melt, útil para alimentar gráficos que requieren una fila
    por combinación década-rating (p. ej. Plotly Express).
    """
    log.info("Aplicando reshape (melt) de formato ancho a largo...")

    data = pivot.drop(index="Total", errors="ignore").drop(columns="Total", errors="ignore")
    data = data.reset_index()

    largo = pd.melt(
        data,
        id_vars="decada",
        var_name="rating",
        value_name="cantidad_titulos",
    )
    largo = largo[largo["cantidad_titulos"] > 0].sort_values(
        ["decada", "cantidad_titulos"], ascending=[True, False]
    )

    largo.to_csv(OUT_MELT, index=False)
    log.info("Tabla en formato largo guardada en '%s' (%d filas).", OUT_MELT, len(largo))
    return largo


# ==========================================================
# 3. CHUNKING — procesamiento por lotes para volúmenes grandes
# ==========================================================
def procesar_por_chunks(chunk_size: int = 1000) -> dict:
    """
    Procesa el CSV en lotes (chunks) en lugar de cargarlo completo en
    memoria de una sola vez. Aunque el dataset actual (8.807 filas)
    cabe cómodamente en memoria, esta técnica es la que se usaría en
    un escenario de producción con archivos de millones de filas, y
    se incluye aquí para demostrar el patrón correcto.

    Acumula conteos por país sin nunca mantener el DataFrame completo
    en memoria simultáneamente.
    """
    log.info("Procesando CSV por chunks de %d filas...", chunk_size)

    inicio = time.time()
    conteo_paises = pd.Series(dtype="int64")
    filas_procesadas = 0
    n_chunks = 0

    for chunk in pd.read_csv(CSV_PATH, chunksize=chunk_size):
        n_chunks += 1
        filas_procesadas += len(chunk)

        paises_chunk = (
            chunk["country"]
            .fillna("Sin información")
            .str.split(",")
            .str[0]
            .str.strip()
        )
        conteo_chunk = paises_chunk.value_counts()

        # Acumulación incremental (patrón típico de procesamiento por lotes)
        conteo_paises = conteo_paises.add(conteo_chunk, fill_value=0)

        log.info("  Chunk %d: %d filas acumuladas (%d hasta ahora).", n_chunks, len(chunk), filas_procesadas)

    duracion = time.time() - inicio
    top_paises = conteo_paises.sort_values(ascending=False).head(10).astype(int)

    resumen = {
        "chunk_size": chunk_size,
        "n_chunks_procesados": n_chunks,
        "filas_totales_procesadas": int(filas_procesadas),
        "duracion_segundos": round(duracion, 3),
        "top_10_paises": top_paises.to_dict(),
    }

    with open(OUT_CHUNKING, "w", encoding="utf-8") as f:
        json.dump(resumen, f, indent=2, ensure_ascii=False)

    log.info("Procesamiento por chunks finalizado: %d chunks, %d filas, %.3fs.", n_chunks, filas_procesadas, duracion)
    return resumen


# ==========================================================
# 4. VECTORIZACIÓN / BROADCASTING — score de popularidad
# ==========================================================
def calcular_score_popularidad(df_visualizaciones: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula un score de popularidad normalizado (z-score) usando
    operaciones vectorizadas de NumPy con broadcasting: la media y la
    desviación estándar (escalares) se restan/dividen directamente
    sobre el array completo de visualizaciones, sin ningún loop
    explícito en Python.
    """
    log.info("Calculando score de popularidad con broadcasting (NumPy)...")

    data = df_visualizaciones.copy()
    visualizaciones = data["visualizaciones"].to_numpy(dtype="float64")

    media = visualizaciones.mean()
    desviacion = visualizaciones.std()

    # Broadcasting: el escalar (media) y (desviacion) se aplican a
    # cada elemento del array sin iterar manualmente.
    z_scores = (visualizaciones - media) / desviacion

    # Reescalado adicional a un rango 0-100 (también vectorizado)
    minimo, maximo = z_scores.min(), z_scores.max()
    score_0_100 = (z_scores - minimo) / (maximo - minimo) * 100

    data["popularidad_zscore"] = np.round(z_scores, 3)
    data["popularidad_score_0_100"] = np.round(score_0_100, 1)

    resultado = data[["title", "visualizaciones", "popularidad_zscore", "popularidad_score_0_100"]]
    resultado = resultado.sort_values("popularidad_score_0_100", ascending=False)

    resultado.to_csv(OUT_POPULARIDAD, index=False)
    log.info("Score de popularidad guardado en '%s' (%d filas).", OUT_POPULARIDAD, len(resultado))
    return resultado


# ==========================================================
# ORQUESTACIÓN
# ==========================================================
def ejecutar_analisis_avanzado():
    log.info("=" * 60)
    log.info("Iniciando análisis avanzado de datos")
    log.info("=" * 60)

    df = pd.read_csv(CSV_PATH)
    log.info("Catálogo cargado: %d filas.", len(df))

    pivot = generar_pivot(df)
    generar_reshape(pivot)
    procesar_por_chunks(chunk_size=1000)

    # Para el score de popularidad usamos la tabla simulada de
    # visualizaciones (30 filas), ya que es la que tiene esa métrica.
    import sqlite3
    db_path = os.path.join(PROJECT_ROOT, "data", "catalogo_netflix.db")
    with sqlite3.connect(db_path) as conn:
        df_vis = pd.read_sql_query("SELECT * FROM historial_visualizaciones", conn)
    calcular_score_popularidad(df_vis)

    log.info("Análisis avanzado finalizado correctamente.")
    print("\nTop 5 títulos por score de popularidad (0-100):")
    top5 = pd.read_csv(OUT_POPULARIDAD).head()
    print(top5.to_string(index=False))


if __name__ == "__main__":
    ejecutar_analisis_avanzado()
