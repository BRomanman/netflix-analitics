# API REST del Modelo de Machine Learning

## Descripción

API REST construida con Flask que expone el modelo de clasificación
(`models/modelo_final.pkl`) entrenado para predecir si un título de Netflix
corresponde a una `Movie` o a un `TV Show`.

Se ejecuta en un puerto separado (5001) del dashboard (8050), como un
servicio independiente dentro de la misma arquitectura Docker.

## Cómo levantarla

```bash
# Local
python api/api_ml.py

# Con Docker Compose (junto al resto del sistema)
docker compose up
```

La API queda disponible en `http://localhost:5001`.

## Endpoints

### `GET /health`

Verifica que el servicio esté activo y qué modelo tiene cargado.

```bash
curl http://localhost:5001/health
```

### `GET /model-info`

Devuelve los metadatos completos del modelo: features requeridas, clases,
métricas de evaluación en el conjunto de prueba y la tabla comparativa de
los 3 algoritmos entrenados.

```bash
curl http://localhost:5001/model-info
```

### `GET /predict/ejemplo`

Endpoint de conveniencia para la demo en vivo: ejecuta una predicción con un
ejemplo ya armado, sin necesidad de escribir un JSON a mano.

```bash
curl http://localhost:5001/predict/ejemplo
```

### `POST /predict`

Recibe los atributos de un título y devuelve la predicción del modelo junto
con las probabilidades de cada clase.

```bash
curl -X POST http://localhost:5001/predict \
  -H "Content-Type: application/json" \
  -d '{
        "release_year": 2020,
        "rating": "TV-MA",
        "pais_principal": "United States",
        "num_actores": 5,
        "tiene_director": 0,
        "largo_descripcion": 180,
        "mes_agregado": 9
      }'
```

Respuesta:

```json
{
  "prediccion": "TV Show",
  "probabilidades": {"Movie": 0.09, "TV Show": 0.91},
  "modelo_usado": "Gradient Boosting",
  "input_recibido": { "...": "..." }
}
```

Si falta algún campo obligatorio, la API responde con código `400` y el
detalle de los campos faltantes. El campo `decada_lanzamiento` es opcional:
si no se envía, se calcula automáticamente a partir de `release_year`.

## Campos requeridos

| Campo | Tipo | Ejemplo |
|---|---|---|
| release_year | int | 2020 |
| rating | string | "TV-MA" |
| pais_principal | string | "United States" |
| num_actores | int | 5 |
| tiene_director | 0 o 1 | 0 |
| largo_descripcion | int | 180 |
| mes_agregado | int (1-12) | 9 |
