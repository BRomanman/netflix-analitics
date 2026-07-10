"""
entrenar_modelo.py
====================================================
Modelo de Machine Learning - Netflix Analytics Dashboard
Evaluación Final Transversal - SCY1101

OBJETIVO DE NEGOCIO
--------------------
Predecir el TIPO de contenido (Movie / TV Show) a partir de sus
metadatos (año, clasificación de audiencia, país, elenco, etc.),
sin usar el campo `listed_in` (género), ya que ese campo contiene
literalmente las palabras "TV Shows" / "Movies" y volvería el
problema trivial (fuga de información / data leakage).

Este es un caso de uso real: permite, por ejemplo, autocompletar o
validar la clasificación de contenido nuevo cuyo tipo aún no fue
etiquetado manualmente en el catálogo.

Se entrenan y comparan 3 algoritmos de clasificación supervisada:
    1. Regresión Logística   (modelo lineal, muy interpretable)
    2. Random Forest         (ensamble de árboles, no lineal)
    3. Gradient Boosting     (boosting secuencial)

Al Random Forest se le aplica además una búsqueda de hiperparámetros
(GridSearchCV) para optimizar su desempeño (tuning).

Salidas generadas (todas en /models):
    - modelo_final.pkl              -> pipeline completo (preprocesamiento + modelo)
    - metadatos_modelo.json         -> features esperadas, clases, métricas
    - tabla_resumen_modelos.csv     -> comparación de los 3 modelos
    - fig_comparacion_modelos.png   -> barras comparando accuracy/F1
    - fig_matriz_confusion.png      -> matriz de confusión del mejor modelo
    - fig_importancia_features.png  -> importancia de variables
    - fig_roc_curve.png             -> curva ROC del mejor modelo
"""

import json
import os

import joblib
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

matplotlib.use("Agg")

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# ==========================================================
# RUTAS
# ==========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "netflix_titles.csv")

OUT_MODEL = os.path.join(BASE_DIR, "modelo_final.pkl")
OUT_META = os.path.join(BASE_DIR, "metadatos_modelo.json")
OUT_TABLA = os.path.join(BASE_DIR, "tabla_resumen_modelos.csv")
OUT_FIG_COMP = os.path.join(BASE_DIR, "fig_comparacion_modelos.png")
OUT_FIG_CM = os.path.join(BASE_DIR, "fig_matriz_confusion.png")
OUT_FIG_IMP = os.path.join(BASE_DIR, "fig_importancia_features.png")
OUT_FIG_ROC = os.path.join(BASE_DIR, "fig_roc_curve.png")

RANDOM_STATE = 42


def cargar_datos():
    print("1. Cargando catálogo Netflix...")
    df = pd.read_csv(DATA_PATH)
    print(f"   {df.shape[0]} filas, {df.shape[1]} columnas.")
    return df


def construir_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ingeniería de atributos. Se excluye deliberadamente `listed_in`
    y `duration` (en su forma cruda) porque delatan el target de
    forma trivial. Se generan variables derivadas que sí requieren
    que el modelo aprenda un patrón real.
    """
    print("2. Construyendo variables predictoras (feature engineering)...")
    data = df.copy()

    # `rating` viene con algunos valores corruptos tipo "74 min"
    # (error conocido del dataset original de Kaggle, columnas desalineadas).
    ratings_validos = {
        "TV-MA", "TV-14", "TV-PG", "R", "PG-13", "TV-Y7", "TV-Y",
        "PG", "TV-G", "NR", "G", "TV-Y7-FV", "NC-17", "UR",
    }
    data["rating"] = data["rating"].where(data["rating"].isin(ratings_validos), "Unknown")
    data["rating"] = data["rating"].fillna("Unknown")

    # País principal (primero de la lista) agrupando categorías poco frecuentes
    data["country"] = data["country"].fillna("Sin informacion")
    data["pais_principal"] = data["country"].str.split(",").str[0].str.strip()
    top_paises = data["pais_principal"].value_counts().head(10).index
    data["pais_principal"] = data["pais_principal"].where(
        data["pais_principal"].isin(top_paises), "Otro"
    )

    # Cantidad de actores listados en el elenco
    data["cast"] = data["cast"].fillna("")
    data["num_actores"] = data["cast"].apply(
        lambda x: len([a for a in x.split(",") if a.strip()]) if x else 0
    )

    # ¿Tiene director registrado?
    data["tiene_director"] = data["director"].notna().astype(int)

    # Longitud de la descripción (proxy de qué tan detallada es la sinopsis)
    data["largo_descripcion"] = data["description"].fillna("").str.len()

    # Mes de incorporación al catálogo
    data["date_added"] = pd.to_datetime(data["date_added"], errors="coerce")
    data["mes_agregado"] = data["date_added"].dt.month.fillna(0).astype(int)

    # Década de lanzamiento (variable numérica más estable que el año exacto)
    data["decada_lanzamiento"] = (data["release_year"] // 10) * 10

    columnas_features = [
        "release_year",
        "decada_lanzamiento",
        "rating",
        "pais_principal",
        "num_actores",
        "tiene_director",
        "largo_descripcion",
        "mes_agregado",
    ]

    X = data[columnas_features]
    y = data["type"]

    return X, y, columnas_features


def construir_preprocesador(columnas_numericas, columnas_categoricas):
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), columnas_numericas),
            ("cat", OneHotEncoder(handle_unknown="ignore"), columnas_categoricas),
        ]
    )


def evaluar_modelo(nombre, pipeline, X_test, y_test, pos_label):
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, list(pipeline.classes_).index(pos_label)]

    metricas = {
        "modelo": nombre,
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, pos_label=pos_label),
        "recall": recall_score(y_test, y_pred, pos_label=pos_label),
        "f1": f1_score(y_test, y_pred, pos_label=pos_label),
        "roc_auc": roc_auc_score((y_test == pos_label).astype(int), y_proba),
    }
    return metricas, y_pred, y_proba


def main():
    df = cargar_datos()
    X, y, columnas_features = construir_features(df)

    columnas_numericas = [
        "release_year", "decada_lanzamiento", "num_actores",
        "tiene_director", "largo_descripcion", "mes_agregado",
    ]
    columnas_categoricas = ["rating", "pais_principal"]

    # ==========================================================
    # 3. SPLIT TRAIN / TEST (estratificado por la clase objetivo)
    # ==========================================================
    print("3. Dividiendo en train/test (80/20, estratificado)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    print(f"   Train: {X_train.shape[0]} filas | Test: {X_test.shape[0]} filas")

    preprocesador = construir_preprocesador(columnas_numericas, columnas_categoricas)
    pos_label = "TV Show"  # clase minoritaria -> métricas más informativas

    resultados = []
    pipelines_entrenados = {}

    # ==========================================================
    # 4. MODELO 1: REGRESIÓN LOGÍSTICA (baseline interpretable)
    # ==========================================================
    print("4. Entrenando Regresión Logística...")
    pipe_lr = Pipeline([
        ("prep", preprocesador),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE)),
    ])
    pipe_lr.fit(X_train, y_train)
    m_lr, _, _ = evaluar_modelo("Regresión Logística", pipe_lr, X_test, y_test, pos_label)
    resultados.append(m_lr)
    pipelines_entrenados["Regresión Logística"] = pipe_lr

    # ==========================================================
    # 5. MODELO 2: RANDOM FOREST + TUNING (GridSearchCV)
    # ==========================================================
    print("5. Entrenando Random Forest con búsqueda de hiperparámetros (GridSearchCV)...")
    pipe_rf = Pipeline([
        ("prep", preprocesador),
        ("clf", RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE)),
    ])
    grid_params = {
        "clf__n_estimators": [100, 200],
        "clf__max_depth": [None, 8, 12],
        "clf__min_samples_leaf": [1, 3],
    }
    grid_rf = GridSearchCV(pipe_rf, grid_params, cv=3, scoring="f1_macro", n_jobs=-1)
    grid_rf.fit(X_train, y_train)
    pipe_rf_best = grid_rf.best_estimator_
    print(f"   Mejores hiperparámetros: {grid_rf.best_params_}")
    m_rf, _, _ = evaluar_modelo("Random Forest (tuned)", pipe_rf_best, X_test, y_test, pos_label)
    resultados.append(m_rf)
    pipelines_entrenados["Random Forest (tuned)"] = pipe_rf_best

    # ==========================================================
    # 6. MODELO 3: GRADIENT BOOSTING
    # ==========================================================
    print("6. Entrenando Gradient Boosting...")
    pipe_gb = Pipeline([
        ("prep", preprocesador),
        ("clf", GradientBoostingClassifier(random_state=RANDOM_STATE)),
    ])
    pipe_gb.fit(X_train, y_train)
    m_gb, _, _ = evaluar_modelo("Gradient Boosting", pipe_gb, X_test, y_test, pos_label)
    resultados.append(m_gb)
    pipelines_entrenados["Gradient Boosting"] = pipe_gb

    # ==========================================================
    # 7. TABLA RESUMEN Y SELECCIÓN DEL MEJOR MODELO
    # ==========================================================
    print("7. Generando tabla resumen de métricas...")
    tabla = pd.DataFrame(resultados).sort_values("f1", ascending=False).reset_index(drop=True)
    tabla.to_csv(OUT_TABLA, index=False)
    print(tabla.to_string(index=False))

    mejor_nombre = tabla.iloc[0]["modelo"]
    mejor_pipeline = pipelines_entrenados[mejor_nombre]
    print(f"\n   >>> Mejor modelo según F1-score: {mejor_nombre}")

    y_pred_mejor = mejor_pipeline.predict(X_test)
    y_proba_mejor = mejor_pipeline.predict_proba(X_test)[:, list(mejor_pipeline.classes_).index(pos_label)]

    print("\n   Reporte de clasificación (mejor modelo):")
    print(classification_report(y_test, y_pred_mejor))

    # ==========================================================
    # 8. VISUALIZACIONES
    # ==========================================================
    print("8. Generando visualizaciones...")

    # 8.1 Comparación de modelos (accuracy y F1)
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(tabla))
    ancho = 0.35
    ax.bar(x - ancho / 2, tabla["accuracy"], ancho, label="Accuracy", color="#4C72B0")
    ax.bar(x + ancho / 2, tabla["f1"], ancho, label="F1-score", color="#DD8452")
    ax.set_xticks(x)
    ax.set_xticklabels(tabla["modelo"], rotation=15, ha="right")
    ax.set_ylim(0, 1)
    ax.set_title("Comparación de modelos de clasificación")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT_FIG_COMP, dpi=120)
    plt.close()

    # 8.2 Matriz de confusión del mejor modelo
    fig, ax = plt.subplots(figsize=(5, 5))
    cm = confusion_matrix(y_test, y_pred_mejor, labels=mejor_pipeline.classes_)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=mejor_pipeline.classes_)
    disp.plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title(f"Matriz de Confusión - {mejor_nombre}")
    plt.tight_layout()
    plt.savefig(OUT_FIG_CM, dpi=120)
    plt.close()

    # 8.3 Curva ROC del mejor modelo
    fig, ax = plt.subplots(figsize=(5, 5))
    RocCurveDisplay.from_predictions(
        (y_test == pos_label).astype(int), y_proba_mejor, ax=ax, name=mejor_nombre
    )
    ax.set_title(f"Curva ROC - {mejor_nombre} (clase positiva: {pos_label})")
    plt.tight_layout()
    plt.savefig(OUT_FIG_ROC, dpi=120)
    plt.close()

    # 8.4 Importancia de variables (si el modelo la soporta)
    clf_final = mejor_pipeline.named_steps["clf"]
    prep_final = mejor_pipeline.named_steps["prep"]
    nombres_ohe = prep_final.named_transformers_["cat"].get_feature_names_out(columnas_categoricas)
    nombres_features = columnas_numericas + list(nombres_ohe)

    if hasattr(clf_final, "feature_importances_"):
        importancias = clf_final.feature_importances_
        serie_imp = pd.Series(importancias, index=nombres_features).sort_values(ascending=False).head(12)
        fig, ax = plt.subplots(figsize=(8, 6))
        serie_imp.sort_values().plot(kind="barh", ax=ax, color="#55A868")
        ax.set_title(f"Importancia de variables - {mejor_nombre}")
        plt.tight_layout()
        plt.savefig(OUT_FIG_IMP, dpi=120)
        plt.close()
    elif hasattr(clf_final, "coef_"):
        coefs = clf_final.coef_[0]
        serie_imp = pd.Series(coefs, index=nombres_features).sort_values(key=abs, ascending=False).head(12)
        fig, ax = plt.subplots(figsize=(8, 6))
        serie_imp.sort_values().plot(kind="barh", ax=ax, color="#55A868")
        ax.set_title(f"Coeficientes (importancia) - {mejor_nombre}")
        plt.tight_layout()
        plt.savefig(OUT_FIG_IMP, dpi=120)
        plt.close()

    # ==========================================================
    # 9. GUARDAR MODELO Y METADATOS PARA LA API
    # ==========================================================
    print("9. Guardando modelo entrenado y metadatos...")
    joblib.dump(mejor_pipeline, OUT_MODEL)

    metadatos = {
        "modelo_seleccionado": mejor_nombre,
        "clases": list(mejor_pipeline.classes_),
        "clase_positiva_metrica": pos_label,
        "features_requeridas": columnas_features,
        "columnas_numericas": columnas_numericas,
        "columnas_categoricas": columnas_categoricas,
        "metricas_test": tabla.iloc[0].to_dict(),
        "tabla_comparacion": tabla.to_dict(orient="records"),
        "n_train": int(X_train.shape[0]),
        "n_test": int(X_test.shape[0]),
    }
    with open(OUT_META, "w", encoding="utf-8") as f:
        json.dump(metadatos, f, indent=2, ensure_ascii=False)

    print("\n¡LISTO! Modelo entrenado, evaluado y guardado correctamente.")
    print(f"   -> {OUT_MODEL}")
    print(f"   -> {OUT_META}")
    print(f"   -> {OUT_TABLA}")


if __name__ == "__main__":
    main()
