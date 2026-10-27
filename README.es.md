<p align="center"><a href="README.md">English</a> · <strong>Español</strong></p>

# MIRAGE para QGIS

**Extrae firmas de rásteres y revísalas en su contexto geoespacial.**

La interfaz principal es ahora un panel de QGIS y herramientas de Processing.
La API, CLI y GUI independiente conservan el mismo núcleo numérico.

## Instalación y primer uso

1. Descarga MIRAGE_QGIS_1.2.0.zip desde [Releases](https://github.com/jordan-zav/MIRAGE/releases/latest).
2. En QGIS abre Complementos → Administrar e instalar complementos → Instalar a partir de ZIP.
3. Selecciona el ZIP completo, activa MIRAGE y abre Ráster → MIRAGE.
4. Si faltan bibliotecas de imagen, instálalas con el botón del panel. Requiere
   internet y utiliza una carpeta separada sin sustituir las bibliotecas GIS del anfitrión.
5. Carga un raster de archivo GDAL, declara el tipo de entrada e indica la escala en metros.
6. Centra el mapa en una zona valida, pulsa Compare 3 previews y elige una variante.
7. Selecciona una carpeta nueva o vacía y ejecuta Extract.
8. El GeoPackage se carga en QGIS; contrástalo con el original y evidencia independiente.

Es la **edición experimental para QGIS**, comprobada en QGIS 3.44.12
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
- mirage:preview_candidates: tres variantes sobre la misma ventana nativa.

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
es un paquete histórico; no contiene las mejoras de 1.2.0.

## Comprobaciones y desarrollo

~~~powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check src tests mirage_qgis scripts
python scripts/package_qgis.py --output /ruta/nueva/MIRAGE_QGIS_1.2.0.zip
~~~

El empaquetador utiliza una lista explícita, incluye licencia y manifiesto
SHA-256 y copia el núcleo sin modificarlo. Excluye datos locales, credenciales,
entornos y resultados. Las pruebas QGIS se ejecutan con su Python y plataforma
Qt offscreen, sin controlar el escritorio.

[Validación](docs/VALIDATION_1_2_0.md) · [Flujo](docs/workflow.md) ·
[Parámetros](docs/parameters.md) · [Informe histórico](docs/informe_mirage_paper.md).

Las pruebas de software y sintéticas no demuestran validez de campo. Exactitud
geológica, calidad de interpretación, escalabilidad y otras plataformas
necesitan evaluación independiente.

## Licencia y contacto

[GNU GPL v3](LICENSE.txt). Jordan Zavaleta — [GisGeo Dev](https://gisgeo.dev) ·
[jordanzav@gisgeo.dev](mailto:jordanzav@gisgeo.dev).


## Configuracion adaptable en metros (1.2)

1. Selecciona el tipo real de entrada: relieve, campo magnetico, gravedad, imagen optica o desconocido. La textura no establece su origen.
2. Indica objetivo, longitud minima, radio de suavizado, distancia de enlace y simplificacion en metros. Este flujo requiere CRS proyectado en metros y pixeles cuadrados ortogonales. Para geofisica, ademas, malla orientada al norte y ventana sin huecos.
3. Situa el centro del mapa sobre el area que quieras revisar y pulsa Compare 3 previews. Se procesan las mismas 256 por 256 celdas nativas con tres sensibilidades; las muestras reducidas de Recommend nunca cambian la resolucion usada para convertir metros a pixeles.
4. Compara las superposiciones y parametros; elige Use balanced, conservative o detail. No se elige un ganador por numero de trazas. Se guardan el recorte, PNG, GeoPackage, candidatos y receta seleccionada en la ruta mostrada.
5. Selecciona una carpeta nueva para la extraccion completa. La receta queda incluida en su informe JSON. Cambiar el raster o los ajustes anula la seleccion. Los limites del recorte pueden afectar el resultado; no se promete identidad entre recorte y extraccion regional.

Use manual advanced parameters conserva el flujo por pixeles y parametros expertos sin receta. Recommend solo prepara candidatos; no decide origen arqueologico ni cambia el tipo declarado. La entrada desconocida usa extraccion generica de bordes. Preserve geometry es una eleccion explicita del usuario.

Processing: mirage:recommend_parameters genera el plan, mirage:preview_candidates compara una ventana (CENTER opcional en CRS fuente, WINDOW_PIXELS de 32 a 512), y mirage:extract_signatures admite RECIPE con un JSON seleccionado. La API compartida ofrece recommend_adaptive, select_recipe y validate_recipe; CLI acepta --recipe ruta.json. Cada receta esta ligada a ruta, tamano y fecha de la fuente; no se aplica automaticamente a otro archivo. El informe de extraccion calcula tambien SHA-256 de la entrada.

La longitud minima fisica se comprueba de nuevo en la geometria final, despues de simplificar y recortar mascaras. La resolucion puede impedir representar longitudes menores de dos pixeles. Las variantes alteran suavizado y umbral; mantienen longitud minima, enlace, simplificacion y objetivo. Los PNG muestran el raster original; las trazas TDR provienen del campo transformado. Ni las formas circulares ni un mayor numero de trazas demuestran origen o precision.

RADI se redondea a pixeles nativos. El detector tonal conserva sigma minimo de 1,2 pixeles y geofisica de 0,5; solicitar cero suavizado no desactiva ese filtro numerico. El JSON registra la conversion a parametros.
