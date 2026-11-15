# Corrección de wavelets y crestas

Se localizaron dos defectos de procesamiento, sin cambiar coordenadas de mapa ni escalar resultados para acercarlos a la verdad del banco.

1. PyWavelets CWT extiende con ceros fuera de los ejes. Un campo potencial con nivel base distinto de cero adquiere una discontinuidad artificial en los cuatro bordes. Su amplitud domina la normalización de cada escala y suprime contactos interiores. Se aplica reflexión de ocho escalas a cada lado, se retira el nivel medio y se recorta la magnitud antes de normalizar.
2. La supresión no máxima orientada por Hessiano no exigía curvatura negativa. Las zonas convexas podían producir líneas paralelas fuera de la cresta porque la comparación se hacía en una dirección localmente plana. Ahora se exige autovalor mínimo negativo. Afecta las rutas nuevas THDR/worming/wavelets; no altera el núcleo numérico v1.2.

La prueba de regresión usa un contacto tanh norte-sur en 128 por 128, píxel 50 m y escalas 50/100/200 m, con niveles base 0 y 10000. Exige mapa de fuerza invariante y distancia mediana a la traza de hasta dos celdas. Falló tras corregir solo la extensión (tres celdas) y pasó con la condición de curvatura. Las pruebas de la API existentes pasan. Esto demuestra el defecto y su corrección en ese contrato, no garantiza reducir el error medio de 32 celdas en todos los campos. Esa conclusión depende del banco nuevo y se informará por separado.
