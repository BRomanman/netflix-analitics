# Integración API TVMaze

## Descripción

TVMaze es una API pública utilizada para obtener información adicional sobre series y programas de televisión.

Sitio oficial:

https://api.tvmaze.com

## Objetivo

Complementar la información existente del catálogo Netflix con datos externos obtenidos en tiempo real.

## Endpoint utilizado

Ejemplo:

```text
https://api.tvmaze.com/search/shows?q=Wednesday
```

## Datos obtenidos

La API entrega información como:

* Nombre del programa
* Idioma
* Estado de emisión
* Rating promedio

## Campos incorporados al proyecto

* tvmaze_rating
* tvmaze_language
* tvmaze_status

## Beneficio

Permite enriquecer el análisis incorporando información externa no disponible en el dataset original.
