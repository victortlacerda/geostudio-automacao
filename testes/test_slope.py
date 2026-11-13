"""Módulo 02 com a amostra real s00_talude5m.gsz (GeoStudio 2026.1, licença de estudante).

Gabarito conferido na interface do GeoStudio: superfície crítica 369, FS = 1,786 (Morgenstern-Price).
"""
from pathlib import Path
import importlib.util

import pytest

from modulos.comum.gsz import ArquivoGSZ
from modulos.comum.slope import checagens, geometria, ler_resultados

AMOSTRA = Path(__file__).parent / "dados" / "s00_talude5m.gsz"


@pytest.fixture(scope="module")
def res():
    return ler_resultados(ArquivoGSZ(AMOSTRA), "Análise SLOPE/W")


def test_fs_critico_igual_ao_da_interface(res):
    c = res.critica
    assert c.numero == 369
    assert c.fs == pytest.approx(1.786, abs=5e-4)
    assert res.metodo == "Morgenstern-Price"


def test_superficies_validas_e_invalidas(res):
    assert len(res.superficies) == 405
    assert len(res.validas) == 225
    assert res.invalidas_por_codigo() == {998: 180}
    assert [s.numero for s in res.com_detalhe()] == [369, 364, 374, 365, 324]


def test_fatias_e_lambda_da_critica(res):
    c = res.critica
    assert len(c.fatias) == 31
    (x0, y0), (x1, y1) = c.entrada_saida()
    assert (x0, y0) == pytest.approx((6.5, 5.0))
    assert (x1, y1) == pytest.approx((14.1875, 10.0))
    ultimo = max(c.lambda_fs, key=lambda d: d["LambdaEntryNum"])
    assert ultimo["FOSByMoment"] == pytest.approx(ultimo["FOSByForce"], abs=1e-3)


def test_configuracao_da_busca(res):
    cfg = res.configuracao
    assert cfg["direcao"] == "RightToLeft"
    assert cfg["entrada"] == ((1.0, 5.0), (6.5, 5.0))
    assert cfg["criticas_guardadas"] == 5


def test_checagens(res):
    msgs = checagens(res, fs_alvo=1.5)
    assert any("borda da faixa esquerda" in m for _, m in msgs)       # sai em x = 6,5 = fim da faixa
    assert not any("abaixo do alvo" in m for _, m in msgs)
    assert any("abaixo do alvo" in m for _, m in checagens(res, fs_alvo=2.0))


def test_geometria():
    pontos, regioes = geometria(ArquivoGSZ(AMOSTRA))
    assert pontos["4"] == (12.5, 10.0)
    assert regioes == [["1", "2", "3", "4", "5", "6"]]


def test_modulo_gera_planilha_e_figuras(tmp_path):
    caminho = Path(__file__).parents[1] / "modulos" / "02_resultados_slope" / "resultados_slope.py"
    spec = importlib.util.spec_from_file_location("resultados_slope", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main([str(AMOSTRA), "--fs-alvo", "1.5", "--saida", str(tmp_path)]) == 0
    nomes = {p.name for p in tmp_path.iterdir()}
    assert "resultados_slope.xlsx" in nomes
    assert {n for n in nomes if n.endswith(".png")} == {
        "Análise_SLOPE_W_critica.png", "Análise_SLOPE_W_fatias.png", "Análise_SLOPE_W_lambda.png"}
    from openpyxl import load_workbook
    wb = load_workbook(tmp_path / "resultados_slope.xlsx")
    assert wb.sheetnames == ["Resumo", "Superfícies", "Fatias", "Entre fatias", "Lambda x FS", "Figuras"]
    assert wb["Resumo"]["D5"].value == pytest.approx(1.7862, abs=1e-4)
    assert wb["Resumo"]["F5"].value == "OK"


def test_sem_resultados_avisa(gsz_sintetico):
    with pytest.raises(LookupError, match="Resolva"):
        ler_resultados(_sem_resultado(gsz_sintetico), "Estabilidade/Jusante")


def _sem_resultado(gsz):
    import zipfile
    destino = gsz.with_name("sem.gsz")
    with zipfile.ZipFile(gsz) as zi, zipfile.ZipFile(destino, "w") as zo:
        zo.writestr("sem.xml", zi.read("talude_teste.xml"))
    return ArquivoGSZ(destino)
