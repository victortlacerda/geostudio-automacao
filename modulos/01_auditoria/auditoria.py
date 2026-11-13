#!/usr/bin/env python3
"""Módulo 01: auditoria do projeto GeoStudio, com relatório em HTML. Só lê o .gsz (sem API).

Resume o projeto inteiro e confere a coerência dos dados, no molde do soiltest_auditoria do
plaxis3d-automacao (ERRO / ALERTA / INFO):

  1. Projeto: arquivo, versão do GeoStudio, revisão, data, unidades, seções do modelo.
  2. Análises: árvore, tipo, método, se está resolvida, FS e verificação contra o FS alvo.
  3. Comparação de métodos (quando há mais de uma análise SLOPE/W resolvida): tabela, gráfico e
     superfícies críticas sobrepostas.
  4. Geometria: figura com as regiões coloridas pelo material, áreas, extensão do modelo.
  5. Materiais: parâmetros e checagens (faixas usuais de literatura; são alertas, não regras).
  6. Cada análise SLOPE/W: busca de superfícies, superfície crítica, superfícies inválidas e checagens.

Saída: <nome>_auditoria/relatorio.html (um arquivo só, com as figuras embutidas; abre no navegador
e imprime em PDF) ao lado do .gsz.

Uso:
    python auditoria.py                       # escolhe o(s) .gsz numa janela; pergunta o FS alvo
    python auditoria.py talude.gsz --fs-alvo 1.5
    python auditoria.py pasta_de_modelos      # todos os .gsz da pasta
No Windows também dá para arrastar o .gsz em cima de auditoria.bat.

[não testado] em modelos com mais de uma geometria, SEEP/W e SIGMA/W (só inventário, sem checagens).
"""
from __future__ import annotations

import argparse
import base64
import datetime
import html
import importlib.util
import io
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from modulos.comum.gsz import ArquivoGSZ  # noqa: E402
from modulos.comum.modelo import ler_modelo  # noqa: E402
from modulos.comum.slope import CODIGOS, RIGOROSOS, checagens, ler_resultados, nome_metodo  # noqa: E402

VERSAO = "auditoria-v0.1"
NIVEIS = ("ERRO", "ALERTA", "INFO")

# Faixas usuais para Mohr-Coulomb (literatura); fora delas é ALERTA, não erro.
FAIXA_GAMA = (14.0, 23.0)       # kN/m³
FAIXA_PHI = (15.0, 45.0)        # graus
COESAO_ALTA = 30.0              # kPa


def _modulo02():
    """Reaproveita as figuras do módulo 02 (a pasta começa com número, então importa pelo caminho)."""
    caminho = RAIZ / "modulos" / "02_resultados_slope" / "resultados_slope.py"
    spec = importlib.util.spec_from_file_location("resultados_slope", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ utilidades
def esc(x):
    return html.escape("" if x is None else str(x))


def num(v, casas=2):
    if v is None or v == "":
        return "–"
    if isinstance(v, (int, float)):
        return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return esc(v)


def tabela(cab, linhas, classe=""):
    h = "".join(f"<th>{esc(c)}</th>" for c in cab)
    corpo = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in linhas)
    return f'<div class="tab"><table class="{classe}"><thead><tr>{h}</tr></thead><tbody>{corpo}</tbody></table></div>'


def selo(nivel):
    return f'<span class="selo {nivel.lower()}">{nivel}</span>'


def lista_achados(achados):
    if not achados:
        return '<p class="ok">Nenhum alerta.</p>'
    return "<ul class=\"achados\">" + "".join(
        f"<li>{selo(n)} {esc(m)}</li>" for n, m in sorted(achados, key=lambda a: NIVEIS.index(a[0]))) + "</ul>"


def figura_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def img(b64, legenda):
    return f'<figure><img src="data:image/png;base64,{b64}" alt="{esc(legenda)}"><figcaption>{esc(legenda)}</figcaption></figure>'


def png_arquivo_base64(caminho):
    return base64.b64encode(Path(caminho).read_bytes()).decode()


# ----------------------------------------------------------------- checagens
def checar_materiais(modelo, usados):
    """Devolve {id material: [(nível, mensagem)]}."""
    saida = {}
    for mid, m in modelo.materiais.items():
        a = []
        p = m.parametros
        g, c, phi = p.get("UnitWeight"), p.get("CohesionPrime"), p.get("PhiPrime")
        if mid not in usados:
            a.append(("INFO", "Material não está atribuído a nenhuma região."))
        if m.modelo_slope and m.modelo_slope != "MohrCoulomb":
            a.append(("INFO", f"Modelo de resistência '{m.modelo_slope}': só γ é conferido."))
        if g is None:
            a.append(("ERRO", "Peso específico não definido."))
        elif g <= 0:
            a.append(("ERRO", f"γ = {g} deve ser positivo."))
        elif not FAIXA_GAMA[0] <= g <= FAIXA_GAMA[1]:
            a.append(("ALERTA", f"γ = {g:.1f} kN/m³ fora da faixa usual ({FAIXA_GAMA[0]:.0f} a {FAIXA_GAMA[1]:.0f})."))
        if m.modelo_slope == "MohrCoulomb":
            if phi is not None and not 0 <= phi < 90:
                a.append(("ERRO", f"φ' = {phi}° fora do intervalo físico (0 a 90°)."))
            elif phi is not None and phi > 0 and not FAIXA_PHI[0] <= phi <= FAIXA_PHI[1]:
                a.append(("ALERTA", f"φ' = {phi:.1f}° fora da faixa usual ({FAIXA_PHI[0]:.0f} a {FAIXA_PHI[1]:.0f}°)."))
            if c is not None and c < 0:
                a.append(("ERRO", f"c' = {c} kPa negativo."))
            if (c or 0) == 0 and (phi or 0) == 0:
                a.append(("ERRO", "c' e φ' nulos: material sem resistência."))
            if c is not None and c > COESAO_ALTA:
                a.append(("INFO", f"c' = {c:.1f} kPa (> {COESAO_ALTA:.0f} kPa): confirme que é efetiva e não total."))
            if (c or 0) == 0 and (phi or 0) > 0:
                a.append(("INFO", "Sem coesão: superfícies rasas tendem a FS ≈ tan φ'/tan β (talude infinito)."))
        saida[mid] = a
    return saida


def checar_projeto(arquivo, modelo):
    a = []
    if modelo.unidades and modelo.unidades != "Metric":
        a.append(("ALERTA", f"Sistema de unidades '{modelo.unidades}': os scripts assumem kN, m, kPa."))
    for r in modelo.regioes:
        if r.area <= 0:
            a.append(("ERRO", f"Região {r.id} com área nula."))
    for an in arquivo.analises:
        mapa = modelo.regiao_material.get(an.id, {})
        sem = [r.id for r in modelo.regioes if r.id not in mapa]
        if sem:
            a.append(("ERRO", f"{an.nome}: região(ões) {', '.join(sem)} sem material."))
        if not arquivo.tem_resultados(an):
            a.append(("ALERTA", f"{an.nome}: análise sem resultados no arquivo (resolva e salve)."))
    if not _tem_agua(modelo.raiz):
        a.append(("INFO", "Nenhuma linha piezométrica ou poropressão no modelo: análise em condição seca. Confirme."))
    for tag in ("Reinforcements", "PointLoads", "SurchargeLoads"):
        if modelo.secoes.get(tag):
            a.append(("INFO", f"O modelo tem {modelo.secoes[tag]} item(ns) em '{tag}': "
                              "a auditoria ainda não interpreta essa seção [não testado]."))
    return a


def _tem_agua(raiz):
    """Linha piezométrica ou condição de poropressão com conteúdo em algum lugar do modelo.
    [não testado]: nomes das tags confirmados só pela ausência na amostra seca s00_talude5m."""
    if raiz is None:
        return False
    return any(("piezo" in el.tag.lower() or "porewater" in el.tag.lower()) and len(el) for el in raiz.iter())


def checar_busca(cfg):
    a = []
    if not cfg:
        return [("ALERTA", "Busca de superfícies não encontrada no arquivo.")]
    if cfg.get("criticas_guardadas", 1) < 2:
        a.append(("INFO", "Só 1 superfície crítica guardada: guarde mais (ex.: 5) para ver a vizinhança do mínimo."))
    inc = cfg.get("incrementos")
    if inc and min(inc) < 4:
        a.append(("ALERTA", f"Poucos incrementos nas faixas de entrada e saída ({inc[0]} e {inc[1]})."))
    return a


def comparar_metodos(resultados):
    """resultados: [(analise, ResultadoSlope)]. Devolve (linhas, achados)."""
    validos = [(a, r) for a, r in resultados if r.critica]
    if len(validos) < 2:
        return [], []
    fss = [r.critica.fs for _, r in validos]
    fmin, fmax = min(fss), max(fss)
    achados = [("INFO", f"FS entre {num(fmin, 3)} e {num(fmax, 3)} nos {len(validos)} métodos "
                        f"(variação de {num(100 * (fmax - fmin) / fmin, 1)} %).")]
    rig = [r.critica.fs for a, r in validos if any(k in (a.metodo or "").lower() for k in RIGOROSOS)]
    if len(rig) >= 2 and (max(rig) - min(rig)) / min(rig) > 0.02:
        achados.append(("ALERTA", f"Métodos rigorosos diferem mais de 2 % ({num(min(rig), 3)} a {num(max(rig), 3)}): "
                                  "confira a convergência e a função de força entre fatias."))
    nums = {r.critica.numero for _, r in validos}
    if len(nums) > 1:
        achados.append(("INFO", "A superfície crítica muda com o método (veja a figura sobreposta)."))
    linhas = [(a, r, (r.critica.fs - fmin) / fmin) for a, r in validos]
    return linhas, achados


def converter_nivel(n):
    return {"ATENÇÃO": "ALERTA", "AVISO": "ALERTA"}.get(n, n)


# ------------------------------------------------------------------- figuras
def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def figura_geometria(modelo, analise_id):
    plt = _plt()
    from matplotlib.patches import Polygon
    fig, ax = plt.subplots(figsize=(9, 4.6))
    vistos = set()
    for r in modelo.regioes:
        m = modelo.material_da_regiao(analise_id, r.id)
        cor = m.cor if m else "#ffffff"
        rot = (m.nome if m else "sem material") if (m.id if m else None) not in vistos else None
        vistos.add(m.id if m else None)
        ax.add_patch(Polygon(r.xy, closed=True, facecolor=cor, edgecolor="#444", lw=1, label=rot))
        if r.xy:
            cx = sum(p[0] for p in r.xy) / len(r.xy)
            cy = sum(p[1] for p in r.xy) / len(r.xy)
            ax.text(cx, cy, f"R{r.id}", ha="center", va="center", fontsize=8, color="#333")
    for pid, (x, y) in modelo.pontos.items():
        ax.plot(x, y, "o", ms=2.5, color="#333")
        ax.annotate(pid, (x, y), xytext=(3, 3), textcoords="offset points", fontsize=7, color="#666")
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.grid(True, lw=0.3, alpha=0.5)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return figura_base64(fig)


def figura_metodos(linhas, fs_alvo):
    plt = _plt()
    nomes = [a.nome if not a.metodo or a.nome.startswith(nome_metodo(a.metodo)) or a.nome.startswith(a.metodo)
             else f"{nome_metodo(a.metodo)}\n({a.nome})" for a, _, _ in linhas]
    fss = [r.critica.fs for _, r, _ in linhas]
    fig, ax = plt.subplots(figsize=(9, 0.55 * len(linhas) + 1.4))
    y = range(len(linhas))
    ax.barh(list(y), fss, color=["#c0392b" if f < fs_alvo else "#2c6fbb" for f in fss], height=0.6)
    for i, f in zip(y, fss):
        ax.text(f, i, f"  {f:.3f}".replace(".", ","), va="center", fontsize=9)
    ax.axvline(fs_alvo, color="#555", ls="--", lw=1, label=f"FS alvo {fs_alvo:.2f}".replace(".", ","))
    ax.legend(loc="lower right", fontsize=8)
    ax.set_yticks(list(y))
    ax.set_yticklabels(nomes, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, max(fss + [fs_alvo]) * 1.15)
    ax.set_xlabel("Fator de segurança")
    ax.grid(True, axis="x", lw=0.3, alpha=0.5)
    fig.tight_layout()
    return figura_base64(fig)


def figura_sobreposta(modelo, linhas):
    plt = _plt()
    from matplotlib.patches import Polygon
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for r in modelo.regioes:
        ax.add_patch(Polygon(r.xy, closed=True, facecolor="#f3e9c6", edgecolor="#555", lw=1))
    cores = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    for i, (a, r, _) in enumerate(linhas):
        b = r.critica.base()
        if b:
            ax.plot([p[0] for p in b], [p[1] for p in b], color=cores[i % len(cores)], lw=1.6,
                    label=f"{nome_metodo(a.metodo) or a.nome}: FS {r.critica.fs:.3f} (nº {r.critica.numero})")
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.grid(True, lw=0.3, alpha=0.5)
    ax.legend(loc="lower right", fontsize=7)
    fig.tight_layout()
    return figura_base64(fig)


# ------------------------------------------------------------------ relatório
CSS = """
:root{--fundo:#f7f7f5;--papel:#ffffff;--texto:#1f2328;--suave:#5b6470;--linha:#d8dbe0;
--destaque:#2c6fbb;--erro:#b42318;--erro-f:#fde7e5;--alerta:#9a5b00;--alerta-f:#fff1d6;
--info:#34557a;--info-f:#e6eef8;--ok:#1d7a3a;--ok-f:#e3f4e8}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--fundo:#16181c;--papel:#1e2127;
--texto:#e6e8eb;--suave:#9aa3ad;--linha:#353a42;--destaque:#6aa5ec;--erro:#ff8a80;--erro-f:#3a1d1b;
--alerta:#f2b55c;--alerta-f:#352a14;--info:#9cc0ea;--info-f:#1c2836;--ok:#7fd49a;--ok-f:#17301f}}
*{box-sizing:border-box}body{margin:0;background:var(--fundo);color:var(--texto);
font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1040px;margin:0 auto;padding:24px 16px 64px}
header{border-bottom:2px solid var(--texto);padding-bottom:12px;margin-bottom:20px}
h1{font-size:1.6rem;margin:0 0 4px}h2{font-size:1.2rem;margin:36px 0 10px;padding-bottom:4px;
border-bottom:1px solid var(--linha)}h3{font-size:1.02rem;margin:22px 0 8px}
.sub{color:var(--suave);font-size:.9rem}
.cartoes{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.cartao{background:var(--papel);border:1px solid var(--linha);border-radius:8px;padding:10px 12px}
.cartao b{display:block;font-size:1.35rem;font-variant-numeric:tabular-nums}
.cartao span{color:var(--suave);font-size:.82rem}
.tab{overflow-x:auto;margin:8px 0 14px}table{border-collapse:collapse;width:100%;background:var(--papel);
font-size:.88rem}th,td{border:1px solid var(--linha);padding:5px 8px;text-align:left;vertical-align:top}
th{background:var(--fundo);font-weight:600}td{font-variant-numeric:tabular-nums}
.selo{display:inline-block;font-size:.72rem;font-weight:700;padding:1px 6px;border-radius:4px;
letter-spacing:.02em;margin-right:4px}.selo.erro{color:var(--erro);background:var(--erro-f)}
.selo.alerta{color:var(--alerta);background:var(--alerta-f)}.selo.info{color:var(--info);background:var(--info-f)}
.selo.ok{color:var(--ok);background:var(--ok-f)}.ok{color:var(--ok)}
ul.achados{list-style:none;padding:0;margin:6px 0}ul.achados li{padding:4px 0;border-bottom:1px dashed var(--linha)}
figure{margin:12px 0;background:#fff;border:1px solid var(--linha);border-radius:6px;padding:6px}
figure img{max-width:100%;height:auto;display:block;margin:0 auto}
figcaption{font-size:.8rem;color:#5b6470;text-align:center;padding-top:4px}
.nota{color:var(--suave);font-size:.84rem}footer{margin-top:40px;color:var(--suave);font-size:.8rem}
@media print{body{background:#fff}main{max-width:none}h2{break-after:avoid}figure,table{break-inside:avoid}}
"""


def gerar_relatorio(caminho: Path, fs_alvo=1.5, pasta_saida: Path | None = None):
    arquivo = ArquivoGSZ(caminho)
    modelo = ler_modelo(arquivo)
    m02 = _modulo02()
    saida = pasta_saida or caminho.with_name(caminho.stem + "_auditoria")
    saida.mkdir(parents=True, exist_ok=True)

    achados_projeto = checar_projeto(arquivo, modelo)
    usados = {mid for mapa in modelo.regiao_material.values() for mid in mapa.values()}
    achados_mat = checar_materiais(modelo, usados)

    # resultados de cada análise SLOPE/W (sem abortar na primeira falha)
    res_slope, achados_analise, falhas = [], {}, []
    for a in arquivo.analises:
        ach = []
        if "SLOPE" in (a.tipo or "").upper():
            ach += [(n, m) for n, m in checar_busca(modelo.busca.get(a.id, {}))]
            if arquivo.tem_resultados(a):
                try:
                    r = ler_resultados(arquivo, a)
                    res_slope.append((a, r))
                    ach += [(converter_nivel(n), f"{a.nome}: {m}") for n, m in checagens(r, fs_alvo)]
                except Exception as e:  # noqa: BLE001
                    falhas.append(f"{a.nome}: {e}")
                    ach.append(("ERRO", f"Não foi possível ler os resultados: {e}"))
        else:
            ach.append(("INFO", f"Análise {a.tipo}: só inventário nesta versão da auditoria."))
        achados_analise[a.id] = ach
    linhas_met, achados_met = comparar_metodos(res_slope)

    todos = achados_projeto + achados_met + [x for v in achados_mat.values() for x in v] \
        + [x for v in achados_analise.values() for x in v]
    cont = {n: sum(1 for a in todos if a[0] == n) for n in NIVEIS}
    fs_min = min((r.critica.fs for _, r in res_slope if r.critica), default=None)
    parecer = ("ERRO" if cont["ERRO"] else "ALERTA" if cont["ALERTA"] else "OK")

    info = modelo.info
    partes = []
    partes.append(f"""<header><h1>Auditoria do projeto · {esc(caminho.name)}</h1>
<div class="sub">GeoStudio {esc(info.get('AppVersion', '?'))} · revisão {esc(info.get('RevNumber', '?'))}
· salvo em {esc(info.get('Date', '?'))} {esc(info.get('Time', ''))} · unidades {esc(modelo.unidades or '?')}
· auditado em {datetime.datetime.now():%d/%m/%Y %H:%M} · {VERSAO}</div></header>""")

    # ---------------- resumo
    cartoes = [
        (selo(parecer if parecer != "OK" else "OK"), "Parecer"),
        (num(fs_min, 3) if fs_min is not None else "–", f"FS mínimo (alvo {num(fs_alvo)})"),
        (str(len(arquivo.analises)), "Análises"),
        (str(len(modelo.materiais)), "Materiais"),
        (str(cont["ERRO"]), "Erros"), (str(cont["ALERTA"]), "Alertas"), (str(cont["INFO"]), "Notas"),
    ]
    partes.append("<h2>Resumo</h2><div class=\"cartoes\">" + "".join(
        f'<div class="cartao"><b>{v}</b><span>{esc(t)}</span></div>' for v, t in cartoes) + "</div>")
    res_por_id = {a.id: r for a, r in res_slope}
    linhas = []
    for nivel, a in arquivo.arvore():
        r = res_por_id.get(a.id)
        c = r.critica if r else None
        verif = ("–" if c is None else selo("OK") if c.fs >= fs_alvo else selo("ERRO").replace("ERRO", "NÃO ATENDE"))
        linhas.append(("&nbsp;" * 4 * nivel + esc(a.nome), esc(a.tipo), esc(nome_metodo(a.metodo)),
                       "sim" if arquivo.tem_resultados(a) else "<b>não</b>",
                       num(c.fs, 3) if c else "–", str(c.numero) if c else "–", verif))
    partes.append(tabela(["Análise", "Tipo", "Método", "Resolvida", "FS", "Superfície", f"FS ≥ {num(fs_alvo)}"], linhas))
    partes.append("<h3>Achados do projeto</h3>" + lista_achados(achados_projeto))
    partes.append('<p class="nota">ERRO: dado incoerente ou que impede a análise. ALERTA: fora da faixa usual '
                  'ou situação que pede conferência. INFO: observação. As faixas de materiais são referências '
                  'de literatura, não regras de norma.</p>')

    # ---------------- comparação de métodos
    if linhas_met:
        partes.append("<h2>Comparação de métodos</h2>")
        partes.append(tabela(["Análise", "Método", "FS", "Δ do mínimo", "Superfície", "Centro (x; y)", "Raio",
                              "Entrada → saída (x)"],
                             [(esc(a.nome), esc(nome_metodo(a.metodo)), f"<b>{num(r.critica.fs, 3)}</b>", ("+" if d > 0 else "") + num(100 * d, 1) + " %",
                               str(r.critica.numero),
                               f"{num(r.critica.centro_x)}; {num(r.critica.centro_y)}", num(r.critica.raio),
                               _entrada_saida_txt(r.critica)) for a, r, d in linhas_met]))
        partes.append(lista_achados(achados_met))
        partes.append(img(figura_metodos(linhas_met, fs_alvo), "FS da superfície crítica por método"))
        partes.append(img(figura_sobreposta(modelo, linhas_met), "Superfícies críticas de cada método"))

    # ---------------- geometria
    ext = modelo.extensao
    partes.append("<h2>Geometria</h2>")
    if ext:
        partes.append(f"<p>Extensão: x de {num(ext[0])} a {num(ext[1])} m, y de {num(ext[2])} a {num(ext[3])} m · "
                      f"{len(modelo.pontos)} pontos · {len(modelo.regioes)} região(ões).</p>")
    primeira = arquivo.analises[0].id if arquivo.analises else "1"
    if modelo.regioes:
        partes.append(img(figura_geometria(modelo, primeira), "Regiões e materiais (primeira análise)"))
        partes.append(tabela(["Região", "Pontos", "Área (m²)", "Material"],
                             [(f"R{r.id}", esc(", ".join(r.pontos)), num(r.area),
                               esc((modelo.material_da_regiao(primeira, r.id) or type("x", (), {"nome": "–"})).nome))
                              for r in modelo.regioes]))

    # ---------------- materiais
    partes.append("<h2>Materiais</h2>")
    partes.append(tabela(["Material", "Modelo", "γ (kN/m³)", "c' (kPa)", "φ' (°)", "Situação"],
                         [(f'<span style="display:inline-block;width:10px;height:10px;background:{m.cor};'
                           f'border:1px solid #888;margin-right:6px"></span>{esc(m.nome)}',
                           esc(m.modelo_slope or m.modelo_sigma or m.modelo_seep),
                           num(m.parametros.get("UnitWeight"), 1), num(m.parametros.get("CohesionPrime"), 1),
                           num(m.parametros.get("PhiPrime"), 1), _situacao(achados_mat[mid]))
                          for mid, m in modelo.materiais.items()]))
    for mid, m in modelo.materiais.items():
        if achados_mat[mid]:
            partes.append(f"<h3>{esc(m.nome)}</h3>" + lista_achados(achados_mat[mid]))

    # ---------------- análises
    for a in arquivo.analises:
        partes.append(f"<h2>Análise · {esc(a.nome)}</h2>")
        partes.append(f'<p class="sub">{esc(a.tipo)} · {esc(nome_metodo(a.metodo))}'
                      + (f" · filha da análise {esc(a.pai_id)}" if a.pai_id else "") + "</p>")
        cfg = modelo.busca.get(a.id)
        if cfg:
            partes.append("<h3>Busca de superfícies</h3>" + tabela(["Item", "Valor"], _linhas_busca(cfg)))
        agua = modelo.agua.get(a.id)
        if agua and agua.get("UnitWaterWeight"):
            partes.append(f'<p class="nota">Peso específico da água: {num(agua["UnitWaterWeight"], 3)} kN/m³.</p>')
        r = res_por_id.get(a.id)
        if r and r.critica:
            c = r.critica
            inv = r.invalidas_por_codigo()
            partes.append("<h3>Resultado</h3>" + tabela(["Item", "Valor"], [
                ("FS da superfície crítica", f"<b>{num(c.fs, 3)}</b> (nº {c.numero})"),
                ("Centro (x; y) e raio", f"{num(c.centro_x)}; {num(c.centro_y)} · R = {num(c.raio)} m"),
                ("Entrada → saída", _entrada_saida_txt(c)),
                ("Volume e peso da massa", f"{num(c.volume)} m³/m · {num(c.peso, 1)} kN/m"),
                ("λ na convergência", num(c.lambda_, 3)),
                ("Superfícies testadas", f"{len(r.superficies)} ({len(r.validas)} válidas)"),
                ("Inválidas por código", ", ".join(f"{k} ({CODIGOS.get(k, 'código ' + str(k))}): {v}"
                                                   for k, v in inv.items()) or "nenhuma"),
            ]))
            destino = saida / f"{m02.nome_arquivo(a.nome)}_critica.png"
            pontos = {k: v for k, v in modelo.pontos.items()}
            m02.figura_critica(r, pontos, [rg.pontos for rg in modelo.regioes], destino)
            partes.append(img(png_arquivo_base64(destino), f"{a.nome}: superfície crítica e faixas de busca"))
            destino.unlink(missing_ok=True)
        partes.append("<h3>Achados</h3>" + lista_achados(achados_analise.get(a.id, [])))

    # ---------------- rastreabilidade
    partes.append("<h2>Rastreabilidade</h2>")
    partes.append(tabela(["Seção do modelo (XML)", "Itens"], [(esc(k), str(v)) for k, v in modelo.secoes.items()]))
    if falhas:
        partes.append("<h3>Falhas de leitura</h3><ul>" + "".join(f"<li>{esc(f)}</li>" for f in falhas) + "</ul>")
    partes.append(f'<footer>Gerado por geostudio-automacao/{VERSAO} a partir de {esc(caminho)}. Leitura direta do '
                  '.gsz, sem a API do GeoStudio. Confira os valores na interface antes de usar em projeto.</footer>')

    doc = (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f"<title>Auditoria {esc(caminho.stem)}</title><style>{CSS}</style></head>"
           f"<body><main>{''.join(partes)}</main></body></html>")
    destino = saida / "relatorio.html"
    destino.write_text(doc, encoding="utf-8")
    return destino, {"parecer": parecer, "contagem": cont, "fs_min": fs_min,
                     "metodos": [(a.nome, a.metodo, r.critica.fs) for a, r, _ in linhas_met], "achados": todos}


def gerar_comparacao(caminhos, fs_alvo=1.5, destino: Path | None = None):
    """Junta as análises SLOPE/W resolvidas de vários .gsz numa comparação só.

    Útil na licença de estudante, que aceita no máximo 2 análises por arquivo: cada método fica num
    arquivo e a comparação é feita aqui. Análises repetidas (mesmo método e mesmo FS) entram uma vez.
    """
    class Rotulo:                                    # análise com o nome do arquivo junto
        def __init__(self, a, arquivo):
            self.nome, self.metodo, self.id = f"{a.nome} ({arquivo})", a.metodo, a.id

    resultados, vistos, modelos, falhas = [], set(), [], []
    for caminho in caminhos:
        try:
            arq = ArquivoGSZ(caminho)
            modelos.append(ler_modelo(arq))
            for a in arq.analises:
                if "SLOPE" not in (a.tipo or "").upper() or not arq.tem_resultados(a):
                    continue
                r = ler_resultados(arq, a)
                if not r.critica:
                    continue
                chave = (a.metodo, round(r.critica.fs, 6))
                if chave in vistos:
                    continue
                vistos.add(chave)
                resultados.append((Rotulo(a, Path(caminho).name), r))
        except Exception as e:  # noqa: BLE001
            falhas.append(f"{Path(caminho).name}: {e}")
    if len(resultados) < 2:
        raise LookupError("Menos de duas análises SLOPE/W resolvidas para comparar." +
                          (" Falhas: " + "; ".join(falhas) if falhas else ""))
    linhas, achados = comparar_metodos(resultados)
    linhas.sort(key=lambda t: t[1].critica.fs)
    geometrias = {tuple(sorted(m.pontos.items())) for m in modelos}
    if len(geometrias) > 1:
        achados.append(("ALERTA", "Os arquivos não têm a mesma geometria: a comparação mistura modelos diferentes."))
    mats = {tuple(sorted((k, tuple(sorted(v.parametros.items()))) for k, v in m.materiais.items())) for m in modelos}
    if len(mats) > 1:
        achados.append(("ALERTA", "Os arquivos não têm os mesmos materiais: a comparação mistura modelos diferentes."))
    destino = destino or Path(caminhos[0]).with_name("comparacao_metodos.html")
    destino.parent.mkdir(parents=True, exist_ok=True)
    partes = [f"""<header><h1>Comparação de métodos</h1><div class="sub">{len(resultados)} análises de
{len(caminhos)} arquivo(s) · FS alvo {num(fs_alvo)} · {datetime.datetime.now():%d/%m/%Y %H:%M} · {VERSAO}</div></header>"""]
    partes.append(tabela(["Método", "Análise (arquivo)", "FS", "Δ do mínimo", "Superfície", "Centro (x; y)", "Raio",
                          "Entrada → saída", "λ"],
                         [(f"<b>{esc(nome_metodo(a.metodo))}</b>", esc(a.nome), f"<b>{num(r.critica.fs, 3)}</b>",
                           ("+" if d > 0 else "") + num(100 * d, 1) + " %", str(r.critica.numero),
                           f"{num(r.critica.centro_x)}; {num(r.critica.centro_y)}", num(r.critica.raio),
                           _entrada_saida_txt(r.critica),
                           num(r.critica.lambda_, 3) if any(k in (a.metodo or "").lower() for k in RIGOROSOS) else "–")
                          for a, r, d in linhas]))
    partes.append(lista_achados(achados))
    partes.append('<p class="nota">Rigorosos (equilíbrio de forças e de momentos): Morgenstern-Price, Spencer, GLE, '
                  'Sarma. Bishop simplificado: só momentos. Janbu simplificado: só forças horizontais. Fellenius '
                  '(Ordinário): ignora as forças entre fatias e costuma dar o menor FS.</p>')
    partes.append(img(figura_metodos(linhas, fs_alvo), "FS da superfície crítica por método"))
    partes.append(img(figura_sobreposta(modelos[0], linhas), "Superfícies críticas de cada método"))
    if falhas:
        partes.append("<h3>Falhas de leitura</h3><ul>" + "".join(f"<li>{esc(f)}</li>" for f in falhas) + "</ul>")
    partes.append(f'<footer>Arquivos: {esc(", ".join(Path(c).name for c in caminhos))}. Gerado por '
                  f'geostudio-automacao/{VERSAO}.</footer>')
    destino.write_text(f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
                       f'<meta name="viewport" content="width=device-width,initial-scale=1">'
                       f"<title>Comparação de métodos</title><style>{CSS}</style></head>"
                       f"<body><main>{''.join(partes)}</main></body></html>", encoding="utf-8")
    return destino, [(a.nome, a.metodo, r.critica.fs) for a, r, _ in linhas], achados


def _situacao(achados):
    if any(n == "ERRO" for n, _ in achados):
        return selo("ERRO")
    if any(n == "ALERTA" for n, _ in achados):
        return selo("ALERTA")
    return selo("OK")


def _entrada_saida_txt(c):
    e, s = c.entrada_saida()
    if e is None:
        return "–"
    return f"({num(e[0])}; {num(e[1])}) → ({num(s[0])}; {num(s[1])})"


DIRECOES = {"RightToLeft": "da direita para a esquerda", "LeftToRight": "da esquerda para a direita"}


def _linhas_busca(cfg):
    lin = []
    if cfg.get("entrada"):
        e = cfg["entrada"]
        lin.append(("Faixa de entrada (esquerda)", f"({num(e[0][0])}; {num(e[0][1])}) a ({num(e[1][0])}; {num(e[1][1])})"
                    if None not in e else "–"))
    if cfg.get("saida"):
        s = cfg["saida"]
        lin.append(("Faixa de saída (direita)", f"({num(s[0][0])}; {num(s[0][1])}) a ({num(s[1][0])}; {num(s[1][1])})"
                    if None not in s else "–"))
    if cfg.get("incrementos"):
        lin.append(("Incrementos (esquerda, direita)", f"{cfg['incrementos'][0]}, {cfg['incrementos'][1]}"))
    lin.append(("Direção do movimento", DIRECOES.get(cfg.get("direcao"), cfg.get("direcao") or "–")))
    lin.append(("Superfícies críticas guardadas", str(cfg.get("criticas_guardadas", "–"))))
    if cfg.get("volume_minimo") is not None:
        lin.append(("Volume mínimo", f"{num(cfg['volume_minimo'])} m³/m"))
    if cfg.get("limites"):
        lin.append(("Limites", ", ".join(f"{k} = {num(v)}" for k, v in cfg["limites"].items())))
    if cfg.get("lambdas"):
        lin.append(("Valores de λ", ", ".join(num(x, 1) for x in cfg["lambdas"])))
    return lin


# ----------------------------------------------------------------------- main
def perguntar_numero(texto, padrao):
    try:
        r = input(f"{texto} [Enter = {padrao}]: ").strip()
    except EOFError:
        return padrao
    try:
        return float(r.replace(",", ".")) if r else padrao
    except ValueError:
        print("  valor inválido, usando o padrão")
        return padrao


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gsz", nargs="*", type=Path, help=".gsz ou pasta com .gsz")
    ap.add_argument("--fs-alvo", type=float, help="FS mínimo para a verificação (padrão 1,5)")
    ap.add_argument("--saida", type=Path, help="pasta de saída (padrão: <nome>_auditoria ao lado do .gsz)")
    ap.add_argument("--nao-abrir", action="store_true", help="não abre o relatório no navegador")
    ap.add_argument("--sem-comparacao", action="store_true",
                    help="com vários arquivos, não gera a comparação de métodos entre eles")
    a = ap.parse_args(argv)

    arquivos = []
    for p in a.gsz:
        arquivos += sorted(p.glob("*.gsz")) if p.is_dir() else [p]
    interativo = not arquivos
    if interativo:
        arquivos = _modulo02().escolher_arquivos()
        if not arquivos:
            print("Nenhum arquivo escolhido.")
            return 1
    fs_alvo = a.fs_alvo if a.fs_alvo is not None else (perguntar_numero("FS alvo", 1.5) if interativo else 1.5)

    erros = 0
    if len(arquivos) > 1 and not a.sem_comparacao:
        try:
            destino, metodos, _ = gerar_comparacao(arquivos, fs_alvo, a.saida / "comparacao_metodos.html"
                                                   if a.saida else None)
            print("=" * 70)
            print("Comparação entre os arquivos:")
            for nome, metodo, f in metodos:
                print(f"    {nome_metodo(metodo):<28} FS = {f:.3f}  ({nome})")
            print(f"  Relatório: {destino}")
        except LookupError as e:
            print(f"  (sem comparação entre arquivos: {e})")
    for caminho in arquivos:
        print("=" * 70)
        print(caminho)
        try:
            pasta = (a.saida / Path(caminho).stem) if (a.saida and len(arquivos) > 1) else a.saida
            destino, r = gerar_relatorio(Path(caminho), fs_alvo, pasta)
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO: {e}")
            erros += 1
            continue
        c = r["contagem"]
        fs = f"{r['fs_min']:.3f}" if r["fs_min"] is not None else "–"
        print(f"  Parecer: {r['parecer']} · FS mínimo {fs} · {c['ERRO']} erro(s), {c['ALERTA']} alerta(s), "
              f"{c['INFO']} nota(s)")
        for nome, metodo, f in r["metodos"]:
            print(f"    {nome_metodo(metodo):<28} FS = {f:.3f}  ({nome})")
        for n, m in r["achados"]:
            if n != "INFO":
                print(f"    [{n}] {m}")
        print(f"  Relatório: {destino}")
        if interativo and not a.nao_abrir:
            import webbrowser
            webbrowser.open(destino.as_uri())
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
