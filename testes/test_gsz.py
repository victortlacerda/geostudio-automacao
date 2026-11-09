import zipfile

import pytest

from modulos.comum.gsz import ArquivoGSZ, pasta_resultados


def test_le_analises_materiais_e_versao(gsz_sintetico):
    g = ArquivoGSZ(gsz_sintetico)
    assert g.info["Version"] == "26.1.0"
    assert [a.nome for a in g.analises] == ["Percolação", "Estabilidade/Jusante", "Tensões"]
    assert [a.tipo for a in g.analises] == ["SEEP/W", "SLOPE/W", "SIGMA/W"]
    argila = g.materiais[0]
    assert argila.nome == "Argila" and argila.modelo_slope == "MohrCoulomb"
    assert argila.resistencia == {"UnitWeight": "18", "CohesionPrime": "10", "PhiPrime": "25"}
    assert argila.hidraulico["KSat"] == "1e-08"


def test_arvore_coloca_filha_abaixo_do_pai(gsz_sintetico):
    g = ArquivoGSZ(gsz_sintetico)
    assert [(n, a.nome) for n, a in g.arvore()] == [
        (0, "Percolação"), (1, "Estabilidade/Jusante"), (0, "Tensões")]


def test_barra_no_nome_vira_e3_na_pasta(gsz_sintetico):
    g = ArquivoGSZ(gsz_sintetico)
    a = g.analise("Estabilidade/Jusante")
    assert pasta_resultados(a.nome) == "Estabilidade&3Jusante"
    assert g.passos(a) == ["000"]
    assert "Estabilidade&3Jusante/000/slip_surface.csv" in g.arquivos_resultado(a)


def test_le_node_csv_com_numeros(gsz_sintetico):
    g = ArquivoGSZ(gsz_sintetico)
    cab, linhas = g.ler_nos(g.analise("Percolação"))
    assert cab == ["Node", "X", "Y", "PoreWaterPressure", "TotalHead"]
    assert linhas[1]["PoreWaterPressure"] == pytest.approx(30.5)
    assert linhas[2]["PoreWaterPressure"] == pytest.approx(-2.1)


def test_analise_sem_resultado_avisa(gsz_sintetico):
    g = ArquivoGSZ(gsz_sintetico)
    t = g.analise("Tensões")
    assert not g.tem_resultados(t)
    with pytest.raises(LookupError, match="Resolva antes"):
        g.ler_nos(t)


def test_nome_inexistente_lista_as_analises(gsz_sintetico):
    with pytest.raises(KeyError, match="Percolação"):
        ArquivoGSZ(gsz_sintetico).analise("Não existe")


def test_xml_com_outro_nome_ainda_e_achado(tmp_path, gsz_sintetico):
    renomeado = tmp_path / "copia renomeada.gsz"
    renomeado.write_bytes(gsz_sintetico.read_bytes())
    assert ArquivoGSZ(renomeado).xml_principal == "talude_teste.xml"


def test_arquivo_que_nao_e_zip(tmp_path):
    falso = tmp_path / "x.gsz"
    falso.write_text("não sou zip")
    with pytest.raises(ValueError, match="não abre como ZIP"):
        ArquivoGSZ(falso)


def test_zip_sem_xml(tmp_path):
    vazio = tmp_path / "vazio.gsz"
    with zipfile.ZipFile(vazio, "w") as z:
        z.writestr("leia.txt", "nada")
    with pytest.raises(ValueError, match="nenhum XML"):
        ArquivoGSZ(vazio)
