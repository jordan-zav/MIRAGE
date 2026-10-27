# MIRAGE para QGIS 1.1.0

[English](README.md) · **Español**

Extrae firmas morfológicas de rásteres y revísalas con capas de referencia GIS.
Es la primera edición experimental para QGIS: no clasifica automáticamente el
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

## Uso

Carga un ráster de archivo compatible con GDAL, selecciónalo y elige objetivo y
perfil. Puedes solicitar parámetros iniciales heurísticos; revisa Advanced
parameters y selecciona una carpeta de salida nueva o vacía. Extract ejecuta
una tarea y carga el GeoPackage resultante. Cancel se atiende entre etapas
numéricas, no interrumpe inmediatamente una operación de biblioteca en curso.

Processing incluye mirage:extract_signatures y mirage:recommend_parameters,
utilizables por lotes y desde modelos. Cada ejecución necesita una salida propia.

Se admiten monobanda, RGB y RGBA. Se excluyen NoData y píxeles transparentes.
Geofísica exige una malla completa, orientada al norte, de píxel cuadrado y CRS
proyectado en metros. Rellena huecos o reproyecta de forma explícita antes de
utilizar ese modo; MIRAGE no modifica silenciosamente el original.
La tolerancia de simplificación utiliza unidades del CRS fuente.

El límite inicial es de 16 millones de píxeles y el núcleo se ejecuta en serie
dentro de QGIS. Ampliarlo requiere memoria suficiente; no hay teselado fuera
de memoria. Se conservan SHP, GeoPackage, informes JSON/Markdown y un manifiesto
de finalización. Las carpetas con resultados previos nunca se sobrescriben.

## Código, límites y licencia

El ZIP incluye copias idénticas del núcleo fuente y un manifiesto SHA-256.
La API, CLI y GUI independiente siguen en el
[repositorio](https://github.com/jordan-zav/MIRAGE). Las pruebas sintéticas y de
software no sustituyen validación de campo. Revisa sensor, escala, CRS, caminos,
drenaje y evidencia independiente antes de interpretar.

[GNU GPL v3](https://github.com/jordan-zav/MIRAGE/blob/main/LICENSE.txt); el ZIP
incluye LICENSE.txt completo. Jordan Zavaleta — [GisGeo Dev](https://gisgeo.dev).
