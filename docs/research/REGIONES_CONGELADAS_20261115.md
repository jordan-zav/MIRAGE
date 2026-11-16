# Regiones públicas fijadas antes de evaluar

Se utilizan tres regiones australianas separadas, tomadas del mismo producto aeromagnético nacional RTP 2019/2020 y de fallas GA 1:1M. La selección responde a cobertura continental y disponibilidad por API, sin ejecutar métodos ni inspeccionar concordancia.

| Región | Oeste | Sur | Este | Norte | CRS métrico |
| --- | ---: | ---: | ---: | ---: | --- |
| Pilbara | 117.4 | -22.4 | 117.8 | -22.0 | EPSG:32750 |
| Mount Isa | 139.3 | -20.9 | 139.7 | -20.5 | EPSG:32754 |
| Broken Hill | 141.2 | -32.1 | 141.6 | -31.7 | EPSG:32754 |

Recorte NCSS sin reducción de resolución; reproyección métrica aproximada a 100 m. Si supera 512 celdas se usa ventana central de 512, fijada geométricamente. Fallas se recortan a la ventana observada. Cada región es una unidad y no se presenta como tres organismos independientes. Los metadatos y términos de ambas fuentes se conservan antes del uso. Los parámetros de detección seguirán la selección sintética congelada. Esta precisión de disponibilidad no modifica métricas ni reglas del protocolo.
