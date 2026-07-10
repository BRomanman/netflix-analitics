# Modelo de Machine Learning

## Descripción

Se incorporó un componente de Machine Learning al proyecto para predecir el
**tipo de contenido** (`Movie` o `TV Show`) a partir de los metadatos
disponibles en el catálogo de Netflix, sin utilizar el campo `listed_in`
(género) ni el campo `duration` en su forma cruda, ya que ambos delatan el
tipo de forma casi directa (fuga de información).

## Objetivo de negocio

Permitir clasificar automáticamente contenido nuevo cuyo tipo aún no ha sido
etiquetado manualmente en el catálogo, o validar de forma automatizada la
consistencia de los datos existentes.

## Dataset utilizado

Se entrenó sobre el catálogo completo (`data/netflix_titles.csv`, 8.807
registros), en lugar de la tabla simulada de 30 filas del dashboard, para
contar con un volumen de datos suficiente para un entrenamiento y una
validación estadísticamente robustos.

## Variables predictoras (features)

| Variable | Tipo | Descripción |
|---|---|---|
| release_year | numérica | Año de lanzamiento |
| decada_lanzamiento | numérica | Década de lanzamiento (derivada) |
| rating | categórica | Clasificación de audiencia |
| pais_principal | categórica | Primer país listado (top 10 + "Otro") |
| num_actores | numérica | Cantidad de actores en el elenco |
| tiene_director | numérica (0/1) | Si el título tiene director registrado |
| largo_descripcion | numérica | Largo en caracteres de la sinopsis |
| mes_agregado | numérica | Mes en que se incorporó al catálogo |

## Preprocesamiento

Pipeline de `scikit-learn` (`ColumnTransformer`) que aplica:

* `StandardScaler` a las variables numéricas.
* `OneHotEncoder` a las variables categóricas.

El preprocesamiento queda encapsulado dentro del mismo objeto `Pipeline` que
el modelo, por lo que el archivo `.pkl` guardado contiene el flujo completo
(no requiere transformar los datos manualmente antes de predecir).

## Modelos entrenados y comparados

1. **Regresión Logística** — modelo lineal, usado como baseline interpretable.
2. **Random Forest** — con búsqueda de hiperparámetros vía `GridSearchCV`
   (`n_estimators`, `max_depth`, `min_samples_leaf`).
3. **Gradient Boosting** — modelo de boosting secuencial.

El modelo con mejor **F1-score** en el conjunto de prueba (20% de los datos,
split estratificado) se selecciona automáticamente y se guarda en
`models/modelo_final.pkl`.

## Métricas de evaluación

Se calculan sobre el conjunto de prueba: `accuracy`, `precision`, `recall`,
`f1-score` y `roc_auc`, además de la matriz de confusión y el reporte de
clasificación completo (`classification_report`).

## Interpretabilidad / hallazgo relevante

La variable más predictiva resultó ser `tiene_director`: en el catálogo,
**97% de las películas** tienen un director registrado, mientras que **91%
de las series de TV no lo tienen**. Este es un patrón real de cómo Netflix
cataloga sus contenidos (las series rara vez se atribuyen a un único
director) y no una fuga de datos, pero domina fuertemente la predicción.
Como mejora futura, se recomienda evaluar el modelo excluyendo esta variable
para forzar el aprendizaje de patrones más sutiles a partir del resto de los
atributos.

## Archivos generados

| Archivo | Contenido |
|---|---|
| `models/modelo_final.pkl` | Pipeline entrenado (preprocesamiento + modelo) |
| `models/metadatos_modelo.json` | Features requeridas, clases, métricas |
| `models/tabla_resumen_modelos.csv` | Comparación de los 3 modelos |
| `models/fig_comparacion_modelos.png` | Accuracy y F1 por modelo |
| `models/fig_matriz_confusion.png` | Matriz de confusión del mejor modelo |
| `models/fig_importancia_features.png` | Importancia de variables |
| `models/fig_roc_curve.png` | Curva ROC |

## Uso a través de la API

Ver `docs/api_ml.md` para el detalle de los endpoints. En resumen:

```bash
python api/api_ml.py
# Servidor disponible en http://localhost:5001

curl http://localhost:5001/predict/ejemplo
```
