"""
test_etl.py
====================================================
Testing automatizado - Netflix Analytics Dashboard
Evaluación Final Transversal - SCY1101

Pruebas unitarias sobre las funciones más críticas del pipeline ETL:
validación de esquema y limpieza de datos. Se usa `unittest` (librería
estándar de Python, sin dependencias externas) para que corra en
cualquier entorno sin instalar nada adicional.

Ejecutar con:
    python -m unittest tests/test_etl.py -v
"""

import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "etl"))

from peliculas_etl import (  # noqa: E402
    ErrorValidacionEsquema,
    limpiar_datos,
    validar_esquema,
)


class TestValidarEsquema(unittest.TestCase):

    def test_esquema_correcto_no_lanza_error(self):
        df = pd.DataFrame({"title": ["A"], "type": ["Movie"], "visualizaciones": [100]})
        try:
            validar_esquema(df, "test", ["title", "type", "visualizaciones"])
        except ErrorValidacionEsquema:
            self.fail("validar_esquema lanzó un error con un esquema correcto.")

    def test_columna_faltante_lanza_error(self):
        df = pd.DataFrame({"title": ["A"], "type": ["Movie"]})  # falta 'visualizaciones'
        with self.assertRaises(ErrorValidacionEsquema):
            validar_esquema(df, "test", ["title", "type", "visualizaciones"])

    def test_dataframe_vacio_lanza_error(self):
        df = pd.DataFrame(columns=["title", "type", "visualizaciones"])
        with self.assertRaises(ErrorValidacionEsquema):
            validar_esquema(df, "test", ["title", "type", "visualizaciones"])

    def test_dataframe_none_lanza_error(self):
        with self.assertRaises(ErrorValidacionEsquema):
            validar_esquema(None, "test", ["title"])

    def test_mensaje_de_error_incluye_columnas_faltantes(self):
        df = pd.DataFrame({"title": ["A"]})
        with self.assertRaises(ErrorValidacionEsquema) as contexto:
            validar_esquema(df, "mi_fuente", ["title", "director", "country"])
        mensaje = str(contexto.exception)
        self.assertIn("director", mensaje)
        self.assertIn("country", mensaje)
        self.assertIn("mi_fuente", mensaje)


class TestLimpiarDatos(unittest.TestCase):

    def test_nulos_se_reemplazan_por_texto_por_defecto(self):
        df = pd.DataFrame({
            "title": [" Inception "],
            "country": [None],
            "director": [None],
            "listed_in": [None],
        })
        resultado = limpiar_datos(df)
        self.assertEqual(resultado.loc[0, "country"], "Sin información")
        self.assertEqual(resultado.loc[0, "director"], "Sin información")
        self.assertEqual(resultado.loc[0, "listed_in"], "Sin información")

    def test_espacios_en_blanco_se_eliminan(self):
        df = pd.DataFrame({
            "title": ["  Inception  "],
            "country": ["  United States  "],
            "director": ["Chris Nolan"],
            "listed_in": ["Sci-Fi"],
        })
        resultado = limpiar_datos(df)
        self.assertEqual(resultado.loc[0, "title"], "Inception")
        self.assertEqual(resultado.loc[0, "country"], "United States")

    def test_no_modifica_el_dataframe_original(self):
        df_original = pd.DataFrame({
            "title": ["Inception"],
            "country": [None],
            "director": [None],
            "listed_in": [None],
        })
        limpiar_datos(df_original)
        # El DataFrame pasado como argumento no debe mutar (se usa .copy())
        self.assertTrue(pd.isna(df_original.loc[0, "country"]))


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "etl"))
from analisis_avanzado import calcular_score_popularidad, generar_pivot  # noqa: E402


class TestTransformacionesAvanzadas(unittest.TestCase):

    def test_pivot_incluye_totales_y_sin_nulos(self):
        df = pd.DataFrame({
            "show_id": ["s1", "s2", "s3"],
            "release_year": [2015, 2015, 2021],
            "rating": ["PG-13", "PG-13", "TV-MA"],
        })
        pivot = generar_pivot(df)
        self.assertIn("Total", pivot.index)
        self.assertIn("Total", pivot.columns)
        self.assertFalse(pivot.isnull().any().any())

    def test_pivot_cuenta_correctamente(self):
        df = pd.DataFrame({
            "show_id": ["s1", "s2", "s3"],
            "release_year": [2015, 2016, 2021],
            "rating": ["PG-13", "PG-13", "TV-MA"],
        })
        pivot = generar_pivot(df)
        # decada 2010 (2015 y 2016) deberia tener 2 en PG-13
        self.assertEqual(pivot.loc[2010, "PG-13"], 2)

    def test_score_popularidad_es_z_score_valido(self):
        df = pd.DataFrame({
            "title": ["A", "B", "C"],
            "visualizaciones": [1000, 5000, 9000],
        })
        resultado = calcular_score_popularidad(df)
        # El titulo con mas visualizaciones debe tener el score mas alto
        self.assertEqual(resultado.iloc[0]["title"], "C")
        # El score 0-100 debe estar siempre en ese rango
        self.assertTrue((resultado["popularidad_score_0_100"] >= 0).all())
        self.assertTrue((resultado["popularidad_score_0_100"] <= 100).all())


if __name__ == "__main__":
    unittest.main(verbosity=2)
