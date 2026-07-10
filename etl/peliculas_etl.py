"""
peliculas_etl.py
====================================================
Pipeline ETL - Netflix Analytics Dashboard
Evaluación Final Transversal - SCY1101

Versión reforzada respecto a la entrega anterior. Se agregan:

    1. Validación de esquema de cada fuente ANTES de procesarla
       (columnas obligatorias, tipos de dato esperados).
    2. Manejo robusto de errores en las 3 fases (Extract, Transform,
       Load), no solo en las llamadas HTTP.
    3. Reintentos con backoff exponencial para la API TVMaze, en vez
       de fallar en el primer intento.
    4. Logging profesional (módulo `logging`) en lugar de `print`,
       con niveles INFO/WARNING/ERROR y salida a archivo + consola.
    5. Configuración por variables de entorno (rutas, timeouts,
       reintentos), con valores por defecto sensatos.
    6. Procesamiento en lotes (batches) de la consulta a la API,
       con reporte de progreso y de tasa de éxito/fallo.
    7. Reporte de calidad de datos (nulos antes/después, filas sin
       coincidencia en el merge, tasa de éxito de la API) guardado
       en docs/reporte_calidad_datos.json.

El esquema de salida (columnas de `vista_dashboard`) se mantiene
idéntico al de la versión anterior para no romper el dashboard
(`dashboards/app.py`) ni el modelo de ML, que dependen de él.
"""

import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime

import pandas as pd
import requests

# ==========================================================
# CONFIGURACIÓN POR VARIABLES DE ENTORNO
# ==========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, "..")

DATA_DIR = os.environ.get("NETFLIX_DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
DOCS_DIR = os.environ.get("NETFLIX_DOCS_DIR", os.path.join(PROJECT_ROOT, "docs"))

TVMAZE_BASE_URL = os.environ.get("TVMAZE_BASE_URL", "https://api.tvmaze.com")
REQUEST_TIMEOUT = float(os.environ.get("TVMAZE_TIMEOUT_SECONDS", "10"))
MAX_REINTENTOS = int(os.environ.get("TVMAZE_MAX_RETRIES", "3"))
BACKOFF_BASE_SECONDS = float(os.environ.get("TVMAZE_BACKOFF_BASE", "0.5"))
RATE_LIMIT_SECONDS = float(os.environ.get("TVMAZE_RATE_LIMIT_SECONDS", "0.2"))
BATCH_SIZE = int(os.environ.get("TVMAZE_BATCH_SIZE", "10"))

DB_VISUALIZACIONES = os.path.join(DATA_DIR, "catalogo_netflix.db")
CSV_CATALOGO = os.path.join(DATA_DIR, "netflix_titles.csv")
DB_FINAL = os.path.join(DATA_DIR, "dataset_final_dashboard.db")
LOG_PATH = os.path.join(PROJECT_ROOT, "etl", "etl.log")
REPORTE_CALIDAD = os.path.join(DOCS_DIR, "reporte_calidad_datos.json")


# ==========================================================
# LOGGING PROFESIONAL
# ==========================================================
def configurar_logger() -> logging.Logger:
    logger = logging.getLogger("netflix_etl")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formato = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler_consola = logging.StreamHandler(sys.stdout)
    handler_consola.setFormatter(formato)
    logger.addHandler(handler_consola)

    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        handler_archivo = logging.FileHandler(LOG_PATH, encoding="utf-8")
        handler_archivo.setFormatter(formato)
        logger.addHandler(handler_archivo)
    except OSError:
        logger.warning("No se pudo crear el archivo de log; se continúa solo con consola.")

    return logger


log = configurar_logger()


# ==========================================================
# VALIDACIÓN DE ESQUEMA
# ==========================================================
class ErrorValidacionEsquema(Exception):
    """Se lanza cuando una fuente de datos no cumple el esquema mínimo esperado."""


def validar_esquema(df: pd.DataFrame, nombre_fuente: str, columnas_obligatorias: list) -> None:
    """
    Verifica que el DataFrame tenga todas las columnas obligatorias.
    No se valida tipo de dato estrictamente (SQLite/CSV son laxos en
    tipado), pero sí presencia de columnas y que el DataFrame no
    esté vacío, que son las causas más comunes de que un pipeline
    reviente silenciosamente más adelante.
    """
    if df is None or df.empty:
        raise ErrorValidacionEsquema(
            f"La fuente '{nombre_fuente}' está vacía o no se pudo leer."
        )

    columnas_faltantes = set(columnas_obligatorias) - set(df.columns)
    if columnas_faltantes:
        raise ErrorValidacionEsquema(
            f"La fuente '{nombre_fuente}' no tiene las columnas obligatorias: "
            f"{sorted(columnas_faltantes)}. Columnas encontradas: {list(df.columns)}"
        )

    log.info(
        "Esquema validado OK para '%s' (%d filas, %d columnas).",
        nombre_fuente, df.shape[0], df.shape[1],
    )


ESQUEMA_VISUALIZACIONES = ["title", "type", "visualizaciones"]
ESQUEMA_CATALOGO = [
    "show_id", "type", "title", "director", "cast", "country",
    "date_added", "release_year", "rating", "duration", "listed_in", "description",
]


# ==========================================================
# 1. EXTRACT
# ==========================================================
def extraer_visualizaciones() -> pd.DataFrame:
    log.info("Extrayendo historial de visualizaciones desde SQLite...")
    try:
        with sqlite3.connect(DB_VISUALIZACIONES) as conn:
            df = pd.read_sql_query("SELECT * FROM historial_visualizaciones", conn)
    except sqlite3.Error as e:
        raise RuntimeError(
            f"No se pudo leer '{DB_VISUALIZACIONES}': {e}. "
            "¿Se ejecutó crear_tienda.py antes del ETL?"
        ) from e

    validar_esquema(df, "SQLite (historial_visualizaciones)", ESQUEMA_VISUALIZACIONES)
    return df


def extraer_catalogo() -> pd.DataFrame:
    log.info("Extrayendo catálogo Netflix desde CSV...")
    try:
        df = pd.read_csv(CSV_CATALOGO)
    except FileNotFoundError as e:
        raise RuntimeError(f"No se encontró el archivo CSV en '{CSV_CATALOGO}'.") from e
    except pd.errors.ParserError as e:
        raise RuntimeError(f"El CSV '{CSV_CATALOGO}' está mal formado: {e}") from e

    validar_esquema(df, "CSV (netflix_titles)", ESQUEMA_CATALOGO)
    return df


# ==========================================================
# 2. TRANSFORM
# ==========================================================
def unir_fuentes(df_visualizaciones: pd.DataFrame, df_catalogo: pd.DataFrame) -> pd.DataFrame:
    log.info("Uniendo visualizaciones con catálogo Netflix (join por 'title')...")

    filas_antes = len(df_visualizaciones)
    df_final = pd.merge(df_visualizaciones, df_catalogo, on="title", how="left")

    # Filas cuyo título no encontró coincidencia en el catálogo -> quedan con NaN.
    sin_coincidencia = df_final["show_id"].isna().sum()
    if sin_coincidencia > 0:
        log.warning(
            "%d de %d títulos no encontraron coincidencia en el catálogo Netflix "
            "(quedarán con datos incompletos).",
            sin_coincidencia, filas_antes,
        )

    df_final = df_final.drop(columns=["type_x"]).rename(columns={"type_y": "type"})
    return df_final, sin_coincidencia


def limpiar_datos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza vectorizada (sin loops fila a fila) usando operaciones
    nativas de Pandas sobre columnas completas.
    """
    log.info("Aplicando limpieza y normalización de datos (vectorizada)...")

    df = df.copy()
    columnas_texto_con_nulos = ["country", "director", "listed_in"]
    for col in columnas_texto_con_nulos:
        df[col] = df[col].fillna("Sin información")

    # Normalización de espacios en blanco sobrantes (vectorizado con .str)
    df["title"] = df["title"].str.strip()
    df["country"] = df["country"].str.strip()

    return df


def consultar_tvmaze_un_titulo(titulo: str) -> dict:
    """
    Consulta TVMaze para un único título, con reintentos y backoff
    exponencial ante errores transitorios de red.

    Devuelve un dict con tvmaze_rating / tvmaze_language / tvmaze_status,
    todos en None si no hubo coincidencia o si fallaron todos los reintentos.
    """
    resultado_vacio = {
        "title": titulo, "tvmaze_rating": None,
        "tvmaze_language": None, "tvmaze_status": None,
    }

    url = f"{TVMAZE_BASE_URL}/search/shows"

    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            response = requests.get(url, params={"q": titulo}, timeout=REQUEST_TIMEOUT)

            if response.status_code == 429:
                # Rate limit: esperar más y reintentar
                espera = BACKOFF_BASE_SECONDS * (2 ** intento)
                log.warning("Rate limit de TVMaze para '%s'. Reintentando en %.1fs...", titulo, espera)
                time.sleep(espera)
                continue

            response.raise_for_status()
            data = response.json()

            if not data:
                return resultado_vacio

            show = data[0].get("show", {})
            return {
                "title": titulo,
                "tvmaze_rating": show.get("rating", {}).get("average"),
                "tvmaze_language": show.get("language"),
                "tvmaze_status": show.get("status"),
            }

        except requests.exceptions.Timeout:
            log.warning("Timeout consultando TVMaze para '%s' (intento %d/%d).", titulo, intento, MAX_REINTENTOS)
        except requests.exceptions.ConnectionError:
            log.warning("Error de conexión con TVMaze para '%s' (intento %d/%d).", titulo, intento, MAX_REINTENTOS)
        except requests.exceptions.HTTPError as e:
            log.warning("Error HTTP de TVMaze para '%s': %s (intento %d/%d).", titulo, e, intento, MAX_REINTENTOS)
        except (ValueError, KeyError, IndexError) as e:
            # Respuesta 200 pero JSON inesperado / campos faltantes
            log.warning("Respuesta inesperada de TVMaze para '%s': %s", titulo, e)
            return resultado_vacio

        if intento < MAX_REINTENTOS:
            time.sleep(BACKOFF_BASE_SECONDS * (2 ** (intento - 1)))

    log.error("Se agotaron los reintentos con TVMaze para '%s'. Se registra como sin datos.", titulo)
    return resultado_vacio


def enriquecer_con_tvmaze(titulos: list) -> pd.DataFrame:
    """
    Consulta la API TVMaze en lotes (batches), reportando progreso y
    tasa de éxito. El procesamiento por lotes facilita medir avance
    en catálogos grandes y aislar fallas a un rango acotado de filas.
    """
    log.info("Consultando TVMaze API para %d títulos (lotes de %d)...", len(titulos), BATCH_SIZE)

    resultados = []
    exitosos = 0

    for inicio in range(0, len(titulos), BATCH_SIZE):
        lote = titulos[inicio: inicio + BATCH_SIZE]
        log.info("Procesando lote %d-%d de %d...", inicio + 1, min(inicio + BATCH_SIZE, len(titulos)), len(titulos))

        for titulo in lote:
            resultado = consultar_tvmaze_un_titulo(titulo)
            if resultado["tvmaze_rating"] is not None or resultado["tvmaze_status"] is not None:
                exitosos += 1
            resultados.append(resultado)
            time.sleep(RATE_LIMIT_SECONDS)

    tasa_exito = (exitosos / len(titulos) * 100) if titulos else 0
    log.info(
        "Consulta TVMaze finalizada: %d/%d títulos con datos (%.1f%% de éxito).",
        exitosos, len(titulos), tasa_exito,
    )

    return pd.DataFrame(resultados), tasa_exito


# ==========================================================
# 3. LOAD
# ==========================================================
def cargar_resultado(df_final: pd.DataFrame) -> None:
    log.info("Guardando dataset final para dashboard en '%s'...", DB_FINAL)
    try:
        with sqlite3.connect(DB_FINAL) as conn:
            df_final.to_sql("vista_dashboard", conn, if_exists="replace", index=False)
    except sqlite3.Error as e:
        raise RuntimeError(f"No se pudo guardar el resultado final en SQLite: {e}") from e


def guardar_reporte_calidad(metricas: dict) -> None:
    try:
        os.makedirs(DOCS_DIR, exist_ok=True)
        with open(REPORTE_CALIDAD, "w", encoding="utf-8") as f:
            json.dump(metricas, f, indent=2, ensure_ascii=False)
        log.info("Reporte de calidad de datos guardado en '%s'.", REPORTE_CALIDAD)
    except OSError as e:
        log.warning("No se pudo guardar el reporte de calidad de datos: %s", e)


# ==========================================================
# ORQUESTACIÓN DEL PIPELINE
# ==========================================================
def ejecutar_etl():
    inicio_ejecucion = datetime.now()
    log.info("=" * 60)
    log.info("Iniciando Pipeline ETL Netflix (versión reforzada)")
    log.info("=" * 60)

    try:
        # ---- EXTRACT ----
        df_visualizaciones = extraer_visualizaciones()
        df_catalogo = extraer_catalogo()

        nulos_antes = df_catalogo.isnull().sum().to_dict()

        # ---- TRANSFORM ----
        df_final, sin_coincidencia = unir_fuentes(df_visualizaciones, df_catalogo)
        df_final = limpiar_datos(df_final)

        titulos = df_final["title"].dropna().unique().tolist()
        df_api, tasa_exito_api = enriquecer_con_tvmaze(titulos)

        df_final = pd.merge(df_final, df_api, on="title", how="left")

        nulos_despues = df_final.isnull().sum().to_dict()

        # ---- LOAD ----
        cargar_resultado(df_final)

        # ---- REPORTE DE CALIDAD ----
        duracion = (datetime.now() - inicio_ejecucion).total_seconds()
        metricas = {
            "fecha_ejecucion": inicio_ejecucion.isoformat(),
            "duracion_segundos": round(duracion, 2),
            "filas_procesadas": int(len(df_final)),
            "titulos_sin_coincidencia_catalogo": int(sin_coincidencia),
            "tasa_exito_api_tvmaze_pct": round(tasa_exito_api, 1),
            "nulos_por_columna_catalogo_original": {k: int(v) for k, v in nulos_antes.items()},
            "nulos_por_columna_dataset_final": {k: int(v) for k, v in nulos_despues.items()},
        }
        guardar_reporte_calidad(metricas)

        log.info("ETL FINALIZADO CORRECTAMENTE en %.1f segundos.", duracion)
        log.info(
            "Resumen: %d filas | %.1f%% éxito API | %d sin coincidencia en catálogo",
            len(df_final), tasa_exito_api, sin_coincidencia,
        )

        columnas_resumen = ["title", "type", "visualizaciones", "tvmaze_rating", "tvmaze_language", "tvmaze_status"]
        print("\n" + df_final[columnas_resumen].head().to_string() + "\n")

        return df_final

    except ErrorValidacionEsquema as e:
        log.error("VALIDACIÓN DE ESQUEMA FALLIDA: %s", e)
        log.error("El pipeline se detiene: una fuente de datos no cumple el formato mínimo esperado.")
        raise
    except RuntimeError as e:
        log.error("ERROR EN EL PIPELINE: %s", e)
        raise
    except Exception as e:
        log.error("ERROR INESPERADO EN EL PIPELINE: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    ejecutar_etl()
