"""Módulo 01 (auditoria) com a amostra real e com uma cópia que ganha uma 2ª análise (outro método)."""
import importlib.util
import re
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
AMOSTRA = RAIZ / "testes" / "dados" / "s00_talude5m.gsz"


def _aud():
    spec = importlib.util.spec_from_file_location("auditoria", RAIZ / "modulos" / "01_auditoria" / "auditoria.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _com_segunda_analise(destino):
    """Cópia da amostra com a análise 2 'Spencer' (mesmos resultados, FS 2 % menor)."""
    with zipfile.ZipFile(AMOSTRA) as z:
        itens = {n: z.read(n) for n in z.namelist()}
    xml_nome = "s00_talude5m.xml"
    xml = itens[xml_nome].decode("utf-8")
    bloco = re.search(r"<Analysis>.*?</Analysis>", xml, re.S).group(0)
    novo = bloco.replace("<ID>1</ID>", "<ID>2</ID>").replace("Análise SLOPE/W", "Spencer") \
                .replace("Morgenstern-Price", "Spencer")
    xml = xml.replace('<Analyses Len="1">', '<Analyses Len="2">').replace(bloco, bloco + novo)
    for secao, item in (("Contexts", "Context"), ("StabilityItems", "StabilityItem")):
        b = re.search(rf"<{item}>\s*<AnalysisID>1</AnalysisID>.*?</{item}>", xml, re.S).group(0)
        xml = xml.replace(b, b + b.replace("<AnalysisID>1</AnalysisID>", "<AnalysisID>2</AnalysisID>"), 1)
    itens[xml_nome] = xml.encode("utf-8")
    pasta1 = "Análise SLOPE&3W/"
    for n, dados in list(itens.items()):
        if n.startswith(pasta1) and n.endswith(".csv"):
            if n.endswith("slip_surface.csv"):
                linhas = dados.decode("utf-8").splitlines()
                cab = linhas[0].split(",")
                i = cab.index("SlipFOS")
                novas = [linhas[0]]
                for l in linhas[1:]:
                    c = l.split(",")
                    if c[i] and float(c[i]) < 900:
                        c[i] = repr(float(c[i]) * 0.98)
                    novas.append(",".join(c))
                dados = "\n".join(novas).encode("utf-8")
            itens["Spencer/" + n[len(pasta1):]] = dados
    with zipfile.ZipFile(destino, "w") as z:
        for n, d in itens.items():
            z.writestr(n, d)
    return destino


def test_auditoria_amostra_real(tmp_path):
    aud = _aud()
    destino, r = aud.gerar_relatorio(AMOSTRA, 1.5, tmp_path)
    html = destino.read_text(encoding="utf-8")
    assert r["parecer"] == "ALERTA"
    assert r["fs_min"] == pytest.approx(1.786, abs=5e-4)
    assert r["contagem"]["ERRO"] == 0
    assert any("borda da faixa esquerda" in m for _, m in r["achados"])
    assert any("condição seca" in m for _, m in r["achados"])
    assert "Argila" in html and "150,00" in html          # material e área da região (20x10 - trapézio)
    assert html.count("data:image/png;base64") >= 2         # geometria + crítica embutidas
    assert "Comparação de métodos" not in html               # só uma análise


def test_auditoria_compara_metodos(tmp_path):
    aud = _aud()
    gsz = _com_segunda_analise(tmp_path / "dois_metodos.gsz")
    destino, r = aud.gerar_relatorio(gsz, 1.5, tmp_path / "saida")
    html = destino.read_text(encoding="utf-8")
    metodos = {m: fs for _, m, fs in r["metodos"]}
    assert metodos["Morgenstern-Price"] == pytest.approx(1.786, abs=5e-4)
    assert metodos["Spencer"] == pytest.approx(1.786 * 0.98, abs=5e-4)
    assert r["fs_min"] == pytest.approx(1.786 * 0.98, abs=5e-4)
    assert "Comparação de métodos" in html
    assert any("Métodos rigorosos diferem" in m for _, m in r["achados"])


def test_checagem_de_materiais():
    aud = _aud()
    from modulos.comum.modelo import MaterialModelo, Modelo
    mats = {
        "1": MaterialModelo("1", "Ok", "#fff", "MohrCoulomb", parametros={"UnitWeight": 18, "CohesionPrime": 5, "PhiPrime": 30}),
        "2": MaterialModelo("2", "Sem resistência", "#fff", "MohrCoulomb", parametros={"UnitWeight": 18}),
        "3": MaterialModelo("3", "Leve", "#fff", "MohrCoulomb", parametros={"UnitWeight": 9, "PhiPrime": 50}),
    }
    m = Modelo({}, "Metric", {}, [], mats, {}, {}, {}, {})
    r = aud.checar_materiais(m, usados={"1", "2", "3"})
    assert r["1"] == []
    assert any(n == "ERRO" and "sem resistência" in t for n, t in r["2"])
    assert sum(n == "ALERTA" for n, _ in r["3"]) == 2      # γ baixo e φ' alto
    assert not any(n == "ERRO" for n, _ in r["3"])


METODOS_REAIS = {          # GeoStudio 2026.1, licença de estudante, 13/11/2026; Fellenius conferido na interface
    "s04a_spencer.gsz": ("Spencer", 1.788),
    "s04b_bishop.gsz": ("Bishop", 1.792),
    "s04c_janbu.gsz": ("Janbu", 1.675),
    "s04d_fellenius.gsz": ("Ordinary", 1.691),
}


@pytest.mark.parametrize("arquivo", sorted(METODOS_REAIS))
def test_metodos_reais(arquivo):
    from modulos.comum.gsz import ArquivoGSZ
    from modulos.comum.slope import checagens, ler_resultados
    g = ArquivoGSZ(RAIZ / "testes" / "dados" / arquivo)
    metodo, fs = METODOS_REAIS[arquivo]
    a = g.analises[1]
    assert a.metodo == metodo
    r = ler_resultados(g, a)
    assert r.critica.fs == pytest.approx(fs, abs=5e-4)
    assert r.critica.numero == 369
    checagens(r)                                    # não pode quebrar com colunas de λ vazias
    assert ler_resultados(g, g.analises[0]).critica.fs == pytest.approx(1.786, abs=5e-4)


def test_comparacao_entre_arquivos(tmp_path):
    aud = _aud()
    arquivos = [RAIZ / "testes" / "dados" / a for a in sorted(METODOS_REAIS)]
    destino, metodos, achados = aud.gerar_comparacao(arquivos, 1.5, tmp_path / "comp.html")
    assert [m for _, m, _ in metodos] == ["Janbu", "Ordinary", "Morgenstern-Price", "Spencer", "Bishop"]
    assert len(metodos) == 5                        # M-P repetido nos 4 arquivos entra uma vez
    assert not any(n == "ALERTA" for n, _ in achados)
    assert "Fellenius (Ordinário)" in destino.read_text(encoding="utf-8")


def test_modulo02_metodos_simplificados(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "rs", RAIZ / "modulos" / "02_resultados_slope" / "resultados_slope.py")
    rs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rs)
    saida, resultados, _ = rs.processar(RAIZ / "testes" / "dados" / "s04b_bishop.gsz", 1.5, tmp_path)
    assert (tmp_path / "resultados_slope.xlsx").exists()
    assert (tmp_path / "Análise_SLOPE_W_lambda.png").exists()     # M-P tem curva FS x λ
    assert not (tmp_path / "Bishop_lambda.png").exists()          # Bishop não varre λ
