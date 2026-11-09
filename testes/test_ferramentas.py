import json

import pytest

from ferramentas import diagnostico_gsi, inspecionar_gsz, mapa_objetos, procurar_instalacao
from modulos.comum.api import Projeto, achatar, tentar


# ----------------------------------------------------------- inspecionar_gsz
def test_inspecionar_grava_txt_e_json(gsz_sintetico):
    assert inspecionar_gsz.main([str(gsz_sintetico)]) == 0
    txt = gsz_sintetico.with_name("talude_teste_inspecao.txt").read_text(encoding="utf-8")
    assert "[2] Estabilidade/Jusante" in txt and "sem resultados" in txt
    assert "colunas: Slip, FOS, CenterX, CenterY, Radius" in txt
    dados = json.loads(gsz_sintetico.with_name("talude_teste_inspecao.json").read_text(encoding="utf-8"))
    assert dados["arquivos_resultado"]["Estabilidade&3Jusante/000/slip_surface.csv"]["linhas"] == 2
    assert dados["malhas"] == ["mesh_1.ply"]


def test_inspecionar_pasta(gsz_sintetico):
    assert inspecionar_gsz.main([str(gsz_sintetico.parent)]) == 0


# ----------------------------------------------------------- diagnostico_gsi
def test_diagnostico_descreve_funcoes_e_mensagens(gsi_falso):
    from google.protobuf import struct_pb2
    gsi_falso.Value = struct_pb2.Value          # uma mensagem protobuf de verdade
    info = diagnostico_gsi.diagnosticar(gsi_falso)
    assert info["versao"] == "0.0-teste"
    assert info["nomes"]["OpenProject"]["tipo"] == "função"
    assert info["nomes"]["OpenProject"]["doc"] == "Abre um projeto (falso)."
    campos = {c["nome"] for c in info["nomes"]["Value"]["campos"]}
    assert {"number_value", "string_value", "struct_value"} <= campos
    assert "OpenProject" in diagnostico_gsi.texto(info)


def test_diagnostico_sem_gsi_avisa(monkeypatch, capsys):
    import builtins
    original = builtins.__import__

    def sem_gsi(nome, *a, **k):
        if nome == "gsi":
            raise ImportError
        return original(nome, *a, **k)

    monkeypatch.setattr(builtins, "__import__", sem_gsi)
    assert diagnostico_gsi.main() == 1
    assert "não está instalado" in capsys.readouterr().out


# ------------------------------------------------------- procurar_instalacao
def test_procurar_acha_wheel_exemplo_e_geocmd(tmp_path, monkeypatch, capsys):
    base = tmp_path / "Seequent" / "GeoStudio 2026.1"
    (base / "API" / "Examples").mkdir(parents=True)
    (base / "Bin").mkdir()
    (base / "API" / "gsi-26.1.0-py3-none-any.whl").write_bytes(b"")
    (base / "API" / "Examples" / "exemplo_slope.py").write_text("print()")
    (base / "Bin" / "GeoCmd.exe").write_bytes(b"")
    monkeypatch.setattr(procurar_instalacao, "raizes_padrao", lambda: [])
    monkeypatch.setattr(procurar_instalacao, "SAIDA", tmp_path / "saida.txt")
    assert procurar_instalacao.main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "gsi-26.1.0-py3-none-any.whl" in out and "pip install" in out
    assert "exemplo_slope.py" in out and "GeoCmd.exe" in out


# ----------------------------------------------------------------- api.py
def test_achatar_valor_com_unidade():
    arvore = {"Materials": [{"Name": "Argila", "CohesionPrime": {"Value": 10.0, "Units": "kPa"}}]}
    assert achatar(arvore, "Obj") == [
        ("Obj.Materials[0].Name", "Argila", ""),
        ("Obj.Materials[0].CohesionPrime", 10.0, "kPa"),
    ]


def test_tentar_usa_alternativa_e_relata_falhas():
    assert tentar("x", lambda: 1 / 0, lambda: 7) == 7
    with pytest.raises(RuntimeError, match="alt 2: KeyError"):
        tentar("y", lambda: 1 / 0, lambda: {}["k"])


def test_gravar_confere_lendo_de_volta(gsi_falso, gsz_sintetico):
    obj = 'CurrentAnalysis.Objects.Materials["Argila"].Slope.CohesionPrime'
    with Projeto(gsz_sintetico) as p:
        assert p.gravar("Estabilidade/Jusante", obj, 12.5, "kPa")
        assert p.ler("Estabilidade/Jusante", obj) == {"Value": 12.5, "Units": "kPa"}
        p.resolver("Estabilidade/Jusante")
    assert gsi_falso.ultimo["projeto"].resolvidas == ["Estabilidade/Jusante"]
    assert gsi_falso.ultimo["projeto"].fechado


def test_gravacao_sem_efeito_e_detectada(gsi_falso, gsz_sintetico):
    obj = "CurrentAnalysis.Objects.X"
    with Projeto(gsz_sintetico) as p:
        p.p.valores[("A", obj)] = {"Value": 1.0, "Units": ""}
        p.p.ignorar_gravacao = True
        with pytest.raises(RuntimeError, match="não teve efeito"):
            p.gravar("A", obj, 2.0, "")


# ------------------------------------------------------------ mapa_objetos
def test_mapa_objetos_grava_csv_e_registra_falhas(gsi_falso, gsz_sintetico, monkeypatch):
    def abrir(caminho):
        from conftest import _Projeto
        proj = _Projeto(caminho)
        proj.valores[("Percolação", "CurrentAnalysis.Objects")] = {
            "Materials": [{"Name": "Argila", "KSat": {"Value": 1e-8, "Units": "m/s"}}]}
        gsi_falso.ultimo["projeto"] = proj
        return proj

    monkeypatch.setattr(gsi_falso, "OpenProject", abrir)
    assert mapa_objetos.main([str(gsz_sintetico), "--analise", "Percolação"]) == 0
    csv = gsz_sintetico.with_name("talude_teste_mapa_objetos.csv").read_text(encoding="utf-8-sig")
    assert "Percolação;CurrentAnalysis.Objects.Materials[0].KSat;1e-08;m/s" in csv
    log = gsz_sintetico.with_name("talude_teste_mapa_objetos_log.txt").read_text(encoding="utf-8")
    assert "Percolação · CurrentAnalysis:" in log
