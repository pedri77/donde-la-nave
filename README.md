# ¿Dónde pondrías tu nave?

Todo el suelo industrial y comercial de **Arganda del Rey** (Madrid), medido desde datos abiertos
y publicado en una web sin servidor: cuánto ocupa cada polígono, a qué distancia está de la vía
rápida y del centro, y un ranking **que hace el lector** moviendo tres pesos con la fórmula a la
vista. Episodio `cci-15` de la serie [«Construido con IA»](https://iacedemy.com/free/yt/construido-con-ia/)
de IAcademy; recorte replicable del proyecto *Arganda Business Digital Twin*.

- **Web:** <https://pedri77.github.io/donde-la-nave/>
- **Fuente:** © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) vía Overpass
  API, instantánea del 2026-10-01. Licencia [ODbL 1.0](https://opendatacommons.org/licenses/odbl/).

## Qué sale de los datos

| Métrica | Valor |
|---|---:|
| Término municipal | 79,93 km² |
| Polígonos industriales (`landuse=industrial` / `man_made=works`) | 19 |
| Polígonos comerciales (`landuse=commercial`) | 4 |
| Suelo industrial | **544,96 ha, el 6,82 % del término** |
| Suelo comercial | 4,75 ha |
| Polígonos sin nombre en OSM | 13 de 23 |
| Polígonos que cruzan el límite municipal | 3 (se cuentan enteros, marcados) |

El mayor con diferencia es el **Polígono Industrial El Guija**: 314 ha, a 70 m de la N-IIIa. El
siguiente, un recinto sin nombre de 90 ha. Los demás están entre 0,1 y 45 ha.

## Cómo funciona el ranking

No hay un *business location score* escondido. Tres pesos (superficie, cercanía a vía rápida,
cercanía al centro, de 0 a 10) y una fórmula escrita en la propia página:

```
puntuación = (p_sup · superficie + p_via · cercanía_vía + p_cen · cercanía_centro) / (p_sup + p_via + p_cen)
```

Cada factor va a 0-1 entre el peor y el mejor de los 23 polígonos. La superficie entra en
escala logarítmica para que El Guija no aplaste a los demás. Con los pesos cambia el orden:
superficie a tope gana El Guija; centro a tope gana el Recinto Ferial. El peso del centro está a
cero por defecto porque no es obvio que estar cerca del casco sea bueno para una nave.

## Lo que NO se pudo medir (y se declara)

- **Parcelas y uso catastral: sin dato.** Los servicios INSPIRE del Catastro no responden en
  acceso anónimo (dominio aparcado, WAF «Request Rejected» y un 404, medido el 2026-10-01; evidencia
  en `data/sources.json` y `raw/catastro_wfs_capabilities.xml`). Esta serie no usa claves.
- **Empresas por polígono: no publicable.** OSM tiene 6 puntos de actividad empresarial en todo el
  municipio; no es un censo. `densidad_empresas_fiable: false` en `data/agregados.json`.
- **Tiempo de viaje: no.** La «accesibilidad» es distancia en línea recta del centroide al segmento
  de vía rápida más cercano (A-3, R-3, M-506, N-IIIa) y al nodo `place=town`.

## Reproducirlo, para cualquier municipio

```bash
python3 scripts/osm_fetch.py "Arganda del Rey"   # Overpass -> raw/osm/<municipio>.json (cachea)
python3 scripts/osm_build.py "Arganda del Rey"   # -> data/agregados.json, poligonos.geojson, contexto.geojson
cp data/*.json data/*.geojson site/data/          # la web lee de site/data/
```

Cambiar de municipio es cambiar el nombre. El mapa es un SVG propio (límite, vías rápidas y centro
salen del mismo snapshot), así que la web no depende de teselas ni de ningún proveedor externo.

## Trampas encontradas y cómo se tratan

1. **Recintos que cruzan el límite** (Centro Emisor RNE, way/28341750, Puente de Arganda): Overpass
   devuelve por intersección; se cuentan enteros y se marcan, no se recortan a ojo.
2. **Solapes**: tres recintos comerciales pequeños tienen el centroide dentro de El Guija; el doble
   conteo posible es < 2 ha sobre 550. Declarado.
3. **Umbral de ruido**: se descartan polígonos < 1.000 m² y ways sin anillo cerrado (0 en esta ejecución).
4. **ODbL**: todo derivado de OSM, incluida la puntuación, hereda la licencia y la atribución.

## Verificación

- Término medido 79,93 km² frente a 79,7 km² de las fichas municipales: < 0,4 % de desviación.
- Tres polígonos comprobados contra su ficha pública de OSM (El Guija, Puente de Arganda, Coto Cisneros).
- Método de área validado con un cuadrado de referencia (0,25 % esfera-plano).
- Web probada en Chromium: 23 polígonos dibujados, 213 tramos de vía, pesos que reordenan, 0 errores.

Informe completo de la medición: [`data/informe.md`](data/informe.md).

Código bajo **MIT** (`LICENSE`). Los datos derivados, bajo ODbL.
