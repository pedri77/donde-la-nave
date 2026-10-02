# Informe de medición — «¿Dónde pondrías tu nave?» (Arganda del Rey)

Municipio piloto: **Arganda del Rey** (Madrid). Todo lo medido sale de un único
snapshot de OpenStreetMap (Overpass API, 2026-10-01) y se puede reejecutar con
`python3 scripts/osm_fetch.py "Arganda del Rey" && python3 scripts/osm_build.py "Arganda del Rey"`.
Cambio de municipio = mismo comando con otro nombre.

## Qué se midió

| Métrica | Valor | Fuente |
|---|---|---|
| Término municipal | 79,93 km² | OSM relación 341635 (anillos exteriores) |
| Polígonos industriales (landuse=industrial / man_made=works) | 19 | OSM |
| Polígonos comerciales (landuse=commercial) | 4 | OSM |
| Suelo industrial total | 544,96 ha (6,82 % del término) | suma de los 19 polígonos |
| Suelo comercial total | 4,75 ha (0,06 %) | suma de los 4 polígonos |
| POIs de empresa en todo el municipio | **6** nodos | OSM (office/craft/man_made=works/industrial) |
| Polígonos con nombre propio | 10 de 23 | OSM |

Comparación de control del término: 79,93 km² medidos aquí frente a los
~79,7 km² publicados (fuente catastral/IGN habitual para fichas municipales):
desviación < 0,4 %, coherente con dos generalizaciones distintas del mismo
límite. No se usa como dato del episodio, solo como sanity check del método.

## Los polígonos, uno a uno

Superficie (ha), distancia del centroide a la vía rápida más cercana
(motorway/trunk: A-3, R-3, N-IIIa) y al nodo del núcleo urbano
(place=town de OSM):

| Polígono | Uso | ha | Vía rápida | km a vía | km a centro |
|---|---|---|---|---|---|
| Polígono Industrial El Guijar (relation/16125038) | ind | 314,07 | N-IIIa | 0,07 | 2,91 |
| way/1191938484 (sin nombre) | ind | 90,20 | N-IIIa | 1,08 | 3,03 |
| Centro Emisor Onda Corta RNE (way/344600814) | ind | 44,71 | A-3 | 0,53 | 6,06 |
| way/1234484928 (sin nombre) | ind | 26,00 | N-IIIa | 0,27 | 3,46 |
| Centros de control Hispasat (way/35983696) | ind | 16,63 | A-3 | 1,13 | 5,99 |
| Planta de Asfalto Asfalpasa (way/1328634876) | ind | 10,24 | A-3 | 1,20 | 5,64 |
| way/35817391 | ind | 7,60 | M-506 | 0,28 | 4,46 |
| way/1328634875 | ind | 6,52 | A-3 | 0,65 | 4,86 |
| way/28341750 | ind | 5,64 | N-IIIa | 1,09 | 4,21 |
| Polígono Industrial Puente de Arganda (way/30111153) | ind | 4,88 | A-3 | 0,09 | 6,69 |
| Polígono Industrial Coto Cisneros (way/28345683) | ind | 3,82 | M-506 | 1,63 | 5,93 |
| Telepuerto Internacional de Arganda (way/351737611) | ind | 3,77 | R-3 | 1,17 | 5,74 |
| Recinto Ferial Arganda del Rey (way/272527072) | com | 3,35 | N-IIIa | 0,13 | 0,61 |
| Tricalsa (way/1278936483) | ind | 2,93 | N-IIIa | 0,16 | 4,17 |
| Emisora de Onda Corta (way/1328634832) | ind | 2,76 | A-3 | 1,39 | 6,13 |
| way/35817399 | ind | 2,56 | A-3 | 0,39 | 4,09 |
| way/32673026 | ind | 1,47 | R-3 | 1,23 | 2,74 |
| way/632161017 | com | 0,96 | N-IIIa | 0,08 | 3,71 |
| way/394119559 | ind | 0,72 | A-3 | 0,13 | 4,78 |
| way/376392665 | ind | 0,29 | A-3 | 2,71 | 5,71 |
| way/632161021 | com | 0,26 | N-IIIa | 0,03 | 3,88 |
| way/553325774 | ind | 0,13 | R-3 | 1,72 | 3,90 |
| way/632161019 | com | 0,16 | N-IIIa | 0,02 | 3,81 |

Nota honesta sobre la «accesibilidad»: es la distancia en línea recta del
centroide del polígono al segmento de vía rápida más cercano, y al nodo
place=town. No es tiempo de viaje, no es calidad del suelo, no es una
puntuación. Un polígono grande no es «mejor» que uno pequeño. El lector decide.

## Empresas por polígono: NO PUBLICABLE

En todo el término municipal OSM tiene **6 nodos** de empresa/actividad
(office, craft, man_made=works, industrial). 4 caen dentro de algún polígono
(3 en El Guijar, 1 en way/1191938484). Con 6 POIs no existe dato fiable de
densidad de empresas: OSM no es un censo de empresas, es lo que la comunidad
ha mapeado. Se declara `densidad_empresas_fiable: false` en
`data/agregados.json` y no se publica ninguna cifra de empresas por polígono.
La fuente real serían el Directorio Central de Empresas (INE) o licencias
municipales: ninguna abierta a nivel de polígono.

## Parcelas por polígono: SIN DATO

El Catastro (única fuente de parcelas y usos del suelo) se descartó por
inviable en anónimo, con evidencia del intento (2026-10-01):

- `https://www1.sedecatastro.es/INSPIRE/wfsCP.ashx?request=GetCapabilities&service=WFS`
  → HTTP 200 pero con una página de *domain parking* (no hay servicio).
- `https://ovc.catastro.meh.es/INSPIRE/wfsCP.ashx?...` → HTTP 200 «Request
  Rejected» (WAF, support ID 10498739829322842722).
- `https://www.catastro.hacienda.gob.es/INSPIRE/wfsCP.ashx?...` → 404.
- ATOM de Madrid (`.../INSPIRE/atom/adri/atom_adri_madrid.xml`) → mismo
  parking de dominio.

Por tanto no hay número de parcelas por polígono ni uso catastral, y no se
estima. Para reactivarlo haría falta la vía oficial vigente de acceso
programático al Catastro (actualmente orientada a sesión iniciada / servicios
de pago por consulta masiva), algo fuera de las reglas de esta serie (sin
claves).

## Trampas detectadas y cómo se tratan

1. **Polígonos que cruzan el límite municipal (3):** way/344600814 (Centro
   Emisor RNE), way/28341750 y way/30111153 (Puente de Arganda). Overpass
   devuelve por intersección, así que su superficie va completa en la suma
   (no se recorta: no hay clip real implementado y se prefiere declararlo).
   Están marcados con `cruza_limite: true` en el GeoJSON.
2. **Solapamientos / doble conteo (3 pares):** way/632161017, way/632161019 y
   way/632161021 (tres polígonos comerciales junto a la N-IIIa) tienen su
   centroide dentro de El Guijar\. La suma total puede contarlos dos veces;
   orden de magnitud del solape: < 2 ha sobre 550 ha.
3. **Sin duplicados OSM↔Catastro que resolver:** al no haber dato catastral,
   el cruce no existe; se declara en vez de presuponerlo.
4. **Parcelas sin uso declarado:** aplicaría al Catastro; sin esa fuente, la
   métrica equivalente es «polígono sin nombre en OSM»: 13 de 23.
5. **Licencias (ODbL):** el GeoJSON y los agregados son derivados de OSM.
   Publicación obligada bajo ODbL con atribución «© OpenStreetMap
   contributors». El término «% de suelo industrial» hereda esa licencia.
6. **Umbral de ruido:** se descartan polígonos < 1.000 m² y ways sin anillo
   cerrado. En esta ejecución: 0 descartados.

## Verificación manual

Tres polígonos comprobados contra la ficha pública de OSM (mismo origen, pero
comprobación visual de que la geometría y las etiquetas son las que dicen ser):

- **Polígono Industrial El Guijar** — https://www.openstreetmap.org/relation/16125038
  OSM lo etiqueta «El Guija» (errata): el nombre oficial es **El Guijar**; el build lo corrige y guarda el original en `nombre_osm`.
  Etiquetado landuse=industrial con nombre; ocupa la vega al noreste del
  casco, entre la N-IIIa y el ferrocarril. Coincide con la zona industrial
  conocida de El Guijar; en el mapa base de OSM se ve el recinto completo.
- **Polígono Industrial Puente de Arganda** — https://www.openstreetmap.org/way/30111153
  Recinto pequeño pegado a la A-3 al sureste del casco (0,09 km del centroide
  a la autovía, coherente con un polígono que bordea la carretera); es uno de
  los que cruzan el límite municipal.
- **Polígono Industrial Coto Cisneros** — https://www.openstreetmap.org/way/28345683
  Zona industrial al suroeste, junto a la M-506; la distancia medida a vía
  rápida (1,63 km, M-506) es la mayor de los polígonos con nombre, coherente
  con su posición en el borde del término.

Chequeo aritmético adicional: el método de área se validó con un cuadrado de
0,01°×0,01° a latitud 40° (951.300 m² esféricos vs 948.900 m² planares,
0,25 % de diferencia esperable entre esfera y plano).

## Ficheros

- `data/agregados.json` — cifras con `meta` por campo (fuente, periodo, URL, unidad, método).
- `data/poligonos.geojson` — 23 polígonos con propiedades (área, distancias, cruce de límite, POIs dentro). ~21 KB, publicable en la web.
- `data/sources.json` — fuentes, licencias (ODbL, condiciones Catastro e IGN) y por qué se descartaron.
- `raw/osm/arganda_del_rey.json` — respuesta Overpass cruda cacheada (no se versiona).
