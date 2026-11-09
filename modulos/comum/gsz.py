"""Leitura de arquivos .gsz do GeoStudio, sem abrir o programa.

O .gsz é um ZIP. Estrutura conhecida (pelo código aberto do PyGeoStudio, usado só como consulta)
e a conferir com as amostras da sua instalação (docs/formato_gsz.md):

    <nome>.xml                         modelo: FileInfo, Geometries, Analyses, Contexts, Materials,
                                       Reinforcements, Functions, DataSets
    mesh_<id>.ply                      malha (binário)
    <Análise>/<NNN>/node.csv           resultados nodais por passo salvo (000 = permanente)
    <Análise>/<NNN>/*.csv              demais tabelas de resultado (superfícies, fatias, elementos...)

No nome da pasta de resultados, '/' do nome da análise vira '&3'.
Somente biblioteca padrão do Python.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Analise:
    id: str
    nome: str
    tipo: str = ""           # Kind: SLOPE/W, SEEP/W, SIGMA/W...
    metodo: str = ""         # Method: SteadyState, Transient, MorgensternPrice...
    pai_id: str = ""         # ParentID (vazio = análise raiz)
    geometria_id: str = ""
    descricao: str = ""
    campos: dict = field(default_factory=dict)   # todos os filhos simples do XML, como texto


@dataclass
class Material:
    id: str
    nome: str
    modelo_slope: str = ""
    modelo_seep: str = ""
    modelo_sigma: str = ""
    resistencia: dict = field(default_factory=dict)  # atributos de <StressStrain>
    hidraulico: dict = field(default_factory=dict)   # atributos de <Hydraulic>


def numero(txt):
    """Converte texto em float quando dá; devolve o texto original caso contrário."""
    if txt is None:
        return None
    t = str(txt).strip()
    try:
        return float(t)
    except ValueError:
        return t


def pasta_resultados(nome_analise: str) -> str:
    return nome_analise.replace("/", "&3")


class ArquivoGSZ:
    """Abre um .gsz para leitura. Uso:  g = ArquivoGSZ("talude.gsz"); g.analises; g.ler_nos(a)."""

    def __init__(self, caminho):
        self.caminho = Path(caminho)
        if not self.caminho.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.caminho}")
        try:
            with zipfile.ZipFile(self.caminho) as z:
                self.membros = z.namelist()
                self.xml_principal = self._achar_xml(self.membros)
                raiz = ET.fromstring(z.read(self.xml_principal))
        except zipfile.BadZipFile as exc:
            raise ValueError(f"{self.caminho.name} não é um .gsz válido (não abre como ZIP).") from exc
        self.secoes = [el.tag for el in raiz]
        self.info = dict(raiz.find("FileInfo").attrib) if raiz.find("FileInfo") is not None else {}
        self.analises = [self._ler_analise(el) for el in self._itens(raiz, "Analyses")]
        self.materiais = [self._ler_material(el) for el in self._itens(raiz, "Materials")]

    # ------------------------------------------------------------------ XML
    def _achar_xml(self, membros):
        esperado = self.caminho.stem + ".xml"
        if esperado in membros:
            return esperado
        na_raiz = [m for m in membros if m.lower().endswith(".xml") and "/" not in m]
        if not na_raiz:
            raise ValueError(f"{self.caminho.name}: nenhum XML de modelo dentro do arquivo.")
        return na_raiz[0]

    @staticmethod
    def _itens(raiz, secao):
        el = raiz.find(secao)
        return list(el) if el is not None else []

    @staticmethod
    def _filhos_texto(el):
        return {f.tag: (f.text or "").strip() for f in el if len(f) == 0 and not f.attrib}

    def _ler_analise(self, el):
        c = self._filhos_texto(el)
        return Analise(
            id=c.get("ID", ""), nome=c.get("Name", ""), tipo=c.get("Kind", ""),
            metodo=c.get("Method", ""), pai_id=c.get("ParentID", ""),
            geometria_id=c.get("GeometryId", ""), descricao=c.get("Description", ""), campos=c,
        )

    def _ler_material(self, el):
        c = self._filhos_texto(el)
        ss, hid = el.find("StressStrain"), el.find("Hydraulic")
        return Material(
            id=c.get("ID", ""), nome=c.get("Name", ""), modelo_slope=c.get("SlopeModel", ""),
            modelo_seep=c.get("SeepModel", ""), modelo_sigma=c.get("StressModel", ""),
            resistencia=dict(ss.attrib) if ss is not None else {},
            hidraulico=dict(hid.attrib) if hid is not None else {},
        )

    # ------------------------------------------------------------ análises
    def analise(self, nome_ou_id):
        for a in self.analises:
            if nome_ou_id in (a.nome, a.id):
                return a
        nomes = ", ".join(a.nome for a in self.analises) or "(nenhuma)"
        raise KeyError(f"Análise '{nome_ou_id}' não existe. Análises do arquivo: {nomes}")

    def filhas(self, analise):
        return [a for a in self.analises if a.pai_id and a.pai_id == analise.id]

    def arvore(self):
        """Lista (nível, análise) em ordem de árvore: cada análise seguida das filhas."""
        ids = {a.id for a in self.analises}
        saida = []

        def visitar(a, nivel):
            saida.append((nivel, a))
            for f in self.filhas(a):
                visitar(f, nivel + 1)

        for a in self.analises:
            if not a.pai_id or a.pai_id not in ids:
                visitar(a, 0)
        return saida

    # ---------------------------------------------------------- resultados
    def arquivos_resultado(self, analise):
        prefixo = pasta_resultados(analise.nome) + "/"
        return [m for m in self.membros if m.startswith(prefixo) and not m.endswith("/")]

    def passos(self, analise):
        """Pastas de passo salvas ('000', '001', ...), em ordem."""
        prefixo = re.escape(pasta_resultados(analise.nome))
        achados = {m.group(1) for m in (re.match(rf"^{prefixo}/(\d+)/", n) for n in self.membros) if m}
        return sorted(achados, key=int)

    def tem_resultados(self, analise):
        return bool(self.arquivos_resultado(analise))

    def ler_csv(self, membro):
        """Devolve (cabeçalho, linhas); linhas são dicionários com números já convertidos."""
        with zipfile.ZipFile(self.caminho) as z:
            bruto = z.read(membro)
        for cod in ("utf-8-sig", "latin-1"):
            try:
                texto = bruto.decode(cod)
                break
            except UnicodeDecodeError:
                continue
        leitor = csv.reader(io.StringIO(texto))
        linhas = [l for l in leitor if any(c.strip() for c in l)]
        if not linhas:
            return [], []
        cab = [c.strip() for c in linhas[0]]
        dados = [{k: numero(v) for k, v in zip(cab, l)} for l in linhas[1:]]
        return cab, dados

    def ler_nos(self, analise, passo=None):
        """Resultados nodais (node.csv) de um passo; sem passo = o último salvo."""
        passos = self.passos(analise)
        if not passos:
            raise LookupError(f"A análise '{analise.nome}' não tem resultados no arquivo. Resolva antes.")
        passo = passos[-1] if passo is None else f"{int(passo):03d}"
        membro = f"{pasta_resultados(analise.nome)}/{passo}/node.csv"
        if membro not in self.membros:
            raise LookupError(f"'{membro}' não existe. Arquivos do passo: "
                              + ", ".join(m.rsplit('/', 1)[-1] for m in self.arquivos_resultado(analise)
                                          if f"/{passo}/" in m))
        return self.ler_csv(membro)

    # --------------------------------------------------------------- resumo
    def resumo(self):
        return {
            "arquivo": self.caminho.name,
            "xml": self.xml_principal,
            "versao": self.info.get("Version", ""),
            "secoes_xml": self.secoes,
            "analises": [
                {"nivel": n, "id": a.id, "nome": a.nome, "tipo": a.tipo, "metodo": a.metodo,
                 "pai_id": a.pai_id, "passos_salvos": self.passos(a)}
                for n, a in self.arvore()
            ],
            "materiais": [
                {"id": m.id, "nome": m.nome, "slope": m.modelo_slope, "seep": m.modelo_seep,
                 "sigma": m.modelo_sigma, "resistencia": m.resistencia}
                for m in self.materiais
            ],
            "malhas": [m for m in self.membros if m.lower().endswith(".ply")],
        }
