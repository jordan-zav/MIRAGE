<p align="center"><a href="README.md">English</a> · <strong>Español</strong></p>

# MIRAGE para QGIS

**Extrae firmas de rásteres y revísalas en su contexto geoespacial.**

La interfaz principal es ahora un panel de QGIS y herramientas de Processing.
La API, CLI y GUI independiente conservan el mismo núcleo numérico.

## Instalación y primer uso

1. Descarga MIRAGE_QGIS_1.1.0.zip desde [Releases](https://github.com/jordan-zav/MIRAGE/releases/latest).
2. En QGIS abre Complementos → Administrar e instalar complementos → Instalar a partir de ZIP.
3. Selecciona el ZIP completo, activa MIRAGE y abre Ráster → MIRAGE.
4. Si faltan bibliotecas de imagen, instálalas con el botón del panel. Requiere
   internet y utiliza una carpeta separada sin sustituir las bibliotecas GIS del anfitrión.
5. Carga un ráster de archivo compatible con GDAL y elige objetivo y perfil.
6. Puedes solicitar recomendaciones heurísticas; revisa Advanced parameters.
7. Selecciona una carpeta nueva o vacía y ejecuta Extract.
8. El GeoPackage se carga en QGIS; contrástalo con el original y evidencia independiente.

Es la **primera edición experimental para QGIS**, comprobada en QGIS 3.44.12
para Windows/Python 3.12. El ZIP admite QGIS 3.40–3.x; otras plataformas y
versiones compatibles requieren comprobaciones propias. Publicarlo en GitHub
no equivale a tener una ficha aprobada en el repositorio oficial QGIS.

## Flujos disponibles

| Objetivo | Función |
| --- | --- |
| Firma geológica | Bordes multiescala, morfología, conexión y filtrado de curvas |
| Geometría arqueológica | Parámetros que favorecen trazas angulares o cerradas |
| Geofísica | TDR, señal analítica, derivadas verticales, THDR y crestas/valles por curvatura |
| Recomendación | Parámetros iniciales heurísticos desde una muestra del ráster |
| Revisión | Capas nativas, tarea en segundo plano y carga de GeoPackage |

Los perfiles modifican parámetros: no determinan el origen de una forma. Las
carreteras, drenaje, iluminación, costuras y ruido pueden parecer objetivos.
Los puntajes del recomendador no son probabilidades calibradas ni un
clasificador geológico entrenado.

## Processing y automatización

- mirage:extract_signatures: extracción, vectores e informes.
- mirage:recommend_parameters: recomendación muestreada a JSON.

Se pueden utilizar por lotes y desde modelos, con una salida propia por
ejecución. El núcleo se ejecuta en serie dentro de una tarea QGIS. Cancel se
atiende entre etapas numéricas, no interrumpe inmediatamente cada llamada de biblioteca.

## Entradas, máscaras y coordenadas

Se admiten monobanda, RGB y RGBA con CRS definido y transformación afín válida.
Los servicios web deben exportarse primero a un ráster local adecuado.

- Se excluyen NoData, no finitos y transparencia; sus vecindades de filtrado
  se protegen y las líneas finales se recortan al dominio válido.
- Geofísica exige malla completa, orientada al norte, de píxel cuadrado y CRS
  proyectado en metros. Rellena huecos o reproyecta explícitamente antes.
- La simplificación utiliza unidades del CRS. Con coordenadas geográficas el
  panel fija FTHR en cero; utiliza cero o reproyecta para aplicar otra tolerancia.
- El límite inicial es de 16 millones de píxeles. Ampliarlo requiere memoria;
  no existe procesamiento completo fuera de memoria. Recorta entradas grandes.
- Cero detecciones es un resultado válido: se genera una capa vacía con
  informe completo, sin inventar lineamientos.

## Salidas y trazabilidad

| Archivo | Contenido |
| --- | --- |
| lineaments.gpkg | Capa que carga el panel |
| lineaments.shp y auxiliares | Shapefile con atributos |
| mirage_report.json | Parámetros, versión, CRS, hash de entrada y estadísticas |
| mirage_report.md | Informe legible |
| mirage_run.json | Estado de ejecución y finalización |

No se sobrescriben resultados. Después de un fallo o cancelación conserva el
manifiesto y elige una carpeta nueva. pix_len mide longitud en píxeles; map_len
y chord utilizan unidades del CRS. Los resúmenes informan metros mediante
conversión de unidades proyectadas o cálculo geodésico.

## Dependencias e interfaz independiente

QGIS utiliza GDAL/OGR, NumPy, SciPy, Shapely y pyproj propios; no necesita
Rasterio ni Fiona. Las bibliotecas de imagen faltantes se instalan con una
acción explícita. La extracción normal es local.

Para ejecutar la fuente independiente usa Python 3.11 y un entorno aislado:

~~~powershell
python -m pip install -r requirements.txt
python src/cli.py -i input.tif -o new_output --profile "Structural continuity" --fthr 0
python src/gui.py
~~~

La CLI admite varias entradas, umbrales, conversión RGB y recomendación opcional.
El ejecutable de Windows de [v1.0.0](https://github.com/jordan-zav/MIRAGE/releases/tag/v1.0.0)
es un paquete histórico; no contiene las mejoras de 1.1.0.

## Comprobaciones y desarrollo

~~~powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check src tests mirage_qgis scripts
python scripts/package_qgis.py --output /ruta/nueva/MIRAGE_QGIS_1.1.0.zip
~~~

El empaquetador utiliza una lista explícita, incluye licencia y manifiesto
SHA-256 y copia el núcleo sin modificarlo. Excluye datos locales, credenciales,
entornos y resultados. Las pruebas QGIS se ejecutan con su Python y plataforma
Qt offscreen, sin controlar el escritorio.

[Validación](docs/VALIDATION_1_1_0.md) · [Flujo](docs/workflow.md) ·
[Parámetros](docs/parameters.md) · [Informe histórico](docs/informe_mirage_paper.md).

Las pruebas de software y sintéticas no demuestran validez de campo. Exactitud
geológica, calidad de interpretación, escalabilidad y otras plataformas
necesitan evaluación independiente.

## Licencia y contacto

[GNU GPL v3](LICENSE.txt). Jordan Zavaleta — [GisGeo Dev](https://gisgeo.dev) ·
[jordanzav@gisgeo.dev](mailto:jordanzav@gisgeo.dev).
