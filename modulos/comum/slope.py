"""Resultados do SLOPE/W lidos direto do .gsz resolvido (sem abrir o GeoStudio, sem a API).

Formato confirmado com docs/amostras_geostudio/slope/s00_talude5m.gsz (GeoStudio 2026.1, licença
de estudante, FS conferido na interface = 1,786):

    <Análise>/001/slip_surface.csv        todas as superfícies testadas (uma linha por superfície)
        SlipNum, SlipFOS, SlipCenterX, SlipCenterY, SlipRadiusX, SlipVolume, SlipWeight,
        ResistingForceX, ActivatingForceX, ResistingMomentX, ActivatingMomentX, LambdaX ...
        SlipFOS >= 900 = superfície inválida (código de erro do solver, ex.: 996, 998)
    <Análise>/001/column_<n>.csv          fatias das N superfícies críticas guardadas
    <Análise>/001/intercolumn_<n>.csv     forças entre fatias
    <Análise>/001/lambdafos_<n>.csv       FS por força e por momento para cada lambda testado
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .gsz import ArquivoGSZ, pasta_resultados

CODIGO_INVALIDO = 900.0

# Nome do método no XML -> nome usual (confirmado na 2026.1, licença de estudante: o menu tem
# Morgenstern-Price, Spencer, Bishop, Janbu e Fellenius; Fellenius é gravado como "Ordinary")
METODOS = {"Ordinary": "Fellenius (Ordinário)", "Morgenstern-Price": "Morgenstern-Price"}
RIGOROSOS = ("morgenstern", "spencer", "gle", "sarma")     # equilíbrio de forças e momentos


def nome_metodo(metodo):
    return METODOS.get(metodo, metodo or "")


def tem_curva_lambda(sup):
    """Só os métodos rigorosos varrem λ; nos simplificados a curva FS x λ não tem sentido."""
    return len({d["LambdaX"] for d in sup.lambda_fs}) > 1   # SlipFOS a partir deste valor é código de erro, não FS

# significado dos códigos mais comuns (manual do SLOPE/W); os demais aparecem como "código N"
CODIGOS = {
    996: "superfície fora da geometria ou sem fatias válidas",
    997: "superfície fora dos limites",
    998: "volume ou profundidade abaixo do mínimo",
    999: "não convergiu",
}


def _num(v):
    return v if isinstance(v, float) else None


@dataclass
class Superficie:
    numero: int
    fs: float | None
    centro_x: float | None
    centro_y: float | None
    raio: float | None
    volume: float | None
    peso: float | None
    lambda_: float | None
    codigo: int | None = None          # código de erro quando inválida
    fatias: list = field(default_factory=list)
    entre_fatias: list = field(default_factory=list)
    lambda_fs: list = field(default_factory=list)

    @property
    def valida(self):
        return self.codigo is None

    def base(self):
        """Pontos (x, y) da base da superfície, da esquerda para a direita, a partir das fatias."""
        pts = []
        for f in sorted(self.fatias, key=lambda f: f["XLeft"]):
            if not pts:
                pts.append((f["XLeft"], f["YBackBotLeft"]))
            pts.append((f["XRight"], f["YBackBotRight"]))
        return pts

    def entrada_saida(self):
        b = self.base()
        return (b[0], b[-1]) if b else (None, None)


@dataclass
class ResultadoSlope:
    analise: str
    metodo: str
    superficies: list               # todas, na ordem do arquivo
    configuracao: dict              # entrada/saída, limites, direção, nº de críticas guardadas

    @property
    def validas(self):
        return sorted((s for s in self.superficies if s.valida), key=lambda s: s.fs)

    @property
    def critica(self):
        v = self.validas
        return v[0] if v else None

    def invalidas_por_codigo(self):
        cont = {}
        for s in self.superficies:
            if not s.valida:
                cont[s.codigo] = cont.get(s.codigo, 0) + 1
        return dict(sorted(cont.items()))

    def com_detalhe(self):
        """Superfícies que têm fatias gravadas no arquivo (as críticas guardadas), por FS."""
        return sorted((s for s in self.superficies if s.fatias), key=lambda s: s.fs)


# ----------------------------------------------------------------------- leitura
def _config_estabilidade(xml, analise_id):
    """Lê do XML do modelo a busca de superfícies da análise (entrada e saída, limites, direção)."""
    import xml.etree.ElementTree as ET
    raiz = ET.fromstring(xml)
    cfg = {}
    for item in raiz.iter("StabilityItem"):
        if (item.findtext("AnalysisID") or "").strip() != str(analise_id):
            continue
        ss = item.find("Entry/SlipSurface")
        if ss is None:
            continue
        cfg["criticas_guardadas"] = int(ss.findtext("NumberOfCriticalSlipsToKeep") or 1)
        cfg["direcao"] = (ss.findtext("DirectionOfSlip") or "").strip()
        ee = ss.find("EntryExit")
        if ee is not None:
            def pt(tag):
                el = ee.find(tag)
                return (float(el.get("X")), float(el.get("Y"))) if el is not None and el.get("X") else None
            cfg["entrada"] = (pt("LeftSideLeftPt"), pt("LeftSideRightPt"))
            cfg["saida"] = (pt("RightSideLeftPt"), pt("RightSideRightPt"))
        lim = ss.find("Limit")
        if lim is not None:
            cfg["limites"] = {k: float(v) for k, v in lim.attrib.items() if v not in ("", None)}
    return cfg


def geometria(arquivo: ArquivoGSZ, geometria_id="1"):
    """Pontos {id: (x, y)} e regiões [[ids...]] da geometria."""
    import xml.etree.ElementTree as ET
    import zipfile
    with zipfile.ZipFile(arquivo.caminho) as z:
        raiz = ET.fromstring(z.read(arquivo.xml_principal))
    for i, geo in enumerate(raiz.iter("Geometry"), start=1):
        gid = (geo.findtext("ID") or str(i)).strip()
        if gid != str(geometria_id) and not (geometria_id == "1" and i == 1):
            continue
        pontos = {p.get("ID"): (float(p.get("X")), float(p.get("Y"))) for p in geo.iter("Point")
                  if p.get("X") is not None}
        regioes = [[x.strip() for x in (r.findtext("PointIDs") or "").split(",") if x.strip()]
                   for r in geo.iter("Region")]
        return pontos, regioes
    return {}, []


def ler_resultados(arquivo: ArquivoGSZ, analise) -> ResultadoSlope:
    """Resultados de uma análise SLOPE/W resolvida (nome, id ou objeto Analise)."""
    a = analise if hasattr(analise, "nome") else arquivo.analise(analise)
    if "SLOPE" not in (a.tipo or "").upper():
        raise ValueError(f"'{a.nome}' é uma análise {a.tipo}, não SLOPE/W.")
    passos = arquivo.passos(a)
    if not passos:
        raise LookupError(f"A análise '{a.nome}' não tem resultados no arquivo. Resolva e salve antes.")
    base = f"{pasta_resultados(a.nome)}/{passos[-1]}/"
    membro = base + "slip_surface.csv"
    if membro not in arquivo.membros:
        raise LookupError(f"'{membro}' não existe no arquivo.")

    _, linhas = arquivo.ler_csv(membro)
    superficies = []
    for r in linhas:
        fs = _num(r.get("SlipFOS"))
        codigo = int(fs) if fs is not None and fs >= CODIGO_INVALIDO else None
        superficies.append(Superficie(
            numero=int(r["SlipNum"]), fs=None if codigo else fs,
            centro_x=_num(r.get("SlipCenterX")), centro_y=_num(r.get("SlipCenterY")),
            raio=_num(r.get("SlipRadiusX")), volume=_num(r.get("SlipVolume")),
            peso=_num(r.get("SlipWeight")), lambda_=_num(r.get("LambdaX")), codigo=codigo))

    por_numero = {s.numero: s for s in superficies}
    for m in arquivo.membros:
        if not m.startswith(base) or not m.endswith(".csv"):
            continue
        achado = re.match(r"(column|intercolumn|lambdafos)_(\d+)\.csv$", m[len(base):])
        if not achado or int(achado.group(2)) not in por_numero:
            continue
        s = por_numero[int(achado.group(2))]
        _, dados = arquivo.ler_csv(m)
        tipo = achado.group(1)
        if tipo == "column":
            s.fatias = sorted(dados, key=lambda f: f["XLeft"])
        elif tipo == "intercolumn":
            s.entre_fatias = sorted(dados, key=lambda f: f["XZCoord"])
        else:
            # Bishop e Janbu gravam só uma das colunas (a outra vem vazia); Fellenius grava o arquivo vazio
            for d in dados:
                for k in ("FOSByForce", "FOSByMoment"):
                    d[k] = _num(d.get(k))
            s.lambda_fs = sorted(dados, key=lambda f: f["LambdaX"])

    import zipfile
    with zipfile.ZipFile(arquivo.caminho) as z:
        cfg = _config_estabilidade(z.read(arquivo.xml_principal), a.id)
    return ResultadoSlope(analise=a.nome, metodo=a.metodo, superficies=superficies, configuracao=cfg)


# ---------------------------------------------------------------------- checagens
def checagens(res: ResultadoSlope, fs_alvo=1.5, tolerancia=1e-6):
    """Avisos no estilo do slide2-automacao. Devolve lista de (nível, mensagem)."""
    avisos = []
    c = res.critica
    if c is None:
        return [("ERRO", "Nenhuma superfície válida. Reveja a busca (entrada e saída, direção do movimento).")]
    if c.fs < fs_alvo:
        avisos.append(("ATENÇÃO", f"FS crítico {c.fs:.3f} abaixo do alvo {fs_alvo:.2f}."))
    n_inv = sum(res.invalidas_por_codigo().values())
    if n_inv and n_inv / len(res.superficies) > 0.5:
        avisos.append(("AVISO", f"{n_inv} de {len(res.superficies)} superfícies inválidas "
                                f"({', '.join(f'{k}: {v}' for k, v in res.invalidas_por_codigo().items())})."))
    entrada, saida = c.entrada_saida()
    cfg = res.configuracao
    for nome, pt, faixa in (("faixa esquerda", entrada, cfg.get("entrada")),
                            ("faixa direita", saida, cfg.get("saida"))):
        if pt is None or not faixa or None in faixa:
            continue
        xs = sorted(p[0] for p in faixa)
        # a superfície crítica pode entrar pela face do talude (ponto da faixa projetado no terreno)
        perto = [x for x in xs if abs(pt[0] - x) <= max(0.02 * (xs[1] - xs[0]), tolerancia)]
        if perto:
            avisos.append(("AVISO", f"A superfície crítica toca a borda da {nome} de entrada e saída "
                                    f"(x = {pt[0]:.2f}; faixa [{xs[0]:.2f}; {xs[1]:.2f}]): amplie a faixa."))
    ult = c.lambda_fs[-1] if c.lambda_fs else {}
    if ult.get("FOSByForce") is not None and ult.get("FOSByMoment") is not None:
        dif = abs(ult["FOSByForce"] - ult["FOSByMoment"])
        if dif > 0.01:
            avisos.append(("AVISO", f"FS por força e por momento diferem {dif:.3f} na última iteração de lambda."))
    return avisos
