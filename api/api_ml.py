"""
api_ml.py
====================================================
API REST - Netflix Analytics Dashboard
Evaluación Final Transversal - SCY1101

Expone el modelo de Machine Learning (models/modelo_final.pkl)
a través de endpoints HTTP para que pueda ser consumido por el
dashboard, por otro sistema, o probado en vivo durante la demo.

ENDPOINTS
---------
GET  /health          -> estado del servicio
GET  /model-info       -> metadatos, métricas y features del modelo
POST /predict          -> predicción para un título nuevo
GET  /predict/ejemplo   -> ejemplo de predicción ya resuelto (para demo rápida)

EJEMPLO DE USO (POST /predict)
--------------------------------
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
"""

import json
import os

import joblib
import pandas as pd
from flask import Flask, jsonify, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "modelo_final.pkl")
META_PATH = os.path.join(BASE_DIR, "..", "models", "metadatos_modelo.json")

app = Flask(__name__)

# ==========================================================
# CARGA DEL MODELO Y METADATOS AL INICIAR LA API
# ==========================================================
print("Cargando modelo entrenado...")
modelo = joblib.load(MODEL_PATH)

with open(META_PATH, "r", encoding="utf-8") as f:
    metadatos = json.load(f)

FEATURES_REQUERIDAS = metadatos["features_requeridas"]
print(f"Modelo cargado: {metadatos['modelo_seleccionado']}")
print(f"Features esperadas: {FEATURES_REQUERIDAS}")


def construir_dataframe_entrada(payload: dict) -> pd.DataFrame:
    """Valida que vengan todas las features y arma el DataFrame de 1 fila
    en el mismo formato que espera el pipeline entrenado."""
    payload = dict(payload)  # copia para no mutar el original

    # decada_lanzamiento se puede derivar automáticamente si no viene
    if "decada_lanzamiento" in FEATURES_REQUERIDAS and "decada_lanzamiento" not in payload:
        if "release_year" not in payload:
            raise ValueError("Falta 'release_year' (necesario para derivar 'decada_lanzamiento')")
        payload["decada_lanzamiento"] = (int(payload["release_year"]) // 10) * 10

    faltantes = [f for f in FEATURES_REQUERIDAS if f not in payload]
    if faltantes:
        raise ValueError(f"Faltan campos obligatorios: {faltantes}")

    fila = {f: payload[f] for f in FEATURES_REQUERIDAS}
    return pd.DataFrame([fila])


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "modelo_cargado": metadatos["modelo_seleccionado"]})


@app.route("/model-info", methods=["GET"])
def model_info():
    return jsonify(metadatos)


@app.route("/predict", methods=["POST"])
def predict():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Body JSON inválido o ausente"}), 400

    try:
        X_nuevo = construir_dataframe_entrada(payload)
    except ValueError as e:
        return jsonify({"error": str(e), "features_requeridas": FEATURES_REQUERIDAS}), 400

    prediccion = modelo.predict(X_nuevo)[0]
    probabilidades = modelo.predict_proba(X_nuevo)[0]
    clases = list(modelo.classes_)

    return jsonify({
        "prediccion": prediccion,
        "probabilidades": {clases[i]: round(float(probabilidades[i]), 4) for i in range(len(clases))},
        "modelo_usado": metadatos["modelo_seleccionado"],
        "input_recibido": payload,
    })


@app.route("/predict/ejemplo", methods=["GET"])
def predict_ejemplo():
    """Endpoint de conveniencia para la demo en vivo: no requiere
    armar un JSON a mano, sólo hacer GET."""
    ejemplo = {
        "release_year": 2021,
        "decada_lanzamiento": 2020,
        "rating": "TV-MA",
        "pais_principal": "United States",
        "num_actores": 6,
        "tiene_director": 0,
        "largo_descripcion": 210,
        "mes_agregado": 9,
    }
    X_nuevo = pd.DataFrame([ejemplo])
    prediccion = modelo.predict(X_nuevo)[0]
    probabilidades = modelo.predict_proba(X_nuevo)[0]
    clases = list(modelo.classes_)

    return jsonify({
        "input_ejemplo": ejemplo,
        "prediccion": prediccion,
        "probabilidades": {clases[i]: round(float(probabilidades[i]), 4) for i in range(len(clases))},
    })


if __name__ == "__main__":
    # Puerto 5001 para no chocar con el dashboard Dash (8050)
    app.run(host="0.0.0.0", port=5001, debug=False)
