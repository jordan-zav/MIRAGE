# MIRAGE 1.3.0

[English](README.md) · [API](docs/API.md) · [Validación](docs/VALIDATION_1_3_0.md)

MIRAGE extrae lineamientos ráster para revisión humana. QGIS es la interfaz principal; la distribución mirage-geo expone el paquete Python mirage y el CLI mirage. GPL-3.0-or-later, Jordan Zavaleta.

**Alcance de 1.3.0:** las rutas nuevas, los bancos y la calibración se aplican solo al modo geofísico (grillas magnéticas y gravimétricas). Los modos geológico y arqueológico conservan el comportamiento de v1.2.0 y no se reevaluaron. Ninguna ruta identifica el origen geológico de un rasgo; la textura o geometría circular tampoco demuestra arqueología.

## Instalación

En QGIS, descarga MIRAGE_QGIS_1.3.0.zip del [release v1.3.0](https://github.com/jordan-zav/MIRAGE/releases/tag/v1.3.0). Ve a Complementos → Administrar e instalar complementos → Instalar a partir de ZIP y abre el panel MIRAGE. Su instalador explícito de dependencias usa el directorio de ajustes de QGIS; MIRAGE_QGIS_DEPENDENCIES permite elegir otro. Conserva las bibliotecas GIS del anfitrión. Comprobado con QGIS 3.44.12 en Windows, fuera de pantalla.

Para Python 3.11 o 3.12, usa un entorno aislado (Git solo hace falta para instalar desde el tag):

~~~shell
python -m venv .venv
# Activa .venv en tu shell y ejecuta:
pip install mirage-geo
pip install "mirage-geo[io,wavelets,nn]"
# o directamente desde el tag:
pip install "mirage-geo @ git+https://github.com/jordan-zav/MIRAGE@v1.3.0"
mirage --help
~~~

El segundo comando añade lectura/escritura ráster y vectorial independiente, PyWavelets y ONNX Runtime CPU. El extra gui añade dependencias de la interfaz Tk; dev añade herramientas de pruebas y construcción. Ningún extra incluye pesos ni PyTorch. Para desarrollo desde el código usa pip install -e ".[dev,wavelets,nn,io]".

## Rutas y perfiles geofísicos

| Ruta/perfil | Comportamiento |
| --- | --- |
| A: geomatic | THDR, worming multinivel, wavelets y anisotropía del tensor; sin pesos neuronales |
| geophysics (predeterminado) | Worming calibrado a 0,50; alturas 0/2/4 y escalas 1/2/4 veces el tamaño de celda |
| legacy-v120 | Flujo histórico de archivos v1.2.0, mediante API, CLI y QGIS |
| legacy-array | Valores anteriores de arrays, THDR a 0,20; distinto de la paridad del flujo de archivos |
| B: neural/onnx | Inferencia experimental con modelo externo, manifiesto explícito y SHA-256 |

mirage.profiles() expone la calibración del motor. Se pueden indicar método y umbral explícitos. Las recetas antiguas ligadas a una fuente conservan legacy-v120 salvo selección explícita. Consulta [perfiles científicos](docs/SCIENTIFIC_PROFILES.md).

~~~python
import numpy as np
import mirage

image = np.tile(np.tanh((np.arange(64) - 31) / 3), (64, 1))
result = mirage.extract(image, pixel_size=25)
result.write("new_lineaments.gpkg", "EPSG:32750")
print(mirage.profiles(), mirage.provenance())
~~~

Las grillas geofísicas deben ser finitas, norte arriba, cuadradas y proyectadas en metros. Quien llama la API de arrays debe suministrar una transformación métrica correcta; los adaptadores de archivos/QGIS comprueban el CRS. Las escalas y alturas de continuación no estiman profundidades geológicas. El cálculo es global en memoria; no se certifica escalabilidad regional ni procesamiento fuera de memoria. Recorta deliberadamente los rásteres grandes. Las salidas conservan geometría, ruta/método, longitud, azimut, fuerza y escala/altura aplicables; worming guarda amplitud por vértice. La fuerza no es confianza geológica.

~~~shell
mirage -i input.tif -o new_output --feature-mode "Geophysics Potential Fields" --input-kind magnetic --geophysics-profile geophysics
mirage -i input.tif -o legacy_output --feature-mode "Geophysics Potential Fields" --input-kind magnetic --geophysics-profile legacy-v120
~~~

QGIS conserva la declaración de entrada, recomendaciones físicas, tres vistas previas de la misma ventana nativa, selección humana y recetas ligadas a la fuente. Consulta [flujo](docs/workflow.md) y [parámetros](docs/parameters.md).

## Resultados y límites

El banco ampliado contiene 3.000 escenas Harmonica independientes de 128 × 128: 1.800 de entrenamiento, 600 de validación y 600 de prueba. La referencia es la traza superior proyectada de los cuerpos, con tolerancia principal de dos celdas. La calibración y selección del modelo usaron solo validación.

| Método de prueba | Precisión | Cobertura | F1 | Error de posición (celdas) |
| --- | ---: | ---: | ---: | ---: |
| A worming | 0,509 | 0,719 | 0,564 | 1,898 |
| A wavelets | 0,473 | 0,785 | 0,550 | 1,578 |
| B TEED, semilla elegida en validación | 0,824 | 0,662 | 0,715 | 8,569 |

B mejora F1 pero empeora la posición; las predicciones vacías reciben la penalización diagonal predefinida (16 escenas B frente a cero worming). Incumple el criterio conjunto de superioridad. La tabla no implica mayor cobertura sintética para B.

Pilbara, Mount Isa y Broken Hill comparan detecciones con magnetometría RTP y fallas/zonas de cizalla cartografiadas a 1:1.000.000 por Geoscience Australia (CC BY 4.0). Las regiones comparten compilación, procesamiento y escala cartográfica: no son fuentes de validación independientes entre sí. A 500 m B aumenta la cobertura de fallas cartografiadas (IC95 pareado de +4,79 a +9,32 puntos porcentuales) y también la densidad alejada (IC95 de +0,0037 a +0,0173 km/km²), por encima del margen permitido. B ofrece más cobertura cartográfica, pero peor posición sintética e incumple el criterio conjunto real. La concordancia cartográfica no es verdad geológica ni identifica origen. Consulta [resultados verificables](docs/VALIDATION_1_3_0.md) e [investigación](docs/research/README.md).

## Ruta B con tu propio modelo

Instala el extra nn. Obtén o entrena un modelo ONNX propio con permisos adecuados y coloca un manifiesto JSON junto a él. MIRAGE no descarga pesos al importar ni extraer. El modelo debe aceptar float32 NCHW, tres canales repetidos de gris normalizado, multiplicados por input_scale y con sustracción de mean por canal; devuelve un mapa de probabilidades, o logits si se declara. Se rellena por reflexión hasta multiple y se recorta la salida al tamaño de entrada. Valida ese preprocesamiento y el umbral para tu levantamiento.

~~~json
{
  "path": "my-model.onnx",
  "sha256": "SUSTITUIR_POR_EL_SHA256_DE_64_CARACTERES_DEL_MODELO",
  "code_license": "MIT",
  "weights_license": "MIT",
  "multiple": 8,
  "input_scale": 255.0,
  "mean": [103.939, 116.779, 123.68],
  "logits": false
}
~~~

Las licencias deben reflejar permisos reales; no copies las etiquetas del ejemplo sin comprobarlos. Se admiten MIT, Apache-2.0 y BSD-3-Clause para código, y también CC0-1.0 para pesos. Calcula SHA-256 del binario exacto y sustituye el marcador. La ruta relativa del modelo se resuelve junto al manifiesto.

~~~python
result = mirage.extract(image, route="neural", method="onnx",
                        model="my-model.json", pixel_size=25, threshold=0.5)
result.write("new_neural_lineaments.gpkg", "EPSG:32750")
~~~

Este ejemplo usa la API de arrays; el CLI histórico de archivos y el panel propio QGIS no exponen selección ONNX. No se distribuyen pesos. El código TEED es MIT, pero no se confirmó un permiso separado para su checkpoint original. La investigación anterior registró el MIT general del repositorio como base; eso no constituye una autorización independiente específica para pesos. Revisa los derechos antes de redistribuir modelos originales o derivados. [Reproducción y hashes](docs/research/REPRODUCING_MODELS.md).

## Cita y desarrollo

Cita: Zavaleta, Jordan. MIRAGE: reproducible raster lineament extraction, versión 1.3.0. https://github.com/jordan-zav/MIRAGE. Metadatos en [CITATION.cff](CITATION.cff) y [.zenodo.json](.zenodo.json). Aquí no se asignó DOI; incorpora el DOI real de Zenodo después del release.

~~~shell
python -m pytest
python -m ruff check src tests mirage_qgis scripts setup.py
python -m build
python scripts/package_qgis.py --output MIRAGE_QGIS_1.3.0.zip
~~~

[Cambios](CHANGELOG.md) · [Borrador del release](docs/research/release_notes_1.3.0.md) · [Guía para publicar](docs/PUBLICAR_PYPI.es.md) · [GPL-3.0-or-later](LICENSE.txt).
