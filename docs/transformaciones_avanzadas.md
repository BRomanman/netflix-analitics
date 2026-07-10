# Transformaciones Avanzadas de Datos

## Descripción

Se incorporó el módulo `etl/analisis_avanzado.py`, complementario al
pipeline ETL principal, que demuestra explícitamente cuatro técnicas
de transformación avanzada sobre el catálogo completo de Netflix
(8.807 registros).

## Técnicas implementadas

### 1. Pivot (`pd.pivot_table`)

Se construye una tabla pivote que cruza **década de lanzamiento**
(filas) con **clasificación de audiencia** (columnas), contando
títulos en cada combinación, con totales de fila/columna (`margins`)
y relleno de combinaciones vacías con 0 en lugar de `NaN`.

Salida: `docs/tabla_pivot_decada_rating.csv`

### 2. Reshape (`pd.melt`)

La misma tabla pivote se convierte de formato ancho a formato largo
(una fila por combinación década-rating), el formato que normalmente
requieren las librerías de visualización como Plotly Express.

Salida: `docs/tabla_reshape_larga.csv`

### 3. Chunking (`pd.read_csv(chunksize=...)`)

El CSV se procesa en lotes de 1.000 filas en lugar de cargarlo
completo en memoria de una sola vez. Se acumulan conteos por país de
forma incremental entre lotes. Aunque el dataset actual cabe
cómodamente en memoria, esta es la técnica correcta para escalar a
archivos de millones de filas sin agotar la RAM disponible.

Salida: `docs/resumen_chunking.json` (incluye tiempo de procesamiento,
cantidad de chunks y el top 10 de países acumulado)

### 4. Vectorización y Broadcasting (NumPy)

Se calcula un score de popularidad normalizado (z-score, reescalado a
0-100) sobre las visualizaciones simuladas. La media y la desviación
estándar (escalares) se restan/dividen directamente sobre el array
completo mediante broadcasting de NumPy — sin ningún loop explícito
en Python:

```python
z_scores = (visualizaciones - media) / desviacion
```

Salida: `docs/resumen_popularidad.csv`

## Cómo ejecutarlo

```bash
python etl/analisis_avanzado.py
```

## Pruebas automatizadas

Las funciones de pivot y de score de popularidad tienen pruebas
unitarias en `tests/test_etl.py` (clase `TestTransformacionesAvanzadas`).
