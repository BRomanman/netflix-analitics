# Usa una imagen ligera de Python
FROM python:3.13-slim

# Crea una carpeta adentro del contenedor para trabajar
WORKDIR /app

# Copia tu lista de librerías
COPY requirements.txt .

# Instala Pandas, Dash, etc.
RUN pip install --no-cache-dir -r requirements.txt

# Copia TODO tu código y bases de datos al contenedor
COPY . .

# Avisa que el dashboard usará este puerto
EXPOSE 8050

# El comando que arranca el dashboard al encender el contenedor
CMD ["python", "dashboards/app.py"]