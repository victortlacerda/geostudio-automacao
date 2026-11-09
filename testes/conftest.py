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


class _Projeto:
    def __init__(self, caminho):
        self.caminho = caminho
        self.valores = {}
        self.resolvidas = []
        self.fechado = False

    def Get(self, req):
        chave = (req["analysis"], req["object"])
        if chave not in self.valores:
            raise KeyError(f"objeto desconhecido: {req['object']}")
        return {"data": self.valores[chave]}

    def Set(self, req):
        from google.protobuf.json_format import MessageToDict
        dado = MessageToDict(req["data"])
        if getattr(self, "ignorar_gravacao", False):
            return
        self.valores[(req["analysis"], req["object"])] = dado

    def SolveAnalyses(self, req):
        self.resolvidas += req["analyses"]

    def Close(self):
        self.fechado = True


@pytest.fixture
def gsi_falso(monkeypatch):
    mod = types.ModuleType("gsi")
    mod.__version__ = "0.0-teste"
    mod.ultimo = {}

    def OpenProject(caminho):
        """Abre um projeto (falso)."""
        mod.ultimo["projeto"] = _Projeto(caminho)
        return mod.ultimo["projeto"]

    mod.OpenProject = OpenProject
    mod.GetRequest = lambda **kw: kw
    mod.SetRequest = lambda **kw: kw
    mod.SolveAnalysesRequest = lambda **kw: kw
    monkeypatch.setitem(sys.modules, "gsi", mod)
    return mod
