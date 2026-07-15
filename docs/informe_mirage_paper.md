# MIRAGE: extraccion automatizada de firmas geoespaciales para interpretacion geologica y arqueologica

Autor: Jordan Zavaleta

Fecha de actualizacion: mayo de 2026

## Resumen

MIRAGE, Morphological Identification and Remote Analysis for Geospatial Extraction, es un marco de trabajo en Python orientado a extraer firmas lineales e interpretables desde rasteres geoespaciales monobanda, RGB o RGBA. El proyecto no se limita a delinear bordes genericos: organiza la deteccion en torno a un objetivo interpretativo definido por el operador, principalmente firma geologica o firma arqueologica. Esta diferencia es central porque los patrones geologicos suelen expresarse como continuidad direccional, anisotropia, auto-similitud y organizacion estructural, mientras que los patrones arqueologicos pueden presentarse como geometria localizada, trazas rectilineas, anillos, caminos, canales o respuestas tipo pipe.

El sistema integra lectura geoespacial, normalizacion radiometrica, deteccion de bordes o esqueletizacion directa, extraccion de trayectorias centrales, filtrado geometrico, enlace de segmentos, supresion de duplicados, exportacion vectorial y generacion de un reporte JSON por corrida. Incluye una interfaz grafica bilingue, una interfaz por linea de comandos, perfiles de parametros predefinidos, recomendacion automatica de configuracion y pruebas unitarias que validan componentes principales del flujo.

## Palabras clave

Firmas geoespaciales, lineamientos, GeoTIFF, arqueologia, geologia estructural, teledeteccion, morfometria, magnetometria, Python, GIS.

## 1. Introduccion

La interpretacion de lineamientos y firmas morfologicas en geociencias y arqueologia depende de una combinacion de evidencia espacial, textura, continuidad, forma, escala y contexto. Los enfoques puramente basados en bordes tienden a generar resultados abundantes pero poco interpretables: extraen discontinuidades visuales, no necesariamente firmas con valor analitico. MIRAGE aborda ese problema mediante un flujo que convierte rasteres monobanda, RGB o RGBA con canal alfa en entidades vectoriales, pero introduce filtros y modos que orientan la extraccion hacia firmas utiles para analisis geologico o arqueologico.

El proyecto se encuentra organizado como una aplicacion local de escritorio y de linea de comandos. Su nucleo computacional esta en los modulos de extraccion y recomendacion de parametros, mientras que la interfaz grafica ofrece una capa operativa para seleccionar datos, aplicar perfiles, analizar rasteres y generar resultados sin escribir comandos manuales.

## 2. Objetivo del proyecto

El objetivo general de MIRAGE es automatizar la extraccion de firmas geoespaciales interpretables desde imagenes GeoTIFF, produciendo salidas vectoriales compatibles con sistemas GIS.

Los objetivos especificos son:

- Aceptar rasteres GeoTIFF monobanda, RGB de tres bandas y RGBA cuando la cuarta banda corresponde a alfa.
- Convertir informacion multibanda en una representacion de intensidad estable para analisis morfologico.
- Diferenciar entre rasteres tonal-continuos y rasteres ya cercanos a linework binario.
- Extraer trayectorias lineales mediante esqueletizacion, deteccion de bordes, ordenamiento de pixeles y filtrado de candidatos.
- Ajustar la extraccion segun metas interpretativas geologicas o arqueologicas.
- Exportar shapefiles y GeoPackage con atributos tecnicos y metricas de cada entidad.
- Producir un reporte por corrida con parametros, rutas de salida y resumen de lineamientos.
- Facilitar el uso mediante GUI, CLI y perfiles de parametros.

## 3. Alcance funcional actual

La version revisada del proyecto contiene los siguientes componentes funcionales:

- Nucleo de extraccion multibanda en src\line_core.py.
- Orquestador de validacion, ejecucion y reporte en src\pipeline.py.
- Interfaz grafica en src\gui.py.
- Interfaz por linea de comandos en src\cli.py.
- Configuracion de perfiles y modos en src\config.py.
- Recomendador automatico de parametros en src\ai\parameter_advisor.py.
- Pruebas unitarias en tests\test_mirage.py.
- Datos de entrenamiento y ejemplos organizados bajo data\training.
- Recurso visual de marca en assets\branding\logo.png.
- Especificacion de empaquetado para PyInstaller en gui.spec.

No se encontro un informe tecnico completo previamente actualizado. La documentacion existente antes de este archivo consistia principalmente en README.md, docs\workflow.md y docs\parameters.md, que son utiles como guias breves pero no cubren el proyecto completo con estructura de paper.

## 4. Datos de entrada y restricciones

MIRAGE acepta GeoTIFF monobanda y GeoTIFF RGB de tres bandas. Tambien acepta GeoTIFF RGBA si la cuarta banda esta marcada como canal alfa; en ese caso, la banda alfa se ignora y el analisis se realiza sobre las tres primeras bandas. El sistema rechaza imagenes de dos bandas, cuatro bandas sin alfa o conteos de bandas distintos a los esperados.

Esta restriccion responde a una decision de consistencia operativa: el sistema se comporta como extractor de firmas desde productos raster ya preparados para inspeccion visual o analisis morfologico, no como lector universal de cualquier raster geoespacial. En la practica, esto reduce ambiguedades sobre composiciones, escalas y significado de bandas.

## 5. Metodologia computacional

### 5.1 Lectura y normalizacion

El flujo abre el raster con Rasterio, valida el numero de bandas y lee una banda gris directa o las bandas RGB. La imagen se convierte a escala de grises usando la banda unica o promediando las bandas disponibles. Despues se normalizan los valores a un rango entre 0 y 1, reemplazando valores no finitos por cero. Esta normalizacion permite que umbrales y filtros operen sobre una escala estable, independientemente del rango radiometrico original.

### 5.2 Identificacion del tipo de raster

El sistema evalua si la imagen parece binaria o casi binaria mediante muestreo espacial, conteo de valores unicos redondeados y fraccion de pixeles extremos. Si el raster ya se parece a linework, se aplica umbralizacion y esqueletizacion directa. Si el raster es tonal, se suaviza y se ejecuta deteccion de bordes mediante Canny.

Esta bifurcacion evita tratar mapas binarios, mascaras o linework preprocesado como si fueran imagenes continuas, y tambien evita forzar imagenes tonales a una segmentacion demasiado simple.

### 5.3 Construccion del esqueleto

En rasteres binarios, MIRAGE usa umbral de Otsu, selecciona la mascara mas plausible por proporcion de area, elimina componentes pequenos y aplica esqueletizacion. En rasteres tonales, usa Canny con umbrales derivados de GTHR, suavizado controlado por RADI y adelgazamiento morfologico. Luego elimina componentes pequenos usando una longitud minima relacionada con LTHR.

### 5.4 Extraccion de centrolineas

Cada componente conectado del esqueleto se analiza como un conjunto de pixeles. Para ordenar la geometria, el sistema construye una vecindad con arbol KD y busca el camino mas largo dentro del componente mediante recorridos tipo BFS. El resultado es una secuencia ordenada de coordenadas de pixel que representa la trayectoria central dominante de cada componente.

### 5.5 Filtro de candidatos

Las lineas candidatas se filtran con metricas de longitud de camino, cuerda, rectitud, elongacion, razon camino-cuerda, densidad de giro y giro maximo. El modo geologico exige mayor continuidad, rectitud y elongacion. El modo arqueologico permite conservar geometria mas curva o localizada cuando existe evidencia de forma, trayectoria o respuesta antropogenica.

### 5.6 Enlace de segmentos

Los segmentos cercanos se conectan si sus extremos cumplen dos condiciones: distancia menor o igual a DTHR y diferencia angular menor o igual a ATHR. En modo arqueologico se permite un margen mayor para curvas cercanas, porque ciertas firmas antropogenicas no tienen la misma continuidad direccional que un lineamiento geologico.

### 5.7 Conversion a coordenadas reales y salida vectorial

Las coordenadas de pixel se transforman al sistema de referencia del raster usando la transformacion geoespacial original. Cada trayectoria se convierte a LineString y puede simplificarse con FTHR. Las lineas finales se guardan como shapefile y GeoPackage mediante GeoPandas, conservando el CRS del raster de entrada.

### 5.8 Supresion de duplicados paralelos

Antes de exportar, MIRAGE elimina lineas paralelas demasiado cercanas cuando su angulo y distancia sugieren que representan el mismo rasgo. Este paso reduce redundancia y mejora la interpretabilidad de la salida.

## 6. Modos interpretativos

### 6.1 Firma geologica

El modo de firma geologica corresponde internamente al valor signature. Esta configuracion prioriza continuidad estructural, orientaciones preferenciales, elongacion y comportamiento compatible con lineamientos naturales. Es apropiada para interpretar rasgos de tectonica, fracturas, alineamientos, textura geofisica densa o respuestas morfometricas dominadas por relieve.

### 6.2 Firma arqueologica

El modo de firma arqueologica corresponde internamente al valor geometry. Esta configuracion conserva mejor patrones localizados, curvos o geometricos, como anillos, trazas rectilineas, caminos, canales, pipes o marcas antropogenicas sutiles. Reduce la dependencia de una orientacion dominante y permite que formas discretas sobrevivan al filtrado.

## 7. Parametros del modelo

MIRAGE usa seis parametros principales:

- RADI controla el radio de suavizado antes de detectar bordes en rasteres tonales.
- GTHR controla la estrictitud de deteccion de bordes.
- LTHR define la longitud minima de firma en pixeles.
- FTHR define la tolerancia de simplificacion de polilineas en unidades de mapa.
- ATHR define la diferencia angular maxima permitida al enlazar segmentos.
- DTHR define la distancia maxima entre extremos para enlazar segmentos.

El proyecto incluye tres perfiles predefinidos:

- Structural continuity, orientado a firmas naturales mas limpias y menos ruido.
- Geo-arch balance, recomendado como punto de equilibrio para expresion geometrica controlada.
- Anthropogenic detail, orientado a conservar respuestas debiles, cortas o irregulares cuando la evidencia sutil es importante.

## 8. Recomendacion automatica de parametros

El modulo src\ai\parameter_advisor.py analiza una muestra del raster y estima metricas de contraste, desviacion del gradiente, densidad de bordes, varianza local, evidencia circular, evidencia de trazas lineales antropogenicas, direccionalidad de lineamientos, saliencia de anomalias, coherencia de orientacion y propiedades opticas RGB.

Con estas metricas calcula puntajes para firma geologica y firma arqueologica. Tambien clasifica la familia del raster como estructura geologica, geometria arqueologica, imagen satelital optica, realce morfometrico, raster magnetico geologico o raster magnetico arqueologico. A partir de esa clasificacion devuelve perfil, modo, parametros, razon explicativa, metricas y puntajes.

El modulo contempla aceleracion GPU opcional con CuPy y CUDA. En modo automatico, si no hay GPU disponible o si el benchmark pequeno no justifica su uso, selecciona CPU. La GUI mantiene una experiencia simple, mientras que la CLI permite declarar preferencia de computo auto, cpu o gpu para recomendacion automatica.

## 9. Interfaz grafica

La GUI esta implementada con Tkinter y ttk. Incluye:

- Seleccion de GeoTIFF de entrada.
- Seleccion de carpeta de salida.
- Selector de perfil de deteccion.
- Boton para aplicar presets.
- Analisis automatico del raster y aplicacion de parametros recomendados.
- Selector de objetivo interpretativo.
- Campos editables para RADI, GTHR, LTHR, FTHR, ATHR y DTHR.
- Ejecucion de la extraccion.
- Generacion de vista previa de lineamientos sobre el raster.
- Panel de recomendaciones, metricas y notas de ajuste.
- Interfaz bilingue ingles y espanol.
- Integracion de logo y enlace de autor.

La vista previa genera un GeoTIFF RGB con los lineamientos en rojo superpuestos sobre una version remuestreada del raster original. Esto permite comprobar visualmente la coherencia de la salida sin abrir manualmente el shapefile en un GIS.

## 10. Interfaz por linea de comandos

La CLI permite ejecutar MIRAGE en flujos reproducibles o por lotes. Acepta una ruta de entrada, una carpeta de salida, perfil inicial, modo interpretativo, parametros manuales y bandera de recomendacion automatica. Cuando se usa auto, la CLI analiza el raster, recomienda parametros, resuelve el modo interpretativo y ejecuta el pipeline con esa configuracion.

La salida estandar imprime un resumen JSON con rutas, parametros, perfil, modo de computo y estadisticas de lineamientos.

## 11. Salidas

Cada corrida genera como minimo:

- Un shapefile llamado lineaments.shp, junto con sus archivos auxiliares.
- Un GeoPackage llamado lineaments.gpkg con la capa lineaments.
- Un archivo mirage_report.json con rutas, parametros y resumen estadistico.

El shapefile incluye atributos como identificador, modo, longitud en pixeles, cuerda, rectitud, elongacion, angulo, numero de vertices, tamano de pixel y parametros usados. El reporte JSON resume conteo total, longitud total, longitud media, maxima y minima. Cuando es posible, las longitudes se estiman en un CRS metrico mediante reproyeccion UTM; si no se puede estimar un CRS metrico, usa las unidades del CRS original.

## 12. Arquitectura del proyecto

La arquitectura esta separada en capas:

- src\line_core.py contiene algoritmos de vision, morfologia, geometria y exportacion vectorial.
- src\pipeline.py valida entradas, ejecuta el nucleo, calcula resumen vectorial y escribe reporte JSON.
- src\config.py define parametros, presets y modos funcionales.
- src\ai\parameter_advisor.py calcula metricas de raster y recomienda parametros.
- src\gui.py implementa la aplicacion de escritorio y la vista previa.
- src\cli.py implementa ejecucion automatizable por consola.
- tests\test_mirage.py valida el comportamiento principal con rasteres sinteticos.

Esta separacion permite que el nucleo sea reutilizable desde GUI, CLI y pruebas, manteniendo la interfaz como capa de operacion y no como lugar principal de logica cientifica.

## 13. Dependencias

El proyecto depende de:

- NumPy para arreglos y operaciones numericas.
- SciPy para filtros y estructuras espaciales.
- scikit-image para bordes, morfologia, Hough y transformaciones.
- Rasterio para lectura y escritura geoespacial raster.
- GeoPandas, Fiona, Shapely y PyProj para salidas vectoriales y manejo CRS.
- PyInstaller para empaquetado.
- Requests como dependencia HTTP disponible.
- CuPy como dependencia opcional no listada en requirements.txt para aceleracion GPU si el entorno la proporciona.

## 14. Empaquetado

El archivo gui.spec prepara un ejecutable de la GUI con PyInstaller. La especificacion recolecta datos, binarios e imports ocultos de Rasterio, Fiona, PyProj y Shapely, que son dependencias geoespaciales sensibles al empaquetado. La salida esta configurada como aplicacion sin consola y con nombre gui.

El proyecto tambien incluye run_mirage.bat como lanzador local. Para distribucion final convendria renombrar el ejecutable y los artefactos de paquete a MIRAGE para mantener coherencia de marca.

## 15. Validacion actual

Se ejecuto la suite de pruebas con python -m pytest -q. El resultado fue:

11 pruebas pasadas en 14.80 segundos.

Las pruebas cubren:

- Estructura esperada de la recomendacion automatica.
- Escritura de shapefile, GeoPackage y reporte JSON.
- Atributos principales de salida vectorial.
- Deteccion de patrones arqueologicos circulares.
- Deteccion de trazas lineales tipo camino.
- Preferencia geologica en textura geofisica densa.
- Clasificacion de familia satelital optica.
- Clasificacion de realce morfometrico.
- Reduccion de sesgo arqueologico ante dominancia direccional.
- Deteccion de contexto magnetico arqueologico.
- Aceptacion de GeoTIFF RGBA con alfa valido.

## 16. Discusion

MIRAGE presenta una arquitectura coherente para transformar rasteres geoespaciales preparados en firmas vectoriales interpretables. Su mayor fortaleza no es simplemente detectar lineas, sino formalizar una diferencia operativa entre continuidad estructural y geometria antropogenica. Esta distincion permite que el mismo nucleo computacional atienda casos geologicos y arqueologicos con reglas de filtrado distintas.

El sistema tambien muestra una preocupacion practica por el flujo real de trabajo: GUI, CLI, reporte JSON, shapefile, GeoPackage, vista previa, perfiles y recomendacion automatica. Esto lo acerca a una herramienta de analisis aplicada y no solo a un prototipo de algoritmo.

Sin embargo, el alcance actual tambien tiene limites importantes. La extraccion sigue siendo sensible a parametros, escala y preprocesamiento del raster. La recomendacion automatica mejora la ergonomia, pero no reemplaza validacion experta ni comparacion con datos de campo. La salida shapefile se conserva por compatibilidad y se complementa con GeoPackage para flujos GIS modernos.

## 17. Limitaciones

Las principales limitaciones identificadas son:

- Entrada restringida a GeoTIFF monobanda, RGB o RGBA con alfa.
- Dependencia de calidad, resolucion y preparacion previa del raster.
- Posibilidad de falsos positivos en bordes culturales, sombras, drenajes, vegetacion o artefactos de procesamiento.
- Ausencia de evaluacion cuantitativa contra verdad de terreno o dataset anotado.
- Exportacion en shapefile y GeoPackage; el shapefile conserva las restricciones de nombres y tipos propias del formato.
- Empaquetado preparado pero no documentado como release final.
- Dependencia opcional GPU no integrada en requirements.txt.

## 18. Recomendaciones tecnicas

Para fortalecer el proyecto se recomienda:

- Agregar un informe de corrida en formato humano, ademas del JSON.
- Documentar ejemplos reproducibles con datos pequenos incluidos o enlazados.
- Separar claramente datasets de entrenamiento, datasets de prueba y ejemplos de usuario.
- Ampliar pruebas con casos de falla: raster sin CRS, raster sin transformacion util, ausencia de lineamientos y cuatro bandas sin alfa.
- Definir una estrategia de versionado y release del ejecutable.
- Normalizar el nombre de salida de PyInstaller desde gui hacia MIRAGE.
- Revisar textos con mojibake en razones explicativas en espanol dentro del recomendador.

## 19. Conclusiones

MIRAGE ya cuenta con una base funcional consistente para extraccion de firmas geoespaciales desde GeoTIFF monobanda, RGB y RGBA con alfa. El proyecto integra algoritmos de procesamiento de imagen, geometria vectorial, validacion de entradas, modos interpretativos, recomendacion automatica, GUI, CLI, reporte JSON y pruebas unitarias. La evidencia de validacion local confirma que la suite actual pasa correctamente.

El aporte principal del proyecto es conceptual y operativo: desplaza la extraccion desde la idea de lineas genericas hacia firmas orientadas por proposito interpretativo. En geologia, prioriza continuidad, direccion y estructura; en arqueologia, preserva geometria localizada y formas potencialmente antropogenicas. Esa decision hace que MIRAGE sea una herramienta especializada con identidad propia dentro de flujos GIS aplicados a geociencias y prospeccion arqueologica.

El proyecto no debe considerarse cerrado cientificamente sin validacion contra casos reales anotados, pero si se encuentra en una etapa util como herramienta funcional, extensible y empaquetable. Sus proximos avances deberian concentrarse en compatibilidad de entrada, formatos de salida modernos, documentacion de casos de uso, validacion experimental y pulido de distribucion.

## Referencias internas revisadas

- README.md
- docs\workflow.md
- docs\parameters.md
- requirements.txt
- gui.spec
- src\config.py
- src\line_core.py
- src\pipeline.py
- src\cli.py
- src\gui.py
- src\ai\parameter_advisor.py
- tests\test_mirage.py
- data\training\README.md
