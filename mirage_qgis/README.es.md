# MIRAGE para QGIS 1.2.0

[English](README.md) · **Español**

Extrae firmas morfológicas de rásteres y revísalas con capas de referencia GIS.
Es la edición experimental para QGIS: no clasifica automáticamente el
origen geológico o arqueológico de las formas.

## Instalación

1. Conserva el ZIP completo. En QGIS abre Complementos → Administrar e instalar
   complementos → Instalar a partir de ZIP y selecciona el archivo.
2. Activa MIRAGE y abre Ráster → MIRAGE.
3. Si faltan bibliotecas de imagen, usa el botón de instalación del panel.
   Requiere internet y utiliza una carpeta aislada sin sustituir la pila GIS de QGIS.
4. Reinicia QGIS si la instalación lo solicita.

Requiere QGIS 3.40–3.x y Python 3.10 o superior. Comprobado en QGIS 3.44.12 para
Windows/Python 3.12. Utiliza GDAL, NumPy, SciPy, Shapely y pyproj del anfitrión;
scikit-image 0.25–0.26 y las dependencias de imagen faltantes se instalan aparte.
La primera descarga puede tardar varios minutos; la extracción normal es local.


## Configuracion adaptable en metros (1.2)

1. Selecciona el tipo real de entrada: relieve, campo magnetico, gravedad, imagen optica o desconocido. La textura no establece su origen.
2. Indica objetivo, longitud minima, radio de suavizado, distancia de enlace y simplificacion en metros. Este flujo requiere CRS proyectado en metros y pixeles cuadrados ortogonales. Para geofisica, ademas, malla orientada al norte y ventana sin huecos.
3. Situa el centro del mapa sobre el area que quieras revisar y pulsa Compare 3 previews. Se procesan las mismas 256 por 256 celdas nativas con tres sensibilidades; las muestras reducidas de Recommend nunca cambian la resolucion usada para convertir metros a pixeles.
4. Compara las superposiciones y parametros; elige Use balanced, conservative o detail. No se elige un ganador por numero de trazas. Se guardan el recorte, PNG, GeoPackage, candidatos y receta seleccionada en la ruta mostrada.
5. Selecciona una carpeta nueva para la extraccion completa. La receta queda incluida en su informe JSON. Cambiar el raster o los ajustes anula la seleccion. Los limites del recorte pueden afectar el resultado; no se promete identidad entre recorte y extraccion regional.

Use manual advanced parameters conserva el flujo por pixeles y parametros expertos sin receta. Recommend solo prepara candidatos; no decide origen arqueologico ni cambia el tipo declarado. La entrada desconocida usa extraccion generica de bordes. Preserve geometry es una eleccion explicita del usuario.

Processing: mirage:recommend_parameters genera el plan, mirage:preview_candidates compara una ventana (CENTER opcional en CRS fuente, WINDOW_PIXELS de 32 a 512), y mirage:extract_signatures admite RECIPE con un JSON seleccionado. La API compartida ofrece recommend_adaptive, select_recipe y validate_recipe; CLI acepta --recipe ruta.json. Cada receta esta ligada a ruta, tamano y fecha de la fuente; no se aplica automaticamente a otro archivo. El informe de extraccion calcula tambien SHA-256 de la entrada.

La longitud minima fisica se comprueba de nuevo en la geometria final, despues de simplificar y recortar mascaras. La resolucion puede impedir representar longitudes menores de dos pixeles. Las variantes alteran suavizado y umbral; mantienen longitud minima, enlace, simplificacion y objetivo. Los PNG muestran el raster original; las trazas TDR provienen del campo transformado. Ni las formas circulares ni un mayor numero de trazas demuestran origen o precision.

## Código, límites y licencia

El ZIP incluye copias idénticas del núcleo fuente y un manifiesto SHA-256.
La API, CLI y GUI independiente siguen en el
[repositorio](https://github.com/jordan-zav/MIRAGE). Las pruebas sintéticas y de
software no sustituyen validación de campo. Revisa sensor, escala, CRS, caminos,
drenaje y evidencia independiente antes de interpretar.

[GNU GPL v3](https://github.com/jordan-zav/MIRAGE/blob/main/LICENSE.txt); el ZIP
incluye LICENSE.txt completo. Jordan Zavaleta — [GisGeo Dev](https://gisgeo.dev).

RADI se redondea a pixeles nativos. El detector tonal conserva sigma minimo de 1,2 pixeles y geofisica de 0,5; solicitar cero suavizado no desactiva ese filtro numerico. El JSON registra la conversion a parametros.
