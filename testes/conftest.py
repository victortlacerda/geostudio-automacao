"""Fixtures: um .gsz sintético no formato conhecido e um pacote `gsi` falso.

O .gsz sintético segue a estrutura descrita em docs/formato_gsz.md. Quando as amostras reais
da 2026.1 chegarem (docs/amostras_geostudio/), os testes passam a usá-las também.
"""
from __future__ import annotations

import sys
import types
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

XML = """<?xml version="1.0" encoding="utf-8"?>
<GSIData>
  <FileInfo Version="26.1.0" />
  <Geometries Len="1"><Geometry><ID>1</ID><Name>Seção A</Name><MeshId>1</MeshId></Geometry></Geometries>
  <Analyses Len="3">
    <Analysis><ID>1</ID><Name>Percolação</Name><Kind>SEEP/W</Kind><Method>SteadyState</Method><GeometryId>1</GeometryId></Analysis>
    <Analysis><ID>2</ID><Name>Estabilidade/Jusante</Name><Kind>SLOPE/W</Kind><Method>MorgensternPrice</Method><ParentID>1</ParentID><GeometryId>1</GeometryId></Analysis>
    <Analysis><ID>3</ID><Name>Tensões</Name><Kind>SIGMA/W</Kind><Method>InSitu</Method><GeometryId>1</GeometryId></Analysis>
  </Analyses>
  <Materials Len="2">
    <Material><ID>1</ID><Name>Argila</Name><SlopeModel>MohrCoulomb</SlopeModel><SeepModel>SatOnly</SeepModel>
      <StressStrain UnitWeight="18" CohesionPrime="10" PhiPrime="25" /><Hydraulic KSat="1e-08" /></Material>
    <Material><ID>2</ID><Name>Areia</Name><SlopeModel>MohrCoulomb</SlopeModel>
      <StressStrain UnitWeight="19" CohesionPrime="0" PhiPrime="33" /></Material>
  </Materials>
</GSIData>
"""

NODE_CSV = "Node,X,Y,PoreWaterPressure,TotalHead\n1,0,0,50.0,10\n2,10,0,30.5,8\n3,10,5,-2.1,5\n"


@pytest.fixture
def gsz_sintetico(tmp_path):
    caminho = tmp_path / "talude_teste.gsz"
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("talude_teste.xml", XML.encode("utf-8"))
        z.writestr("mesh_1.ply", b"ply\nformat binary_little_endian 1.0\nend_header\n")
        z.writestr("Percolação/000/node.csv", NODE_CSV.encode("utf-8"))
        z.writestr("Estabilidade&3Jusante/000/node.csv", NODE_CSV.encode("utf-8"))
        z.writestr("Estabilidade&3Jusante/000/slip_surface.csv",
                   "Slip,FOS,CenterX,CenterY,Radius\n1,1.512,12,20,15\n2,1.437,13,21,16\n".encode("utf-8"))
    return caminho


class _Enum:
    """Imita um enum protobuf (EnumTypeWrapper): atributos por nome e .Name(numero)."""

    def __init__(self, nome, valores):
        self.__name__ = nome
        self._por_numero = {v: k for k, v in valores.items()}
        for k, v in valores.items():
            setattr(self, k, v)

    def Name(self, numero):
        return self._por_numero[int(numero)]

    def Value(self, nome):
        return getattr(self, nome)


RESULT_TYPE = _Enum("ResultType", {"Nodes": 1000, "Elements": 1002, "Gauss": 1003, "BeamGauss": 1026,
                                   "Slip": 1013, "CriticalSlip": 1014, "Column": 1015,
                                   "LambdaFOS": 1017, "SavedTimeStep": 1106})
DATA_PARAM = _Enum("DataParamType", {"eXCoord": 5, "eYCoord": 6, "eWaterPressure": 40,
                                     "eRawSlipFOS": 700, "eSlipCenterX": 701, "eSlipRadius": 702,
                                     "eBaseNormalStress": 710})
UNIT_CATEGORY = _Enum("UnitCategory", {"Undefined": 0, "Length": 1, "Pressure": 16})

# tabelas que o projeto falso "tem": tabela -> {parâmetro: (nome, unidade, categoria, valores)}
TABELAS_FALSAS = {
    1014: {"eRawSlipFOS": ("Factor of Safety", "", 0, [1.437]),
           "eSlipCenterX": ("Slip surface center X", "m", 1, [13.0]),
           "eSlipRadius": ("Slip surface radius", "m", 1, [16.0])},
    1000: {"eXCoord": ("X", "m", 1, [0.0, 10.0, 10.0]),
           "eWaterPressure": ("Water Pressure", "kPa", 16, [50.0, 30.5, -2.1])},
    1015: {"eBaseNormalStress": ("Total Normal Stress", "kPa", 16, [12.0, 20.0])},
}
INSTANCIA_OBRIGATORIA = {1015}


class _Projeto:
    def __init__(self, caminho):
        self.caminho = caminho
        self.valores = {}
        self.resolvidas = []
        self.carregadas = []
        self.com_resultados = {"Percolação", "Estabilidade/Jusante"}
        self.falha_solve = None
        self.ignorar_gravacao = False
        self.fechado = False

    def Get(self, req):
        from google.protobuf import json_format, struct_pb2
        chave = (req["analysis"], req["object"])
        if chave not in self.valores:
            raise KeyError(f"objeto desconhecido: {req['object']}")
        return types.SimpleNamespace(data=json_format.ParseDict(self.valores[chave], struct_pb2.Value()))

    def Set(self, req):
        from google.protobuf.json_format import MessageToDict
        if not self.ignorar_gravacao:
            self.valores[(req["analysis"], req["object"])] = MessageToDict(req["data"])
        return types.SimpleNamespace()

    def SolveAnalyses(self, req):
        self.resolvidas += req["analyses"]
        ok = self.falha_solve is None
        status = {n: types.SimpleNamespace(succeeded=ok, error_message=self.falha_solve or "")
                  for n in req["analyses"]}
        return types.SimpleNamespace(all_succeeded=ok, completion_status=status)

    def QueryResultsAvailability(self, req):
        return types.SimpleNamespace(has_results=req["analysis"] in self.com_resultados)

    def LoadResults(self, req):
        self.carregadas.append(req["analysis"])
        return types.SimpleNamespace()

    def _tabela(self, req):
        t = int(req["table"])
        if t not in TABELAS_FALSAS:
            raise ValueError("tabela sem dados nesta análise")
        if t in INSTANCIA_OBRIGATORIA and req.get("instance") is None:
            raise ValueError("instance obrigatório nesta tabela")
        return TABELAS_FALSAS[t]

    def QueryTableParamsInfo(self, req):
        info = [types.SimpleNamespace(dataparam=DATA_PARAM.Value(p), key=p, display=d[0], units=d[1],
                                      unit_category=d[2]) for p, d in self._tabela(req).items()]
        return types.SimpleNamespace(params_info=info)

    def QueryResults(self, req):
        tab = self._tabela(req)
        res = {int(dp): types.SimpleNamespace(values=list(tab[DATA_PARAM.Name(dp)][3]))
               for dp in req["dataparams"] if DATA_PARAM.Name(dp) in tab}
        return types.SimpleNamespace(results=res)

    def Close(self):
        self.fechado = True


@pytest.fixture
def gsi_falso(monkeypatch):
    from google.protobuf import struct_pb2
    mod = types.ModuleType("gsi")
    mod.__version__ = "0.0-teste"
    mod.ultimo = {}
    mod.versao_alvo = None

    def OpenProject(caminho):
        """Abre um projeto (falso)."""
        mod.ultimo["projeto"] = _Projeto(caminho)
        return mod.ultimo["projeto"]

    def set_target_version(v):
        mod.versao_alvo = v

    mod.OpenProject = OpenProject
    mod.set_target_version = set_target_version
    mod.Value = struct_pb2.Value
    mod.Point = lambda **kw: kw
    mod.ResultType = RESULT_TYPE
    mod.DataParamType = DATA_PARAM
    mod.UnitCategory = UNIT_CATEGORY
    for nome in ("GetRequest", "SetRequest", "SolveAnalysesRequest", "LoadResultsRequest",
                 "QueryResultsRequest", "QueryTableParamsInfoRequest", "QueryResultsAvailabilityRequest",
                 "QueryResultsAtCoordinatesRequest"):
        setattr(mod, nome, lambda **kw: kw)
    monkeypatch.setitem(sys.modules, "gsi", mod)
    return mod
