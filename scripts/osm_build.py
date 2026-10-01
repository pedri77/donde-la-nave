#!/usr/bin/env python3
"""Construye los agregados del observatorio «¿Dónde pondrías tu nave?».

Lee raw/osm/{municipio}.json (Overpass, ver osm_fetch.py para la consulta
exacta) y produce en data/:
  - agregados.json   : cifras del episodio con bloque meta por campo
  - poligonos.geojson: polígonos de suelo industrial/comercial (para el mapa)
  - informe.md       : números medidos, trampas y verificación manual

Método (todo en Python puro, sin dependencias):
  - Superficies: área esférica de anillos lon/lat (fórmula del exceso
    esférico, la misma que usa Turf.js). Coordenadas WGS84 de OSM.
  - Término municipal: anillos exteriores (role=outer) de la relación
    administrativa OSM, cosidos por extremos compartidos.
  - Cruce de límite: se marca todo polígono con algún vértice FUERA del
    término (Overpass devuelve por intersección, no por inclusión).
  - Solapamientos: pares de polígonos donde el centroide de uno cae dentro
    del otro -> riesgo de doble conteo; se informa, no se "corrige".

  - Accesibilidad: distancia del centroide de cada polígono al segmento más
    cercano de vía rápida (motorway|trunk) usando proyección local
    equirectangular; y distancia al nodo place=town del núcleo urbano.
    Es DISTANCIA medida, no una puntuación de calidad.
  - Empresas por polígono: solo se cuenta si hay POIs suficientes; con
    menos de 50 POIs en el municipio se declara "no fiable" y no se publica
    densidad por polígono.
"""
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "raw" / "osm"
DATA = REPO / "data"

R_TIERRA = 6371008.8  # radio medio WGS84 (m)

META_OSM = {
    "source": "OpenStreetMap via Overpass API (overpass-api.de/api/interpreter)",
    "url": "https://overpass-api.de/api/interpreter",
    "license": "ODbL 1.0 (Open Data Commons Open Database License)",
    "attribution": "© OpenStreetMap contributors",
}


def pt(p):
    """Normaliza un punto Overpass {'lat','lon'} a (lon, lat)."""
    return (p["lon"], p["lat"]) if isinstance(p, dict) else (p[0], p[1])

# ---------- geometría ----------
def anillo_area_m2(ring):
    """Área esférica de un anillo lon/lat cerrado.

    Integral de Green sobre la esfera: A = R²·|Σ (λ2−λ1)·(2+sen φ1+sen φ2)| / 2
    con ángulos en radianes (fórmula trapezoidal estándar; error < 0,1 % a
    escala municipal).
    """
    if ring[0] != ring[-1]:
        ring = ring + [ring[0]]
    total = 0.0
    for i in range(len(ring) - 1):
        l1, f1 = math.radians(ring[i][0]), math.radians(ring[i][1])
        l2, f2 = math.radians(ring[i + 1][0]), math.radians(ring[i + 1][1])
        total += (l2 - l1) * (2 + math.sin(f1) + math.sin(f2))
    return abs(total) * R_TIERRA * R_TIERRA / 2


def centroide(ring):
    lon = sum(p[0] for p in ring) / len(ring)
    lat = sum(p[1] for p in ring) / len(ring)
    return (lon, lat)


def punto_en_anillo(pt, ring):
    """Ray casting sobre lon/lat (válido a escala municipal)."""
    x, y = pt
    dentro = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y):
            xint = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < xint:
                dentro = not dentro
        j = i
    return dentro


def punto_en_poligonos(pt, anillos):
    return any(punto_en_anillo(pt, r) for r in anillos)


def dist_m(a, b):
    """Distancia local equirectangular centrada en a (m)."""
    lat0 = math.radians(a[1])
    dx = (b[0] - a[0]) * math.cos(lat0)
    dy = (b[1] - a[1])
    return math.hypot(dx, dy) * (math.pi / 180) * R_TIERRA


def dist_punto_segmento_m(p, s1, s2):
    """Proyecta p sobre el segmento s1-s2 en métrica local alrededor de p."""
    def loc(q):  # (m este, m norte) relativo a p
        return ((q[0] - p[0]) * math.cos(math.radians(p[1])),
                (q[1] - p[1])) 
    x1, y1 = loc(s1)
    x2, y2 = loc(s2)
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        d = math.hypot(x1, y1)
    else:
        t = max(0.0, min(1.0, (-(x1 * dx + y1 * dy)) / L2))
        d = math.hypot(x1 + t * dx, y1 + t * dy)
    return d * (math.pi / 180) * R_TIERRA


# ---------- ensamblado de relaciones ----------
def coser_anillos(tramos):
    """Une tramos lon/lat en anillos cerrados por extremos compartidos."""
    tramos = [list(t) for t in tramos]
    anillos = []
    while tramos:
        anillo = tramos.pop(0)
        cambiado = True
        while cambiado and anillo[0] != anillo[-1]:
            cambiado = False
            for i, t in enumerate(tramos):
                if t[0] == anillo[-1]:
                    anillo += t[1:]
                elif t[-1] == anillo[-1]:
                    anillo += list(reversed(t))[1:]
                elif t[-1] == anillo[0]:
                    anillo = t + anillo[1:]
                elif t[0] == anillo[0]:
                    anillo = list(reversed(t)) + anillo[1:]
                else:
                    continue
                tramos.pop(i)
                cambiado = True
        if anillo[0] == anillo[-1]:
            anillos.append(anillo)
        # tramos que no cierran se descartan y se cuentan
    return anillos


def anillos_relation(rel):
    tramos = [[pt(q) for q in m["geometry"]] for m in rel.get("members", [])
              if m.get("type") == "way" and m.get("role") == "outer" and m.get("geometry")]
    return coser_anillos(tramos)


def main(nombre: str) -> None:
    clave = nombre.lower().replace(" ", "_")
    datos = json.loads((RAW / f"{clave}.json").read_text())
    els = datos["elements"]

    # límite municipal
    rels_lim = [e for e in els if e["type"] == "relation"
                and e.get("tags", {}).get("boundary") == "administrative"
                and e.get("tags", {}).get("admin_level") == "8"]
    if not rels_lim:
        raise SystemExit("no se encontró la relación del límite municipal")
    anillos_municipio = []
    for r in rels_lim:
        anillos_municipio += anillos_relation(r)
    area_municipio = sum(anillo_area_m2(a) for a in anillos_municipio)

    # núcleo urbano (nodo place=town/city con el nombre del municipio)
    centros = [e for e in els if e["type"] == "node"
               and e.get("tags", {}).get("place") in ("town", "city")]
    centro = (centros[0]["lon"], centros[0]["lat"]) if centros else None

    # vías rápidas: motorway + trunk con geometría
    vias = []  # (ref, [segmentos])
    for e in els:
        if e["type"] == "way" and e.get("tags", {}).get("highway") in ("motorway", "trunk"):
            g = [pt(q) for q in e.get("geometry", [])]
            if g and len(g) >= 2:
                vias.append((e["tags"].get("ref") or e["tags"].get("name") or "?", g))

    # POIs de empresa/actividad (nodos)
    pois = [e for e in els if e["type"] == "node" and e.get("tags")]

    # polígonos de suelo
    poligonos = []
    descartados = []
    for e in els:
        tg = e.get("tags", {})
        uso = tg.get("landuse") or ("industrial" if tg.get("man_made") == "works" else None)
        if uso not in ("industrial", "commercial"):
            continue
        pid = f"{e['type']}/{e['id']}"
        if e["type"] == "way":
            g = [pt(q) for q in e.get("geometry", [])]
            anillos = [g] if g and g[0] == g[-1] else []
        else:
            anillos = anillos_relation(e)
        if not anillos:
            descartados.append({"id": pid, "motivo": "sin anillo cerrado (way abierto o relación no ensamblable)"})
            continue
        area = sum(anillo_area_m2(a) for a in anillos)
        if area < 1000:  # < 0,1 ha: ruido de mapeo
            descartados.append({"id": pid, "motivo": f"área {area:.0f} m² < 1.000 m² (umbral de ruido)"})
            continue
        cen = centroide(max(anillos, key=anillo_area_m2))
        fuera = sum(1 for a in anillos for p in a if not punto_en_poligonos(p, anillos_municipio))
        # accesibilidad
        d_via, ref_via = None, None
        if vias:
            mejor = None
            for ref, g in vias:
                for i in range(len(g) - 1):
                    d = dist_punto_segmento_m(cen, g[i], g[i + 1])
                    if mejor is None or d < mejor[0]:
                        mejor = (d, ref)
            d_via, ref_via = mejor
        d_centro = dist_m(cen, centro) if centro else None
        dentro_pois = sum(1 for p in pois
                          if punto_en_poligonos((p["lon"], p["lat"]), anillos))
        poligonos.append({
            "id": pid,
            "nombre": tg.get("name"),
            "uso": uso,
            "area_m2": round(area, 1),
            "vertices_fuera_termino": fuera,
            "cruza_limite": fuera > 0,
            "dist_via_rapida_m": round(d_via, 1) if d_via is not None else None,
            "via_rapida": ref_via,
            "dist_centro_urbano_m": round(d_centro, 1) if d_centro is not None else None,
            "pois_dentro": dentro_pois,
            "anillos": anillos,
        })

    # solapamientos (centroide de uno dentro de otro) -> riesgo doble conteo
    solapados = []
    for i, a in enumerate(poligonos):
        ca = centroide(max(a["anillos"], key=anillo_area_m2))
        for j, b in enumerate(poligonos):
            if j <= i:
                continue
            cb = centroide(max(b["anillos"], key=anillo_area_m2))
            if punto_en_poligonos(ca, b["anillos"]) or punto_en_poligonos(cb, a["anillos"]):
                solapados.append([a["id"], b["id"]])

    area_ind = sum(p["area_m2"] for p in poligonos if p["uso"] == "industrial")
    area_com = sum(p["area_m2"] for p in poligonos if p["uso"] == "commercial")
    pct = lambda a: round(100 * a / area_municipio, 2)

    hoy = "2026-10-01"
    agg = {
        "meta": {
            "generado": hoy,
            "municipio": nombre,
            "source": META_OSM["source"],
            "url": META_OSM["url"],
            "license": META_OSM["license"],
            "attribution": META_OSM["attribution"],
            "period": f"snapshot OSM {datos.get('osm3s', {}).get('timestamp_osm_base', 'desconocido')}",
            "notas": [
                "Catastro INSPIRE (WFS/ATOM) descartado: los endpoints públicos "
                "(www1.sedecatastro.es y ovc.catastro.meh.es) no responden en modo anónimo "
                "(dominio aparcado y rechazo WAF «Request Rejected», medido 2026-10-01); "
                "catastro.hacienda.gob.es/INSPIRE devuelve 404. Sin credenciales no hay vía estable.",
                "Límites municipales: tomados de la relación administrativa de OSM, no del CNIG/IGN "
                "(los servicios IGN actuales requieren clave de API gratuita, api.ign.es).",
                "Overpass devuelve los elementos que INTERSECTAN el área: los polígonos que cruzan "
                "el límite aparecen completos; se marcan en cruce_limite y su superficie no se recorta.",
                "Los POIs de empresa de OSM NO son un censo de empresas: son lo mapeado por la comunidad.",
            ],
        },
        "termino_municipal_m2": {
            "valor": round(area_municipio, 1),
            "meta": {**{k: META_OSM[k] for k in ("source", "url", "license")},
                     "period": "snapshot OSM", "unit": "m²",
                     "metodo": "suma de anillos exteriores (role=outer) de la relación admin_level=8, área esférica"},
        },
        "poligonos_industriales": {
            "valor": sum(1 for p in poligonos if p["uso"] == "industrial"),
            "meta": {**{k: META_OSM[k] for k in ("source", "url", "license")},
                     "period": "snapshot OSM", "unit": "count",
                     "criterio": "landuse=industrial o man_made=works en OSM, anillo cerrado, área ≥ 1.000 m²"},
        },
        "poligonos_comerciales": {
            "valor": sum(1 for p in poligonos if p["uso"] == "commercial"),
            "meta": {**{k: META_OSM[k] for k in ("source", "url", "license")},
                     "period": "snapshot OSM", "unit": "count",
                     "criterio": "landuse=commercial en OSM, anillo cerrado, área ≥ 1.000 m²"},
        },
        "suelo_industrial_m2": {"valor": round(area_ind, 1),
                                "meta": {**{k: META_OSM[k] for k in ("source", "url", "license")},
                                         "period": "snapshot OSM", "unit": "m²",
                                         "nota": "suma sin recorte al término; ver cruce_limite"}},
        "suelo_comercial_m2": {"valor": round(area_com, 1),
                               "meta": {**{k: META_OSM[k] for k in ("source", "url", "license")},
                                        "period": "snapshot OSM", "unit": "m²"}},
        "pct_suelo_industrial": {"valor": pct(area_ind),
                                 "meta": {**{k: META_OSM[k] for k in ("source", "url", "license")},
                                          "period": "snapshot OSM", "unit": "% del término",
                                          "formula": "suelo_industrial_m2 / termino_municipal_m2"}},
        "pct_suelo_comercial": {"valor": pct(area_com),
                                "meta": {**{k: META_OSM[k] for k in ("source", "url", "license")},
                                         "period": "snapshot OSM", "unit": "% del término"}},
        "pois_empresa_municipio": {"valor": len(pois),
                                   "meta": {**{k: META_OSM[k] for k in ("source", "url", "license")},
                                            "period": "snapshot OSM", "unit": "count",
                                            "criterio": "nodos con man_made=works, office, industrial o craft"}},
        "densidad_empresas_fiable": {
            "valor": False,
            "meta": {"source": "criterio editorial", "url": "-", "license": "-",
                     "umbral": "≥ 50 POIs de empresa en el municipio",
                     "razon": (f"hay {len(pois)} POIs: OSM no es censo de empresas; "
                               "no se publica 'empresas por polígono'")} },
        "poligonos_que_cruzan_limite": {
            "valor": sum(1 for p in poligonos if p["cruza_limite"]),
            "meta": {**{k: META_OSM[k] for k in ("source", "url", "license")},
                     "period": "snapshot OSM", "unit": "count",
                     "metodo": "vértices fuera del anillo municipal"}},
        "pares_solapados": {
            "valor": len(solapados),
            "meta": {**{k: META_OSM[k] for k in ("source", "url", "license")},
                     "period": "snapshot OSM", "unit": "count",
                     "metodo": "centroide de uno dentro del otro; riesgo de doble conteo en la suma",
                     "detalle": solapados}},
        "descartados": {
            "valor": len(descartados),
            "meta": {"source": "proceso de construcción", "url": "-", "license": "-",
                     "unit": "count", "detalle": descartados}},
    }

    DATA.mkdir(exist_ok=True)
    (DATA / "agregados.json").write_text(json.dumps(agg, ensure_ascii=False, indent=2))

    # GeoJSON sin los anillos internos
    feats = []
    for p in sorted(poligonos, key=lambda x: -x["area_m2"]):
        coords = [ring for ring in p["anillos"]]
        props = {k: v for k, v in p.items() if k not in ("anillos",)}
        feats.append({"type": "Feature",
                      "geometry": {"type": "Polygon", "coordinates": coords},
                      "properties": props})
    geo = {"type": "FeatureCollection",
           "metadata": {"generado": hoy, "municipio": nombre, **META_OSM},
           "features": feats}
    (DATA / "poligonos.geojson").write_text(json.dumps(geo, ensure_ascii=False))

    # Contexto para el mapa: límite municipal, vías rápidas y centro urbano. Mismo origen (OSM),
    # para que la web no dependa de un servidor de teselas ni de un proveedor externo.
    ctx = [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [a]},
            "properties": {"tipo": "limite", "nombre": nombre}} for a in anillos_municipio]
    ctx += [{"type": "Feature", "geometry": {"type": "LineString", "coordinates": g},
             "properties": {"tipo": "via", "ref": ref}} for ref, g in vias]
    if centro:
        ctx.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": list(centro)},
                    "properties": {"tipo": "centro", "nombre": nombre}})
    (DATA / "contexto.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "metadata": {"generado": hoy, "municipio": nombre, **META_OSM},
         "features": ctx}, ensure_ascii=False))

    # resumen por consola para el informe
    print(json.dumps({k: v["valor"] for k, v in agg.items() if isinstance(v, dict) and "valor" in v},
                     ensure_ascii=False, indent=2))
    for p in sorted(poligonos, key=lambda x: -x["area_m2"]):
        print(f"{p['id']:>14} {p['uso'][:4]} {p['area_m2']/1e4:9.2f} ha "
              f"{'CRUZA' if p['cruza_limite'] else '     '} "
              f"via={p['dist_via_rapida_m'] and round(p['dist_via_rapida_m']/1000, 2)}km({p['via_rapida']}) "
              f"centro={p['dist_centro_urbano_m'] and round(p['dist_centro_urbano_m']/1000, 2)}km "
              f"pois={p['pois_dentro']} {p['nombre'] or ''}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Arganda del Rey")
