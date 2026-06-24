import sqlite3
import pandas as pd
import dash
from dash import dcc, html
import plotly.express as px
import os

# ==========================================
# CARGA DE DATOS
# ==========================================

db_path = os.path.join(
    "data",
    "dataset_final_dashboard.db"
)

conn = sqlite3.connect(db_path)

df = pd.read_sql_query(
    "SELECT * FROM vista_dashboard",
    conn
)

conn.close()

# ==========================================
# KPI'S
# ==========================================

total_titulos = len(df)

total_movies = len(
    df[df["type"] == "Movie"]
)

total_series = len(
    df[df["type"] == "TV Show"]
)

total_visualizaciones = int(
    df["visualizaciones"].sum()
)

# ==========================================
# DISTRIBUCIÓN CONTENIDO
# ==========================================

fig_tipos = px.pie(
    df,
    names="type",
    title="Distribución de Contenido",
    hole=0.4,
    template="plotly_white"
)

# ==========================================
# TOP PAÍSES
# ==========================================

top_paises = (
    df["country"]
    .value_counts()
    .head(10)
    .reset_index()
)

top_paises.columns = [
    "country",
    "cantidad"
]

fig_paises = px.bar(
    top_paises,
    x="country",
    y="cantidad",
    title="Top 10 Países",
    template="plotly_white"
)

# ==========================================
# TOP TÍTULOS MÁS VISTOS
# ==========================================

top_titulos = (
    df.sort_values(
        by="visualizaciones",
        ascending=False
    )
    .head(10)
)

fig_populares = px.bar(
    top_titulos,
    x="title",
    y="visualizaciones",
    color="type",
    title="Top 10 Títulos Más Vistos",
    template="plotly_white"
)

# ==========================================
# TOP GÉNEROS
# ==========================================

generos = (
    df["listed_in"]
    .dropna()
    .str.split(", ")
    .explode()
)

top_generos = (
    generos
    .value_counts()
    .head(10)
    .reset_index()
)

top_generos.columns = [
    "genero",
    "cantidad"
]

fig_generos = px.bar(
    top_generos,
    x="genero",
    y="cantidad",
    title="Top 10 Géneros",
    template="plotly_white"
)

# ==========================================
# TVMAZE - RATINGS
# ==========================================

df_rating = (
    df.dropna(
        subset=["tvmaze_rating"]
    )
    .sort_values(
        by="tvmaze_rating",
        ascending=False
    )
    .head(10)
)

fig_rating = px.bar(
    df_rating,
    x="title",
    y="tvmaze_rating",
    color="type",
    title="Top 10 Ratings TVMaze",
    template="plotly_white"
)

# ==========================================
# TVMAZE - IDIOMAS
# ==========================================

df_language = (
    df["tvmaze_language"]
    .dropna()
    .value_counts()
    .head(10)
    .reset_index()
)

df_language.columns = [
    "language",
    "cantidad"
]

fig_language = px.bar(
    df_language,
    x="language",
    y="cantidad",
    title="Idiomas Detectados por TVMaze",
    template="plotly_white"
)

# ==========================================
# DASHBOARD
# ==========================================

app = dash.Dash(__name__)

estilo_tarjeta = {
    "backgroundColor": "white",
    "padding": "20px",
    "borderRadius": "10px",
    "boxShadow": "0 4px 8px rgba(0,0,0,0.1)",
    "textAlign": "center"
}

app.layout = html.Div(

    style={
        "fontFamily": "Segoe UI",
        "padding": "30px",
        "backgroundColor": "#F4F6F9"
    },

    children=[

        html.H1(
            "🎬 Netflix Analytics Dashboard",
            style={
                "textAlign": "center",
                "marginBottom": "30px"
            }
        ),

        # KPI'S

        html.Div(
            style={
                "display": "flex",
                "gap": "20px",
                "marginBottom": "20px"
            },

            children=[

                html.Div([
                    html.H3("🎬 Total"),
                    html.H2(total_titulos)
                ], style=estilo_tarjeta | {"flex": "1"}),

                html.Div([
                    html.H3("🎥 Películas"),
                    html.H2(total_movies)
                ], style=estilo_tarjeta | {"flex": "1"}),

                html.Div([
                    html.H3("📺 Series"),
                    html.H2(total_series)
                ], style=estilo_tarjeta | {"flex": "1"}),

                html.Div([
                    html.H3("👀 Visualizaciones"),
                    html.H2(f"{total_visualizaciones:,}")
                ], style=estilo_tarjeta | {"flex": "1"})
            ]
        ),

        # FILA 1

        html.Div(
            style={
                "display": "flex",
                "gap": "20px"
            },

            children=[

                html.Div(
                    dcc.Graph(
                        figure=fig_tipos
                    ),
                    style={"flex": "1"}
                ),

                html.Div(
                    dcc.Graph(
                        figure=fig_paises
                    ),
                    style={"flex": "1"}
                )
            ]
        ),

        # FILA 2

        html.Div(
            style={
                "display": "flex",
                "gap": "20px"
            },

            children=[

                html.Div(
                    dcc.Graph(
                        figure=fig_generos
                    ),
                    style={"flex": "1"}
                ),

                html.Div(
                    dcc.Graph(
                        figure=fig_populares
                    ),
                    style={"flex": "1"}
                )
            ]
        ),

        # FILA 3 (API)

        html.Div(
            style={
                "display": "flex",
                "gap": "20px"
            },

            children=[

                html.Div(
                    dcc.Graph(
                        figure=fig_rating
                    ),
                    style={"flex": "1"}
                ),

                html.Div(
                    dcc.Graph(
                        figure=fig_language
                    ),
                    style={"flex": "1"}
                )
            ]
        )
    ]
)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8050,
        debug=False
    )