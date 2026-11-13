import json

import pytest

from ferramentas import diagnostico_gsi, inspecionar_gsz, mapa_objetos, procurar_instalacao, tabelas_resultados
from modulos.comum.api import Projeto, achatar, tentar, valor_numerico

MAT = 'Materials["Argila"].UnitWeight'


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
    (base / "API" / "gsi-1.0-py3-none-any.whl").write_bytes(b"")
    (base / "API" / "Examples" / "exemplo_slope.py").write_text("print()")
    (base / "Bin" / "GeoCmd.exe").write_bytes(b"")
    monkeypatch.setattr(procurar_instalacao, "raizes_padrao", lambda: [])
    monkeypatch.setattr(procurar_instalacao, "SAIDA", tmp_path / "saida.txt")
    assert procurar_instalacao.main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "gsi-1.0-py3-none-any.whl" in out and "pip install" in out
    assert "exemplo_slope.py" in out and "GeoCmd.exe" in out


# ------------------------------------------------------------ api: utilidades
def test_achatar_usa_indice_a_partir_de_1():
    arvore = {"Regions": [{"Material": "Argila", "Area": {"Value": 10.0, "Units": "m²"}}]}
    assert achatar(arvore, "CurrentAnalysis.GeometryItems") == [
        ("CurrentAnalysis.GeometryItems.Regions[1].Material", "Argila", ""),
        ("CurrentAnalysis.GeometryItems.Regions[1].Area", 10.0, "m²"),
    ]


def test_valor_numerico():
    assert valor_numerico(18.0) == 18.0
    assert valor_numerico({"Value": 3, "Units": "kPa"}) == 3.0
    assert valor_numerico("MohrCoulomb") is None
    assert valor_numerico(True) is None


def test_tentar_usa_alternativa_e_relata_falhas():
    assert tentar("x", lambda: 1 / 0, lambda: 7) == 7
    with pytest.raises(RuntimeError, match="alt 2: KeyError"):
        tentar("y", lambda: 1 / 0, lambda: {}["k"])


# --------------------------------------------------- api: objetos e solve
def test_versao_alvo_antes_de_abrir(gsi_falso, gsz_sintetico):
    with Projeto(gsz_sintetico, versao="26.1"):
        pass
    assert gsi_falso.versao_alvo == "26.1"


def test_gravar_numero_confere_lendo_de_volta(gsi_falso, gsz_sintetico):
    with Projeto(gsz_sintetico) as p:
        p.p.valores[("Est", MAT)] = 18.0
        assert p.gravar("Est", MAT, 19.5) == 19.5
        assert p.ler("Est", MAT) == 19.5
    assert gsi_falso.ultimo["projeto"].fechado


def test_gravar_com_unidade_vai_como_struct(gsi_falso, gsz_sintetico):
    with Projeto(gsz_sintetico) as p:
        p.p.valores[("Est", MAT)] = 18.0
        assert p.gravar("Est", MAT, 120.0, unidade="lbf/ft³") == {"Value": 120.0, "Units": "lbf/ft³"}


def test_gravar_texto_e_booleano(gsi_falso, gsz_sintetico):
    with Projeto(gsz_sintetico) as p:
        p.p.valores[("Est", "Materials[\"Argila\"].SlopeModel")] = "MohrCoulomb"
        assert p.gravar("Est", "Materials[\"Argila\"].SlopeModel", "Undrained") == "Undrained"
        p.p.valores[("Est", "X.Ativo")] = False
        assert p.gravar("Est", "X.Ativo", True) is True


def test_gravacao_sem_efeito_e_detectada(gsi_falso, gsz_sintetico):
    with Projeto(gsz_sintetico) as p:
        p.p.valores[("Est", MAT)] = 18.0
        p.p.ignorar_gravacao = True
        with pytest.raises(RuntimeError, match="não teve o efeito esperado"):
            p.gravar("Est", MAT, 20.0)


def test_resolver_confere_status(gsi_falso, gsz_sintetico):
    with Projeto(gsz_sintetico) as p:
        p.resolver("Estabilidade/Jusante")
        assert p.p.resolvidas == ["Estabilidade/Jusante"]
        p.p.falha_solve = "malha inválida"
        with pytest.raises(RuntimeError, match="Estabilidade/Jusante: malha inválida"):
            p.resolver(["Estabilidade/Jusante"])


# ----------------------------------------------------------- api: resultados
def test_consultar_carrega_uma_vez_e_devolve_por_nome(gsi_falso, gsz_sintetico):
    with Projeto(gsz_sintetico) as p:
        assert p.tem_resultados("Estabilidade/Jusante")
        assert not p.tem_resultados("Tensões")
        r = p.consultar("Estabilidade/Jusante", "CriticalSlip", ["eRawSlipFOS", "eSlipRadius"])
        assert r == {"eRawSlipFOS": [1.437], "eSlipRadius": [16.0]}
        p.consultar("Estabilidade/Jusante", "CriticalSlip", ["eSlipCenterX"])
        assert p.p.carregadas == ["Estabilidade/Jusante"]


def test_parametros_tabela(gsi_falso, gsz_sintetico):
    with Projeto(gsz_sintetico) as p:
        info = p.parametros_tabela("Percolação", "Nodes")
    assert info[1] == {"parametro": "eWaterPressure", "chave": "eWaterPressure", "nome": "Water Pressure",
                       "unidade": "kPa", "categoria": "Pressure"}


# ------------------------------------------------------------ ferramentas API
def test_mapa_objetos_grava_csv_e_registra_falhas(gsi_falso, gsz_sintetico, monkeypatch):
    def abrir(caminho):
        from conftest import _Projeto
        proj = _Projeto(caminho)
        proj.valores[("Percolação", "Materials")] = [{"Name": "Argila", "KSat": {"Value": 1e-8, "Units": "m/s"}}]
        gsi_falso.ultimo["projeto"] = proj
        return proj

    monkeypatch.setattr(gsi_falso, "OpenProject", abrir)
    assert mapa_objetos.main([str(gsz_sintetico), "--analise", "Percolação"]) == 0
    csv = gsz_sintetico.with_name("talude_teste_mapa_objetos.csv").read_text(encoding="utf-8-sig")
    assert "Percolação;Materials[1].KSat;1e-08;m/s" in csv
    log = gsz_sintetico.with_name("talude_teste_mapa_objetos_log.txt").read_text(encoding="utf-8")
    assert "Percolação · CurrentAnalysis:" in log


def test_tabelas_resultados(gsi_falso, gsz_sintetico):
    assert tabelas_resultados.main([str(gsz_sintetico)]) == 0
    txt = gsz_sintetico.with_name("talude_teste_tabelas.txt").read_text(encoding="utf-8")
    assert "Tensões  ·  SIGMA/W" in txt and "sem resultados" in txt
    assert "Column (instância 1): 1 parâmetro(s)" in txt          # tentou sem instância, depois com 1
    csv = gsz_sintetico.with_name("talude_teste_tabelas.csv").read_text(encoding="utf-8-sig")
    assert "Estabilidade/Jusante;SLOPE/W;CriticalSlip;;eRawSlipFOS;Factor of Safety;;Undefined;1;1.437" in csv
    assert "Percolação;SEEP/W;Nodes;;eWaterPressure;Water Pressure;kPa;Pressure;3;50 | 30.5 | -2.1" in csv


def test_erro_cp1252_do_geostudio_fica_legivel():
    from modulos.comum.api import descrever_erro
    try:
        b"O arquivo est\xe1 aberto".decode("utf-8")
    except UnicodeDecodeError as e:
        assert descrever_erro(e) == "erro do GeoStudio: O arquivo está aberto"
