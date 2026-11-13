"""Leitura do modelo (XML dentro do .gsz) para o inventário e a auditoria. Só biblioteca padrão.

Confirmado com docs/amostras_geostudio/slope/s00_talude5m.gsz (GeoStudio 2026.1):
- FileInfo: FileVersion, AppVersion, RevNumber, Date, Time
- Coordinates/EngCoords: UnitSystem (Metric)
- Geometries/Geometry: Name, Points/Point (ID, X, Y), Regions/Region (ID, PointIDs)
- Contexts/Context: AnalysisID + GeometryUsesMaterials/GeometryUsesMaterial (ID="Regions-<n>", Entry=<id material>)
- Materials/Material: ID, Name, Color "RGB=(r,g,b)", SlopeModel, StressStrain com FILHOS
  (UnitWeight, CohesionPrime, PhiPrime...); filhos com Missing="true" ficam de fora
- StabilityItems/StabilityItem: AnalysisID + Entry/SlipSurface (busca) e Entry/LambdaSettings
- WaterItems/WaterItem: AnalysisID + Entry/UnitWaterWeight
O que não estiver na amostra (linhas piezométricas, cargas, reforços) é lido de forma genérica: a
auditoria lista as seções do XML e quantos itens cada uma tem, sem interpretar.
"""
from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


def _float(txt):
    try:
        return float(str(txt).strip())
    except (TypeError, ValueError):
        return None


def cor_rgb(txt, padrao="#dddddd"):
    """'RGB=(255,255,128)' -> '#ffff80'."""
    m = re.search(r"\((\d+),\s*(\d+),\s*(\d+)\)", txt or "")
    return "#{:02x}{:02x}{:02x}".format(*(int(g) for g in m.groups())) if m else padrao


def area_poligono(xy):
    """Área (fórmula do laço) de uma lista de (x, y); sempre positiva."""
    s = 0.0
    for (x1, y1), (x2, y2) in zip(xy, xy[1:] + xy[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


@dataclass
class Regiao:
    id: str
    pontos: list                       # ids dos pontos, na ordem
    xy: list                           # coordenadas (x, y)
    area: float


@dataclass
class MaterialModelo:
    id: str
    nome: str
    cor: str
    modelo_slope: str = ""
    modelo_seep: str = ""
    modelo_sigma: str = ""
    parametros: dict = field(default_factory=dict)   # StressStrain: atributos + filhos numéricos
    hidraulico: dict = field(default_factory=dict)


@dataclass
class Modelo:
    info: dict
    unidades: str
    pontos: dict                       # {id: (x, y)} da 1ª geometria
    regioes: list                      # [Regiao]
    materiais: dict                    # {id: MaterialModelo}
    regiao_material: dict              # {id análise: {id região: id material}}
    busca: dict                        # {id análise: dict com a busca de superfícies}
    agua: dict                         # {id análise: dict (peso da água...)}
    secoes: dict                       # {tag: nº de itens} de todas as seções do XML
    raiz: object = None                # ElementTree, para consultas extras

    def material_da_regiao(self, analise_id, regiao_id):
        mid = self.regiao_material.get(str(analise_id), {}).get(str(regiao_id))
        return self.materiais.get(mid) if mid else None

    @property
    def extensao(self):
        if not self.pontos:
            return None
        xs = [p[0] for p in self.pontos.values()]
        ys = [p[1] for p in self.pontos.values()]
        return min(xs), max(xs), min(ys), max(ys)


def _valores(el):
    """Atributos + filhos simples de um elemento, numéricos quando der; ignora Missing="true"."""
    if el is None:
        return {}
    d = {}
    for f in el:
        if len(f) or f.get("Missing") == "true":
            continue
        txt = (f.text or "").strip()
        if txt:
            v = _float(txt)
            d[f.tag] = v if v is not None else txt
    for k, v in el.attrib.items():
        fv = _float(v)
        d[k] = fv if fv is not None else v
    return d


def _busca(ss):
    cfg = {}
    if ss is None:
        return cfg
    cfg["criticas_guardadas"] = int(_float(ss.findtext("NumberOfCriticalSlipsToKeep")) or 1)
    cfg["direcao"] = (ss.findtext("DirectionOfSlip") or "").strip()
    cfg["volume_minimo"] = _float(ss.findtext("MinimumVolume"))
    ee = ss.find("EntryExit")
    if ee is not None:
        def pt(tag):
            el = ee.find(tag)
            if el is None or _float(el.get("X")) is None:
                return None
            return (_float(el.get("X")), _float(el.get("Y")))
        cfg["entrada"] = (pt("LeftSideLeftPt"), pt("LeftSideRightPt"))
        cfg["saida"] = (pt("RightSideLeftPt"), pt("RightSideRightPt"))
        cfg["incrementos"] = (int(_float(ee.findtext("LeftInc")) or 0), int(_float(ee.findtext("RightInc")) or 0))
    g = ss.find("Grid")
    if g is not None:
        cfg["grelha"] = {k: v for k, v in g.attrib.items() if v != ""}
    lim = ss.find("Limit")
    if lim is not None:
        cfg["limites"] = {k: _float(v) for k, v in lim.attrib.items() if _float(v) is not None}
    return cfg


def ler_modelo(caminho_ou_arquivo) -> Modelo:
    """Lê o XML do .gsz (caminho ou ArquivoGSZ)."""
    caminho = getattr(caminho_ou_arquivo, "caminho", caminho_ou_arquivo)
    with zipfile.ZipFile(caminho) as z:
        nome_xml = getattr(caminho_ou_arquivo, "xml_principal", None)
        if not nome_xml:
            nomes = [n for n in z.namelist() if n.lower().endswith(".xml") and "/" not in n]
            nome_xml = nomes[0]
        raiz = ET.fromstring(z.read(nome_xml))

    info = dict(raiz.find("FileInfo").attrib) if raiz.find("FileInfo") is not None else {}
    eng = raiz.find("Coordinates/EngCoords")
    unidades = eng.get("UnitSystem", "") if eng is not None else ""

    pontos, regioes = {}, []
    geo = raiz.find("Geometries/Geometry")
    if geo is not None:
        pts = geo.find("Points")
        for p in (pts if pts is not None else []):
            if _float(p.get("X")) is not None:
                pontos[p.get("ID")] = (_float(p.get("X")), _float(p.get("Y")))
        regs = geo.find("Regions")
        for i, r in enumerate(regs if regs is not None else [], start=1):
            ids = [x.strip() for x in (r.findtext("PointIDs") or "").split(",") if x.strip()]
            xy = [pontos[i_] for i_ in ids if i_ in pontos]
            regioes.append(Regiao(id=(r.findtext("ID") or str(i)).strip(), pontos=ids, xy=xy,
                                  area=area_poligono(xy) if len(xy) >= 3 else 0.0))

    materiais = {}
    for m in raiz.iterfind("Materials/Material"):
        mid = (m.findtext("ID") or "").strip()
        materiais[mid] = MaterialModelo(
            id=mid, nome=(m.findtext("Name") or "").strip(), cor=cor_rgb(m.findtext("Color")),
            modelo_slope=(m.findtext("SlopeModel") or "").strip(),
            modelo_seep=(m.findtext("SeepModel") or "").strip(),
            modelo_sigma=(m.findtext("StressModel") or "").strip(),
            parametros=_valores(m.find("StressStrain")), hidraulico=_valores(m.find("Hydraulic")))

    regiao_material = {}
    for c in raiz.iterfind("Contexts/Context"):
        aid = (c.findtext("AnalysisID") or "").strip()
        mapa = {}
        for g in c.iterfind("GeometryUsesMaterials/GeometryUsesMaterial"):
            m = re.match(r"Regions-(\d+)", g.get("ID", ""))
            if m:
                mapa[m.group(1)] = g.get("Entry")
        regiao_material[aid] = mapa

    busca = {}
    for s in raiz.iterfind("StabilityItems/StabilityItem"):
        aid = (s.findtext("AnalysisID") or "").strip()
        cfg = _busca(s.find("Entry/SlipSurface"))
        lam = [_float(x.text) for x in s.iterfind("Entry/LambdaSettings/LambdaValues/*")]
        if lam:
            cfg["lambdas"] = [x for x in lam if x is not None]
        busca[aid] = cfg

    agua = {}
    for w in raiz.iterfind("WaterItems/WaterItem"):
        agua[(w.findtext("AnalysisID") or "").strip()] = _valores(w.find("Entry"))

    secoes = {el.tag: (int(el.get("Len")) if el.get("Len", "").isdigit() else len(el)) for el in raiz}
    return Modelo(info=info, unidades=unidades, pontos=pontos, regioes=regioes, materiais=materiais,
                  regiao_material=regiao_material, busca=busca, agua=agua, secoes=secoes, raiz=raiz)
