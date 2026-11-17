# Nivel de azar y nulo estructural de la concordancia real de MIRAGE

Fecha de ejecución: 2026-11-16, hora local. Revisión posterior a la publicación de 1.3.0; no cambia artefactos ni parámetros publicados. Alcance: geofísica, worming y ruta B de la campaña 1.3.0. Sin entrenamiento ni selección nueva de parámetros.

## Métodos

Se leyeron las tres rejillas proyectadas de la campaña, sus máscaras válidas y las fallas de Geoscience Australia a escala 1:1.000.000. Son los mismos datos públicos CC BY 4.0 de la validación 1.3.0. La campaña y el banco se mantuvieron intactos. results/metadata.json identifica por SHA-256 cada entrada consumida, incluidos parámetros sellados, manifiesto y modelo ONNX. Las coberturas de los métodos sellados reproducen las publicadas: Pilbara 1,5772 % / 7,5229 %, Mount Isa 1,7762 % / 10,4763 % y Broken Hill 3,0314 % / 8,3348 %, worming / B respectivamente.

Variantes: worming con umbral sellado 0,50; worming 0,20 exclusivamente diagnóstico; B con semilla de entrenamiento 20261115, umbral sellado 0,65 y el manifiesto de la campaña. Se ejecutó de nuevo la inferencia ONNX, que comprueba el hash del modelo. Continuaciones 0, 200 y 400 m; escalas 100, 200 y 400 m; misma vectorización y tratamiento de huecos que el evaluador original. No se tocó la lógica de selección ni el criterio de superioridad de la versión 1.3.0.

matched_fraction es la longitud detectada a distancia menor o igual que la tolerancia de una falla observada, dividida por la longitud detectada observada. Se muestrean ambas geometrías a pasos de como máximo 50 m, con pesos de longitud y pertenencia a celdas válidas. chance_fraction es la proporción de los centros de celdas válidas a esa distancia de las muestras de fallas. Como las celdas tienen área constante (100 por 100 m), es una cuadratura de la fracción de área, no una intersección vectorial exacta. Se reutiliza la misma aproximación espacial de la evaluación histórica. Una muestra de falla puede estar hasta 25 m del punto más próximo sobre la polilínea; el muestreo de área añade discretización de 100 m. No se debe interpretar el último decimal como exactitud cartográfica.

Para el nulo se conserva el conjunto completo de muestras detectadas y sus pesos. Se centra en su centroide ponderado por longitud; se aplica una sola rotación uniforme entre 0 y 360 grados y una traslación que sitúa ese centroide uniformemente en el área válida (celda válida uniforme y posición uniforme dentro de ella). Todas las líneas comparten la transformación. No hay reescalado, movimientos independientes ni retorno periódico por los bordes. Se admite una colocación si conserva al menos el 60 % de la longitud original en celdas válidas; el acierto se calcula sobre esa longitud retenida. La geometría antes del recorte conserva distancias, conectividad, longitudes y ángulos relativos; el recorte puede eliminar partes. El criterio reduce, pero no elimina, el sesgo de borde. La distribución es condicional a esta aceptación; no tiene por qué coincidir con el azar por área.

Se aceptaron 1.000 colocaciones por región y variante: 9.000 realizaciones en total, evaluadas conjuntamente a 250, 500 y 1.000 m. Generador NumPy default_rng, semilla 20261116 reiniciada para cada conjunto; no implica realizaciones independientes entre variantes o tolerancias. Los intentos y las fracciones de longitud retenida se conservan. Límite de intentos: un millón por conjunto; si no se alcanza el número requerido, la función falla explícitamente.

El exceso es el acierto observado menos la media del nulo. El intervalo del 95 % que se presenta es [observado menos percentil 97,5 del nulo; observado menos percentil 2,5 del nulo]. Es un intervalo de referencia de la diferencia frente a colocaciones aleatorias, no un intervalo de confianza de exactitud geológica ni de la media estimada. El valor p unilateral es (1 + número de nulos con acierto mayor o igual al observado) / 1001. Incluye empates y su mínimo es 0,000999. La prueba es condicional al mecanismo de colocación y a la referencia cartográfica, no a una hipótesis de origen geológico.

## Resultados a 500 m

pp significa puntos porcentuales. Los valores p de las tablas no están ajustados por multiplicidad.

| Región | Variante | Tolerancia m | Azar área % | Acierto % | Media nulo % | Exceso pp | Intervalo 95 % pp | p unilateral |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| Pilbara | Worming 0,50 | 500 | 5.63 | 98.20 | 4.62 | +93.59 | [+17.71, +98.20] | 0.0110 |
| Pilbara | Worming 0,20 diagnóstico | 500 | 5.63 | 28.81 | 5.37 | +23.44 | [-1.95, +28.81] | 0.0310 |
| Pilbara | B 20261115, 0,65 | 500 | 5.63 | 23.60 | 6.22 | +17.38 | [-4.86, +23.60] | 0.0490 |
| Mount-Isa | Worming 0,50 | 500 | 28.66 | 11.55 | 28.59 | -17.04 | [-56.90, +11.55] | 0.6983 |
| Mount-Isa | Worming 0,20 diagnóstico | 500 | 28.66 | 33.71 | 30.43 | +3.28 | [-9.46, +18.15] | 0.3626 |
| Mount-Isa | B 20261115, 0,65 | 500 | 28.66 | 38.82 | 30.35 | +8.46 | [-10.13, +25.06] | 0.1958 |
| Broken-Hill | Worming 0,50 | 500 | 31.75 | 39.47 | 32.34 | +7.14 | [-15.29, +27.67] | 0.2617 |
| Broken-Hill | Worming 0,20 diagnóstico | 500 | 31.75 | 33.66 | 32.64 | +1.03 | [-10.69, +12.88] | 0.4346 |
| Broken-Hill | B 20261115, 0,65 | 500 | 31.75 | 36.20 | 32.64 | +3.55 | [-10.92, +18.03] | 0.3087 |

| Región | Variante | Longitud detectada km | Densidad km/km² | Intentos para 1.000 aceptados | Retención media % |
| --- | --- | ---: | ---: | ---: | ---: |
| Pilbara | Worming 0,50 | 2.749 | 0.00149 | 1002 | 99.37 |
| Pilbara | Worming 0,20 diagnóstico | 41.596 | 0.02262 | 1509 | 77.34 |
| Pilbara | B 20261115, 0,65 | 20.287 | 0.01103 | 6018 | 79.50 |
| Mount-Isa | Worming 0,50 | 51.493 | 0.02779 | 1151 | 85.38 |
| Mount-Isa | Worming 0,20 diagnóstico | 1109.320 | 0.59877 | 2042 | 74.93 |
| Mount-Isa | B 20261115, 0,65 | 95.917 | 0.05177 | 2080 | 76.96 |
| Broken-Hill | Worming 0,50 | 66.626 | 0.03955 | 1262 | 83.13 |
| Broken-Hill | Worming 0,20 diagnóstico | 551.688 | 0.32750 | 1729 | 75.35 |
| Broken-Hill | B 20261115, 0,65 | 107.922 | 0.06407 | 1590 | 76.76 |

## Interpretación y límites

Mount Isa y Broken Hill no muestran un exceso significativo a 500 m con ninguna de las tres variantes. En Mount Isa, el worming sellado queda incluso por debajo de la media del nulo. No rechazar el nulo no demuestra ausencia de señal: una referencia incompleta y a escala incompatible puede ocultarla. Aumentar la densidad con umbral 0,20 aumenta mucho la cobertura de fallas, pero no demuestra mejor discriminación.

Pilbara sí presenta exceso nominal a 500 m: worming sellado p = 0,0110, diagnóstico p = 0,0310 y B p = 0,0490. La evidencia del sellado descansa en solo 2,75 km de detecciones y cubre un 1,58 % de las fallas mapeadas. Los intervalos centrales del diagnóstico y de B incluyen cero aunque sus p unilaterales son menores que 0,05: un intervalo central del 95 % corresponde a colas del 2,5 %, mientras la prueba es de una sola cola del 5 %. No son resultados contradictorios.

La tolerancia de 500 m es la principal histórica; 250 y 1.000 m son sensibilidad. Para las seis comparaciones de los dos métodos sellados a 500 m (tres regiones), una corrección Holm al 5 % no rechaza ninguna: el menor p ajustado es 0,0659. El diagnóstico no entra en esa familia y no selecciona un umbral nuevo. Con 1.000 realizaciones, un p alrededor de 0,05 tiene error estándar Monte Carlo aproximado de 0,007; el resultado de B en Pilbara es limítrofe. No se afirma superioridad global ni se elige el mejor resultado entre las 27 filas.

La distribución del nulo conserva la agrupación y organización relativa de la detección antes del recorte, pero rota también sus orientaciones absolutas; no controla anisotropía regional de fallas, posición de contactos ni distribución de litologías. La aceptación del 60 % es un compromiso operativo fijado antes de ejecutar las regiones; no se hizo sensibilidad a otros porcentajes. El recorte puede retirar hasta un 40 % de longitud, y los resultados son condicionales a este criterio. No equivalen a una prueba con el 100 % de geometría dentro del dominio.

La referencia 1:1.000.000 no es verdad de campo. Se necesitan referencias a escala compatible e interpretación independiente para medir capacidad geológica. Las regiones comparten compilación y procesamiento; no son tres réplicas independientes del proceso completo. No se reevaluaron otros modos, QGIS interactivo ni la superioridad sintética de B.

## Texto aplicado a la documentación de validación

Se añadió en docs/VALIDATION_1_3_0.md una sección con el azar por área, la comparación frente al nulo, la longitud limitada de Pilbara y el ajuste por multiplicidad. Los números sostienen matizar la concordancia histórica, sin modificar sus valores ni la conclusión de que B no cumple el criterio combinado de superioridad.

Se añadió esta nota: el umbral calibrado 0,50 del worming es relativo al máximo de la escena. Fue elegido en escenas sintéticas de 128 por 128 celdas; en estas rejillas regionales produce densidades de solo 0,00149 a 0,03955 km/km². El umbral 0,20 es diagnóstico y no sustituye la calibración. Ajustar el umbral o la zona de interés requiere evaluación independiente.

## Verificación y reproducción

Con el Python del proyecto, PYTHONPATH debe señalar src de este clon; el script rechaza cargar MIRAGE desde otra copia. Defina TEMP, TMP y PYTHONPYCACHEPREFIX en la sesión. Ejecute python scripts/evaluate_null_concordance.py CAMPAÑA SALIDA, donde CAMPAÑA es la campaña archivada y SALIDA una carpeta nueva. El script solo lee la campaña y escribe en SALIDA.

Comandos ejecutados y resultados:

- python -m pytest tests/test_null_concordance.py -q -p no:cacheprovider: 4 aprobadas en 1,08 s. Geometría sintética coincidente, no relacionada, área calculable y comportamiento ante vacío o agotamiento de intentos.
- python scripts/evaluate_null_concordance.py CAMPAÑA SALIDA: salida 0, tres regiones, tres variantes, tres tolerancias, 27 filas y nueve archivos de realizaciones completas.
- python -m pytest -q -p no:cacheprovider --junitxml=ARCHIVO: 101 aprobadas, 0 omitidas, 0 fallidas, 33 advertencias, 33,57 s. MIRAGE_BENCHMARK_BANK apuntó al banco existente, por lo que la auditoría optativa verificó particiones y hashes de las 3.000 escenas sin regenerarlas. Advertencias preexistentes de Rasterio/Affine conservadas en el log.
- python -m ruff check src tests mirage_qgis scripts setup.py --no-cache: salida 0, All checks passed.
- Auditoría independiente de salidas: 27 filas y 9.000 realizaciones verificadas contra sus archivos completos; diez hashes de entradas iguales antes y después; las 18 coberturas selladas (tres regiones, dos métodos y tres tolerancias) reproducen la campaña histórica con tolerancia absoluta de 1e-12. No se modificó ninguna entrada.

Las funciones puras están en scripts/evaluate_public.py; el evaluador añade campos al resumen y conserva todos los campos y la lógica de bloqueo anteriores. El script de investigación reutiliza esas funciones. results/results.json contiene las 27 filas y results/metadata.json la identidad de entradas y protocolo. Las geometrías, los 9.000 nulos con sus retenciones, logs y XML de pruebas se entregan fuera del repositorio. No se copiaron rejillas ni pesos al repositorio.
## Sensibilidad completa

| Región | Variante | Tolerancia m | Azar área % | Acierto % | Media nulo % | Exceso pp | Intervalo 95 % pp | p unilateral |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| Pilbara | Worming 0,50 | 250 | 2.84 | 37.59 | 2.22 | +35.37 | [-5.23, +37.59] | 0.0280 |
| Pilbara | Worming 0,50 | 500 | 5.63 | 98.20 | 4.62 | +93.59 | [+17.71, +98.20] | 0.0110 |
| Pilbara | Worming 0,50 | 1000 | 11.11 | 100.00 | 9.92 | +90.08 | [+0.00, +100.00] | 0.0539 |
| Pilbara | Worming 0,20 diagnóstico | 250 | 2.84 | 17.64 | 2.69 | +14.95 | [+1.64, +17.64] | 0.0210 |
| Pilbara | Worming 0,20 diagnóstico | 500 | 5.63 | 28.81 | 5.37 | +23.44 | [-1.95, +28.81] | 0.0310 |
| Pilbara | Worming 0,20 diagnóstico | 1000 | 11.11 | 41.85 | 10.97 | +30.87 | [-14.73, +41.85] | 0.0599 |
| Pilbara | B 20261115, 0,65 | 250 | 2.84 | 13.63 | 3.09 | +10.54 | [-1.65, +13.63] | 0.0370 |
| Pilbara | B 20261115, 0,65 | 500 | 5.63 | 23.60 | 6.22 | +17.38 | [-4.86, +23.60] | 0.0490 |
| Pilbara | B 20261115, 0,65 | 1000 | 11.11 | 42.02 | 12.05 | +29.97 | [-5.39, +42.02] | 0.0390 |
| Mount-Isa | Worming 0,50 | 250 | 15.21 | 3.72 | 15.16 | -11.44 | [-35.40, +3.72] | 0.7662 |
| Mount-Isa | Worming 0,50 | 500 | 28.66 | 11.55 | 28.59 | -17.04 | [-56.90, +11.55] | 0.6983 |
| Mount-Isa | Worming 0,50 | 1000 | 47.29 | 20.25 | 47.36 | -27.11 | [-72.94, +20.25] | 0.7043 |
| Mount-Isa | Worming 0,20 diagnóstico | 250 | 15.21 | 20.98 | 16.14 | +4.83 | [-2.34, +13.05] | 0.1279 |
| Mount-Isa | Worming 0,20 diagnóstico | 500 | 28.66 | 33.71 | 30.43 | +3.28 | [-9.46, +18.15] | 0.3626 |
| Mount-Isa | Worming 0,20 diagnóstico | 1000 | 47.29 | 49.99 | 50.10 | -0.11 | [-19.79, +23.12] | 0.5365 |
| Mount-Isa | B 20261115, 0,65 | 250 | 15.21 | 26.44 | 16.07 | +10.37 | [-0.79, +19.73] | 0.0350 |
| Mount-Isa | B 20261115, 0,65 | 500 | 28.66 | 38.82 | 30.35 | +8.46 | [-10.13, +25.06] | 0.1958 |
| Mount-Isa | B 20261115, 0,65 | 1000 | 47.29 | 47.39 | 49.98 | -2.59 | [-27.50, +24.40] | 0.5634 |
| Broken-Hill | Worming 0,50 | 250 | 16.73 | 18.07 | 17.02 | +1.05 | [-15.31, +13.22] | 0.4086 |
| Broken-Hill | Worming 0,50 | 500 | 31.75 | 39.47 | 32.34 | +7.14 | [-15.29, +27.67] | 0.2617 |
| Broken-Hill | Worming 0,50 | 1000 | 56.37 | 61.77 | 57.65 | +4.13 | [-21.81, +33.16] | 0.4166 |
| Broken-Hill | Worming 0,20 diagnóstico | 250 | 16.73 | 18.33 | 17.29 | +1.04 | [-6.25, +7.93] | 0.3656 |
| Broken-Hill | Worming 0,20 diagnóstico | 500 | 31.75 | 33.66 | 32.64 | +1.03 | [-10.69, +12.88] | 0.4346 |
| Broken-Hill | Worming 0,20 diagnóstico | 1000 | 56.37 | 58.82 | 57.53 | +1.29 | [-13.45, +17.79] | 0.4545 |
| Broken-Hill | B 20261115, 0,65 | 250 | 16.73 | 15.26 | 17.31 | -2.05 | [-11.28, +6.82] | 0.6523 |
| Broken-Hill | B 20261115, 0,65 | 500 | 31.75 | 36.20 | 32.64 | +3.55 | [-10.92, +18.03] | 0.3087 |
| Broken-Hill | B 20261115, 0,65 | 1000 | 56.37 | 57.65 | 57.47 | +0.18 | [-17.57, +19.73] | 0.5085 |
