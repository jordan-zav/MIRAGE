# Enmienda de presupuesto anterior a prueba

Durante el entrenamiento inicial, la validación aún mejora alrededor de la época 90. No se ha ejecutado selección de umbrales ni evaluación sintética o real de prueba. Para cumplir la exigencia de estabilización se amplía el máximo de 150 a 900 épocas por semilla, manteniendo el límite total de tres horas por semilla y la paciencia 15 con mejora relativa 0.001.

Se conserva el entrenamiento inicial. Al continuar cada semilla se parte de su mejor checkpoint de validación, con Adam reiniciado a los mismos hiperparámetros, y se registra explícitamente el reinicio en la trayectoria. No se mezclan pesos de semillas ni se usa prueba para decidir duración. Si una semilla inicial ya cumplió estabilidad, no se continúa. La comparación de selección por BCE usa las trayectorias completas; las métricas y los criterios de superioridad permanecen congelados. Llegar a 900 sin estabilidad se declara insuficiente y no convergido.
