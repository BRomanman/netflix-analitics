# 🎬 Netflix Analytics Dashboard

## 📋 Descripción del Proyecto

Netflix Analytics Dashboard es una solución de Business Intelligence desarrollada en Python que integra múltiples fuentes de datos mediante un proceso ETL (Extract, Transform, Load) para generar métricas y visualizaciones sobre contenido de Netflix.

El proyecto consolida información proveniente de un archivo CSV, una base de datos SQLite y una API externa (TVMaze), permitiendo analizar películas y series mediante un dashboard interactivo desarrollado con Dash y Plotly.

---

# 🏗️ Arquitectura de Datos

El sistema integra tres fuentes de datos diferentes:

### 1. Catálogo Netflix (CSV)

Archivo:

```text
data/netflix_titles.csv
```

Contiene información histórica sobre:

* Título
* Tipo de contenido
* Director
* País
* Año de lanzamiento
* Géneros
* Clasificación

---

### 2. Historial de Visualizaciones (SQLite)

Base de datos:

```text
data/catalogo_netflix.db
```

Contiene información simulada de negocio:

* Título
* Tipo
* Visualizaciones

---

### 3. API Externa TVMaze

API utilizada:

```text
https://api.tvmaze.com
```

Se consulta durante el proceso ETL para enriquecer los datos con:

* Rating
* Idioma
* Estado de emisión

---

# 🔄 Flujo ETL

## Extract

Extracción de información desde:

* CSV Netflix
* SQLite
* API TVMaze

## Transform

Procesamiento y limpieza de datos:

* Unión de fuentes mediante el campo título
* Eliminación de duplicados
* Tratamiento de valores nulos
* Generación de métricas de negocio
* Integración de datos externos

## Load

Carga del resultado final en:

```text
data/dataset_final_dashboard.db
```

Tabla:

```text
vista_dashboard
```

---

# 📊 Dashboard

El dashboard presenta indicadores y visualizaciones tales como:

### KPI's

* Total de títulos
* Total de películas
* Total de series
* Total de visualizaciones

### Visualizaciones

* Distribución de contenido
* Top países
* Top géneros
* Top títulos más vistos
* Ratings obtenidos desde TVMaze
* Idiomas detectados desde TVMaze

---

# 🚀 Requisitos

* Python 3.10 o superior
* Git
* Docker (opcional)

---

# 🛠️ Ejecución Local

## 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## 2. Generar base SQLite

```bash
python crear_tienda.py
```

---

## 3. Ejecutar proceso ETL

```bash
python etl/peliculas_etl.py
```

---

## 4. Ejecutar Dashboard

```bash
python dashboards/app.py
```

Abrir en el navegador:

```text
http://localhost:8050
```

---

# 🐳 Docker

## Construir imagen

```bash
docker build -t netflix-analytics .
```

## Ejecutar contenedor

```bash
docker run -p 8050:8050 netflix-analytics
```

Acceder a:

```text
http://localhost:8050
```

---

# 🧰 Tecnologías Utilizadas

* Python
* Pandas
* SQLite
* Requests
* Dash
* Plotly
* Docker
* TVMaze API

---

# 👨‍💻 Autor

Proyecto desarrollado para fines académicos en el contexto de análisis de datos y Business Intelligence.
