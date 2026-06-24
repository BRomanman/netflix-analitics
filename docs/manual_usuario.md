# Manual de Usuario

## Objetivo

Visualizar información relevante del catálogo Netflix mediante dashboards interactivos.

## Requisitos

* Python 3.10 o superior
* Dependencias instaladas
* Dataset disponible

## Ejecución ETL

Desde la raíz del proyecto ejecutar:

```bash
python etl/peliculas_etl.py
```

Este proceso:

1. Lee el catálogo Netflix.
2. Lee las visualizaciones desde SQLite.
3. Consulta TVMaze.
4. Genera la base final para análisis.

## Ejecución Dashboard

Ejecutar:

```bash
python dashboards/app.py
```

Abrir navegador:

http://localhost:8050


## Indicadores disponibles

### KPI

* Total títulos
* Total películas
* Total series
* Total visualizaciones

### Gráficos

* Distribución de contenido
* Top países
* Top géneros
* Top títulos más vistos
* Ratings TVMaze
* Idiomas TVMaze

## Cierre

El dashboard permite explorar el catálogo y visualizar tendencias relevantes de forma interactiva.
