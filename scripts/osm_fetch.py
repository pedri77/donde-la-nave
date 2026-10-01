#!/usr/bin/env python3
"""Descarga de OpenStreetMap (Overpass API) los datos del municipio.

Sin claves: Overpass API pública (overpass-api.de), licencia ODbL.
Consulta exacta (plantilla, con {NOMBRE} = nombre municipal):

  [out:json][timeout:120];
  area["boundary"="administrative"]["admin_level"="8"]["name"="{NOMBRE}"]->.a;
  // 1) límite municipal (relación)
  rel(area.a)["boundary"="administrative"]["admin_level"="8"]["name"="{NOMBRE}"];
  out ids tags geom;

Cada respuesta se cachea en raw/osm/{clave}.json; reejecutar no re-descarga.
Nota trampa: Overpass "area" recorta por intersección, no por inclusión —
un polígono que toca el límite aparece entero; se detecta en el build.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "raw" / "osm"
OVERPASS = "https://overpass-api.de/api/interpreter"
UA = {"User-Agent": "donde-la-nave/1.0 (episodio ¿dónde pondrías tu nave?)"}

QUERY = """[out:json][timeout:180];
rel["boundary"="administrative"]["admin_level"="8"]["name"="{n}"];
out geom;
area["boundary"="administrative"]["admin_level"="8"]["name"="{n}"]->.a;
(
  way["landuse"~"^(industrial|commercial)$"](area.a);
  way["man_made"="works"](area.a);
  rel["landuse"~"^(industrial|commercial)$"](area.a);
  rel["man_made"="works"](area.a);
);
out geom;
(
  node["man_made"="works"](area.a);
  node["office"](area.a);
  node["industrial"](area.a);
  node["craft"](area.a);
  node["landuse"~"^(industrial|commercial)$"](area.a);
);
out tags center;
way["highway"~"^(motorway|trunk|primary)$"](area.a);
out geom;
node["place"~"^(town|city)$"]["name"~"{n}"](area.a);
out tags center;
"""


def fetch(nombre: str) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    clave = nombre.lower().replace(" ", "_")
    destino = RAW / f"{clave}.json"
    if destino.exists():
        print(f"cache OK: {destino}")
        return
    q = QUERY.format(n=nombre)
    body = urllib.parse.urlencode({"data": q}).encode()
    req = urllib.request.Request(OVERPASS, data=body, headers=UA)
    for intento in range(4):
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                datos = json.load(r)
            destino.write_text(json.dumps(datos, ensure_ascii=False))
            print(f"descargado: {destino} ({destino.stat().st_size} bytes, "
                  f"{len(datos.get('elements', []))} elementos)")
            return
        except Exception as e:  # 429/504 de Overpass: reintentar
            print(f"intento {intento + 1} fallido: {e}", file=sys.stderr)
            time.sleep(20 * (intento + 1))
    raise SystemExit("Overpass agotó los reintentos")


if __name__ == "__main__":
    fetch(sys.argv[1] if len(sys.argv) > 1 else "Arganda del Rey")
