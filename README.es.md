<p align="center"><a href="README.md">English</a> · <strong>Español</strong></p>

# MIRAGE

**Extracción morfológica multiescala de firmas geológicas y arqueológicas.**

Extrae curvas conectadas de rásteres georreferenciados y conserva parámetros y
resultados en productos GIS auditables.

> Una curva detectada puede representar una estructura, drenaje, carretera,
> iluminación, costura o ruido. MIRAGE extrae morfología de imagen, no determina
> automáticamente el origen geológico o arqueológico de cada rasgo.

## Qué incluye

Admite GeoTIFF monobanda, RGB o RGBA, ignorando alfa. Combina respuesta de
bordes multiescala, umbral, limpieza morfológica, unión de curvas y cálculo de
longitud y orientación. Ofrece GUI Tkinter, CLI y recomendaciones iniciales de
parámetros. Exporta Shapefile, GeoPackage y un informe JSON por ejecución.

El perfil geológico prioriza continuidad de lineamientos; el arqueológico
permite formas más cerradas o angulares. Los perfiles cambian parámetros,
no certifican la interpretación de una forma.

## Descarga e instalación

Windows dispone de una aplicación empaquetada en la
[última release](https://github.com/jordan-zav/MIRAGE/releases/latest).
Para ejecutar desde código requiere Python 3.11 y dependencias GIS compatibles:

~~~powershell
git clone https://github.com/jordan-zav/MIRAGE.git
cd MIRAGE
python -m pip install -r requirements.txt
python src/gui.py
~~~

Prepara un entorno aislado antes de instalar. En Windows también puedes abrir
run_mirage.bat. Para línea de comandos:

~~~powershell
python src/cli.py -i input.tif -o output_folder --profile "Structural continuity"
~~~

## Control antes y después de procesar

1. Comprueba CRS, tamaño de píxel, NoData y estadísticas de la entrada.
2. Elige un perfil y escalas adecuados para el objetivo.
3. Compara varios parámetros; no aceptes un único umbral sin revisión.
4. Superpón las curvas sobre el ráster original y capas auxiliares.
5. Identifica drenaje, caminos, costuras y direcciones de adquisición.
6. Revisa distribuciones de longitud y orientación.
7. Conserva el informe junto a los vectores entregados.

| Salida | Contenido |
| --- | --- |
| lineaments.shp | Geometría y atributos Shapefile |
| lineaments.gpkg | Capa equivalente GeoPackage |
| mirage_report.json | Entradas, parámetros, rutas y métricas de resumen |

## Método y desarrollo

- [Flujo](docs/workflow.md).
- [Parámetros](docs/parameters.md).
- [Informe técnico](docs/informe_mirage_paper.md).

~~~powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
~~~

src/pipeline.py coordina el proceso; src/line_core.py contiene algoritmos;
src/config.py define perfiles; src/ai recomienda parámetros; src/gui.py y
src/cli.py son las interfaces. Las pruebas ejercitan el procesamiento y casos
geofísicos sintéticos.

## Estado y límites

La release pública es 1.0.0. Densidad y conectividad cambian con resolución,
contraste, suavizado y umbral. Una curva continua no demuestra una falla o un
rasgo arqueológico. La validación por sensor, región y escala sigue siendo una
tarea independiente, con cartografía, imágenes, geofísica o evidencia de campo.

## Licencia y contacto

[GNU GPL v3](LICENSE.txt). Jordan Zavaleta — GisGeo Dev.
[Correo](mailto:jordanzav@gisgeo.dev) · [Sitio web](https://gisgeo.dev).
