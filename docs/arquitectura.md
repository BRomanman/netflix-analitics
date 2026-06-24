# Arquitectura del Sistema

## Descripción General

Netflix Analytics Dashboard es una solución de análisis de datos que integra información desde múltiples fuentes para generar visualizaciones interactivas orientadas a la toma de decisiones.

## Fuentes de Datos

### Fuente 1: CSV

Archivo:

data/netflix_titles.csv


Contiene información histórica del catálogo Netflix:

* Título
* Tipo
* Director
* País
* Año
* Géneros
* Clasificación

### Fuente 2: SQLite

Base de datos:

data/catalogo_netflix.db


Tabla:

historial_visualizaciones


Contiene:

* Título
* Tipo
* Visualizaciones

### Fuente 3: API TVMaze

API REST:

https://api.tvmaze.com


Información obtenida:

* Rating
* Idioma
* Estado de emisión

## Flujo ETL

1. Extracción desde CSV.
2. Extracción desde SQLite.
3. Consulta a TVMaze.
4. Limpieza de datos.
5. Integración de fuentes.
6. Generación de métricas.
7. Carga a SQLite final.

## Base de Datos Final

Archivo:

data/dataset_final_dashboard.db


Tabla:

vista_dashboard


## Dashboard

La información procesada es consumida por un dashboard desarrollado en Dash y Plotly.
