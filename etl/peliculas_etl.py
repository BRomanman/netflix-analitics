import sqlite3
import pandas as pd
import requests
import os
import time

def ejecutar_etl():

    print("Iniciando Pipeline ETL Netflix...\n")

    # ==========================================
    # 1. EXTRACT
    # ==========================================

    db_path = os.path.join("data", "catalogo_netflix.db")
    csv_path = os.path.join("data", "netflix_titles.csv")

    print("Extrayendo historial de visualizaciones...")

    conn = sqlite3.connect(db_path)

    df_visualizaciones = pd.read_sql_query(
        "SELECT * FROM historial_visualizaciones",
        conn
    )

    conn.close()

    print("Extrayendo catálogo Netflix...")

    df_netflix = pd.read_csv(csv_path)

    # ==========================================
    # 2. TRANSFORM
    # ==========================================

    print("Uniendo visualizaciones con catálogo Netflix...")

    df_final = pd.merge(
        df_visualizaciones,
        df_netflix,
        on="title",
        how="left"
    )

    # Eliminar columna duplicada generada por el merge
    df_final = df_final.drop(columns=["type_x"])

    # Renombrar la columna correcta
    df_final = df_final.rename(
        columns={
            "type_y": "type"
        }
    )

    # ==========================================
    # LIMPIEZA DE DATOS
    # ==========================================

    df_final["country"] = df_final["country"].fillna(
        "Sin información"
    )

    df_final["director"] = df_final["director"].fillna(
        "Sin información"
    )

    df_final["listed_in"] = df_final["listed_in"].fillna(
        "Sin información"
    )

    # ==========================================
    # MÉTRICAS DE NEGOCIO
    # ==========================================

    df_final["popularidad"] = (
        df_final["visualizaciones"] / 1000
    ).round(2)

    # ==========================================
    # 3. API TVMAZE
    # ==========================================

    print("Consultando TVMaze API...")

    datos_api = []

    for titulo in df_final["title"]:

        try:

            url = f"https://api.tvmaze.com/search/shows?q={titulo}"

            response = requests.get(
                url,
                timeout=10
            )

            if response.status_code == 200:

                data = response.json()

                if len(data) > 0:

                    show = data[0]["show"]

                    rating = show.get(
                        "rating",
                        {}
                    ).get(
                        "average"
                    )

                    language = show.get(
                        "language"
                    )

                    status = show.get(
                        "status"
                    )

                    datos_api.append({
                        "title": titulo,
                        "tvmaze_rating": rating,
                        "tvmaze_language": language,
                        "tvmaze_status": status
                    })

                else:

                    datos_api.append({
                        "title": titulo,
                        "tvmaze_rating": None,
                        "tvmaze_language": None,
                        "tvmaze_status": None
                    })

            else:

                datos_api.append({
                    "title": titulo,
                    "tvmaze_rating": None,
                    "tvmaze_language": None,
                    "tvmaze_status": None
                })

            time.sleep(0.2)

        except Exception as e:

            print(
                f"Error con {titulo}: {e}"
            )

            datos_api.append({
                "title": titulo,
                "tvmaze_rating": None,
                "tvmaze_language": None,
                "tvmaze_status": None
            })

    df_api = pd.DataFrame(
        datos_api
    )

    df_final = pd.merge(
        df_final,
        df_api,
        on="title",
        how="left"
    )

    # ==========================================
    # 4. LOAD
    # ==========================================

    print("Guardando dataset final para dashboard...")

    db_final_path = os.path.join(
        "data",
        "dataset_final_dashboard.db"
    )

    conn_final = sqlite3.connect(
        db_final_path
    )

    df_final.to_sql(
        "vista_dashboard",
        conn_final,
        if_exists="replace",
        index=False
    )

    conn_final.close()

    print(
        "\nETL FINALIZADO CORRECTAMENTE\n"
    )

    columnas_resumen = [
        "title",
        "type",
        "visualizaciones",
        "tvmaze_rating",
        "tvmaze_language",
        "tvmaze_status"
    ]

    print(
        df_final[columnas_resumen].head()
    )

if __name__ == "__main__":
    ejecutar_etl()