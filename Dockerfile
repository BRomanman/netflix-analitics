# Usa una imagen ligera de Python
FROM python:3.13-slim

# Crea una carpeta adentro del contenedor para trabajar
WORKDIR /app

# Copia tu lista de librerías
COPY requirements.txt .

# Instala Pandas, Dash, Scikit-learn, Flask, etc.
RUN pip install --no-cache-dir -r requirements.txt

# Copia TODO tu código, bases de datos y modelo entrenado al contenedor
COPY . .

# Avisa qué puertos usará la aplicación:
# 8050 -> Dashboard (Dash)
# 5001 -> API REST del modelo de Machine Learning
EXPOSE 8050
EXPOSE 5001

# El comando por defecto arranca el dashboard.
# El servicio de la API sobreescribe este comando en docker-compose.yml
CMD ["python", "dashboards/app.py"]