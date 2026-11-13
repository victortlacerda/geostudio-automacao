#!/usr/bin/env python3
"""Módulo 02: resultados do SLOPE/W lidos do .gsz resolvido (sem abrir o GeoStudio, sem a API).

Para cada análise SLOPE/W do arquivo gera, numa pasta <nome>_resultados ao lado do .gsz:
  resultados_slope.xlsx   Resumo (FS, método, superfície crítica, checagens), Superfícies (todas,
                          válidas primeiro), Fatias e Entre fatias (das críticas guardadas) e Lambda x FS
  <análise>_critica.png   geometria + superfície crítica + demais críticas guardadas
  <análise>_fatias.png    tensões e resistências ao longo da base da superfície crítica
  <análise>_lambda.png    FS por força e por momento x lambda (Morgenstern-Price / Spencer)

Uso:
    python resultados_slope.py                          # escolhe o .gsz numa janela; pergunta o FS alvo
    python resultados_slope.py talude.gsz --fs-alvo 1.5
    python resultados_slope.py pasta_de_modelos         # todos os .gsz da pasta
No Windows também dá para arrastar o .gsz em cima de resultados_slope.bat.

Validado com docs/amostras_geostudio/slope/s00_talude5m.gsz (FS 1,786 igual ao da interface).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from modulos.comum.gsz import ArquivoGSZ  # noqa: E402
from modulos.comum.slope import CODIGOS, checagens, geometria, ler_resultados  # noqa: E402

VERSAO = "slope-v0.1"


def perguntar_numero(texto, padrao):
    try:
        r = input(f"{texto} [Enter = {padrao}]: ").strip()
    except EOFError:
        return padrao
    if not r:
        return padrao
    try:
        return float(r.replace(",", "."))
    except ValueError:
        print("  valor inválido, usando o padrão")
        return padrao


def escolher_arquivos():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return []
    raiz = tk.Tk()
    raiz.withdraw()
    nomes = filedialog.askopenfilenames(title="Escolha o(s) .gsz resolvido(s)",
                                        filetypes=[("GeoStudio", "*.gsz")])
    raiz.destroy()
    return [Path(n) for n in nomes]


def nome_arquivo(texto):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in texto).strip("_")


# ------------------------------------------------------------------- figuras
def figura_critica(res, pontos, regioes, destino):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=150)
    for reg in regioes:
        xy = [pontos[i] for i in reg if i in pontos]
        if xy:
            ax.add_patch(Polygon(xy, closed=True, facecolor="#f3e9c6", edgecolor="#555555", lw=1))
    detalhadas = res.com_detalhe()
    c = res.critica
    for s in detalhadas[1:]:
        b = s.base()
        ax.plot([p[0] for p in b], [p[1] for p in b], color="#9aa5b1", lw=1, zorder=2)
    if c and c.fatias:
        b = c.base()
        ax.plot([p[0] for p in b], [p[1] for p in b], color="#c0392b", lw=2.2, zorder=3,
                label=f"Crítica nº {c.numero}: FS = {c.fs:.3f}")
        for f in c.fatias:
            ax.plot([f["XLeft"], f["XLeft"]], [f["YBackBotLeft"], f["YBackTopLeft"]],
                    color="#c0392b", lw=0.4, alpha=0.6, zorder=2)
        if c.centro_x is not None:
            ax.plot(c.centro_x, c.centro_y, "o", color="#c0392b", ms=4, zorder=4)
            ax.plot([c.centro_x, b[0][0]], [c.centro_y, b[0][1]], color="#c0392b", lw=0.6, ls=":")
            ax.plot([c.centro_x, b[-1][0]], [c.centro_y, b[-1][1]], color="#c0392b", lw=0.6, ls=":")
    cfg = res.configuracao
    for faixa in (cfg.get("entrada"), cfg.get("saida")):
        if faixa and None not in faixa:
            ax.plot([faixa[0][0], faixa[1][0]], [faixa[0][1], faixa[1][1]], color="#2c6fbb", lw=4,
                    alpha=0.5, solid_capstyle="butt", zorder=4)
    if len(detalhadas) > 1:
        ax.plot([], [], color="#9aa5b1", lw=1, label=f"Outras {len(detalhadas) - 1} críticas guardadas")
    ax.plot([], [], color="#2c6fbb", lw=4, alpha=0.5, label="Faixas de entrada e saída")
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(f"{res.analise}  ·  {res.metodo}")
    ax.grid(True, lw=0.3, alpha=0.5)
    ax.legend(loc="lower right", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(destino)
    plt.close(fig)


def figura_fatias(c, destino):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = [f["X"] for f in c.fatias]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6.4), dpi=150, sharex=True)
    a1.plot(x, [f["NormalEffectiveStress"] for f in c.fatias], "o-", ms=3, label="Tensão normal efetiva")
    a1.plot(x, [f["PoreWaterPressure"] for f in c.fatias], "s-", ms=3, label="Poropressão")
    a1.set_ylabel("kPa")
    a1.legend(fontsize=8)
    a1.grid(True, lw=0.3)
    coes = [f["CohesiveStrength"] for f in c.fatias]
    atr = [f["FrictionalStrength"] for f in c.fatias]
    a2.plot(x, coes, "o-", ms=3, label="Parcela coesiva")
    a2.plot(x, atr, "^-", ms=3, label="Parcela de atrito")
    a2.plot(x, [a + b for a, b in zip(coes, atr)], "k-", lw=1.4, label="Resistência total")
    a2.set_ylabel("kPa")
    a2.set_xlabel("x no meio da fatia (m)")
    a2.legend(fontsize=8)
    a2.grid(True, lw=0.3)
    fig.suptitle(f"Superfície crítica nº {c.numero} · FS = {c.fs:.3f} · {len(c.fatias)} fatias")
    fig.tight_layout()
    fig.savefig(destino)
    plt.close(fig)


def figura_lambda(c, destino):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dados = sorted(c.lambda_fs, key=lambda d: d["LambdaX"])
    lam = [d["LambdaX"] for d in dados]
    fig, ax = plt.subplots(figsize=(7, 4.4), dpi=150)
    ax.plot(lam, [d["FOSByMoment"] for d in dados], "o-", label="FS por momento")
    ax.plot(lam, [d["FOSByForce"] for d in dados], "s-", label="FS por força")
    if c.lambda_ is not None:
        ax.axvline(c.lambda_, color="#c0392b", ls="--", lw=1)
        ax.annotate(f"λ = {c.lambda_:.3f}\nFS = {c.fs:.3f}", (c.lambda_, c.fs), textcoords="offset points",
                    xytext=(8, -28), fontsize=8, color="#c0392b")
    ax.set_xlabel("λ")
    ax.set_ylabel("FS")
    ax.set_title(f"Superfície crítica nº {c.numero}: FS x λ")
    ax.grid(True, lw=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(destino)
    plt.close(fig)


# ------------------------------------------------------------------- planilha
def planilha(resultados, arquivo, fs_alvo, destino, figuras):
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as ImagemXL
    from openpyxl.styles import Font, PatternFill

    negrito = Font(bold=True)
    cab_cor = PatternFill("solid", fgColor="DDE6F0")

    def tabela(ws, cabecalho, linhas, linha0=1):
        for j, h in enumerate(cabecalho, start=1):
            c = ws.cell(row=linha0, column=j, value=h)
            c.font, c.fill = negrito, cab_cor
        for i, lin in enumerate(linhas, start=linha0 + 1):
            for j, v in enumerate(lin, start=1):
                ws.cell(row=i, column=j, value=v)
        for j, h in enumerate(cabecalho, start=1):
            ws.column_dimensions[ws.cell(row=linha0, column=j).column_letter].width = max(11, len(str(h)) + 2)

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumo"
    ws["A1"], ws["A1"].font = f"Resultados SLOPE/W · {arquivo.caminho.name}", Font(bold=True, size=13)
    ws["A2"] = f"GeoStudio {arquivo.info.get('AppVersion', '?')} · gerado por geostudio-automacao {VERSAO}"
    linhas = []
    for res, avisos in resultados:
        c = res.critica
        ent, sai = c.entrada_saida() if c and c.fatias else (None, None)
        linhas.append([
            res.analise, res.metodo, c.numero if c else None, round(c.fs, 4) if c else None,
            fs_alvo, ("OK" if c and c.fs >= fs_alvo else "NÃO ATENDE") if c else "sem superfície válida",
            c.centro_x if c else None, c.centro_y if c else None, c.raio if c else None,
            ent[0] if ent else None, sai[0] if sai else None, c.lambda_ if c else None,
            len(res.validas), len(res.superficies) - len(res.validas),
            " | ".join(f"{n}: {m}" for n, m in avisos) or "sem avisos"])
    tabela(ws, ["Análise", "Método", "Superfície crítica", "FS", "FS alvo", "Verificação", "Centro x (m)",
                "Centro y (m)", "Raio (m)", "x entrada (m)", "x saída (m)", "λ", "Válidas", "Inválidas",
                "Checagens"], linhas, linha0=4)
    ws.column_dimensions["O"].width = 90

    ws2 = wb.create_sheet("Superfícies")
    lin = []
    for res, _ in resultados:
        for s in res.validas + [s for s in res.superficies if not s.valida]:
            lin.append([res.analise, s.numero, s.fs, s.codigo,
                        CODIGOS.get(s.codigo, f"código {s.codigo}") if s.codigo else "",
                        s.centro_x, s.centro_y, s.raio, s.volume, s.peso, s.lambda_])
    tabela(ws2, ["Análise", "Superfície", "FS", "Código", "Motivo da invalidade", "Centro x (m)",
                 "Centro y (m)", "Raio (m)", "Volume (m³/m)", "Peso (kN/m)", "λ"], lin)

    ws3 = wb.create_sheet("Fatias")
    cols = ["ColumnNum", "X", "XLeft", "XRight", "ColumnWidth", "BotAlphaX", "ColumnWeight",
            "PoreWaterPressure", "NormalEffectiveStress", "CohesiveStrength", "FrictionalStrength",
            "ResistingForceX", "ActivatingForceX", "ReinforcementForceX", "SurchargeForceY"]
    nomes = ["Fatia", "x meio (m)", "x esq (m)", "x dir (m)", "Largura (m)", "Ângulo base (rad)",
             "Peso (kN/m)", "Poropressão (kPa)", "σ' normal (kPa)", "Coesiva (kPa)", "Atrito (kPa)",
             "Força resistente (kN/m)", "Força atuante (kN/m)", "Reforço x (kN/m)", "Sobrecarga y (kN/m)"]
    lin = []
    for res, _ in resultados:
        for s in res.com_detalhe():
            for f in s.fatias:
                lin.append([res.analise, s.numero, round(s.fs, 4)] + [f.get(k) for k in cols])
    tabela(ws3, ["Análise", "Superfície", "FS"] + nomes, lin)

    ws4 = wb.create_sheet("Entre fatias")
    lin = []
    for res, _ in resultados:
        for s in res.com_detalhe():
            for f in s.entre_fatias:
                lin.append([res.analise, s.numero, f.get("IntercolumnNum"), f.get("XZCoord"), f.get("Y"),
                            f.get("IntercolumnNormalForce"), f.get("IntercolumnVerticalShearForce")])
    tabela(ws4, ["Análise", "Superfície", "Nº", "x (m)", "y (m)", "Normal E (kN/m)", "Cisalhante X (kN/m)"], lin)

    ws5 = wb.create_sheet("Lambda x FS")
    lin = []
    for res, _ in resultados:
        for s in res.com_detalhe():
            for d in s.lambda_fs:
                lin.append([res.analise, s.numero, d.get("LambdaX"), d.get("FOSByForce"), d.get("FOSByMoment")])
    tabela(ws5, ["Análise", "Superfície", "λ", "FS força", "FS momento"], lin)

    wsf = wb.create_sheet("Figuras")
    linha = 1
    for titulo, caminho in figuras:
        wsf.cell(row=linha, column=1, value=titulo).font = negrito
        img = ImagemXL(str(caminho))
        img.width, img.height = img.width * 0.45, img.height * 0.45
        wsf.add_image(img, f"A{linha + 1}")
        linha += int(img.height / 20) + 4
    wb.save(destino)


# ----------------------------------------------------------------------- main
def processar(caminho: Path, fs_alvo: float, pasta_saida: Path | None = None):
    arquivo = ArquivoGSZ(caminho)
    analises = [a for a in arquivo.analises if "SLOPE" in (a.tipo or "").upper()]
    if not analises:
        raise ValueError(f"{caminho.name}: nenhuma análise SLOPE/W.")
    saida = pasta_saida or caminho.with_name(caminho.stem + "_resultados")
    saida.mkdir(parents=True, exist_ok=True)
    resultados, figuras, faltando = [], [], []
    for a in analises:
        try:
            res = ler_resultados(arquivo, a)
        except LookupError as e:
            faltando.append(str(e))
            continue
        avisos = checagens(res, fs_alvo)
        resultados.append((res, avisos))
        base = saida / nome_arquivo(a.nome)
        pontos, regioes = geometria(arquivo, a.geometria_id or "1")
        figura_critica(res, pontos, regioes, f"{base}_critica.png")
        figuras.append((f"{a.nome}: superfície crítica", f"{base}_critica.png"))
        c = res.critica
        if c and c.fatias:
            figura_fatias(c, f"{base}_fatias.png")
            figuras.append((f"{a.nome}: fatias da crítica", f"{base}_fatias.png"))
        if c and c.lambda_fs:
            figura_lambda(c, f"{base}_lambda.png")
            figuras.append((f"{a.nome}: FS x λ", f"{base}_lambda.png"))
    if not resultados:
        raise LookupError("\n".join(faltando))
    planilha(resultados, arquivo, fs_alvo, saida / "resultados_slope.xlsx", figuras)
    return saida, resultados, faltando


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gsz", nargs="*", type=Path, help=".gsz resolvido(s) ou pasta")
    ap.add_argument("--fs-alvo", type=float, help="FS mínimo para a verificação (padrão 1,5)")
    ap.add_argument("--saida", type=Path, help="pasta de saída (padrão: <nome>_resultados ao lado do .gsz)")
    a = ap.parse_args(argv)

    arquivos = []
    for p in a.gsz:
        arquivos += sorted(p.glob("*.gsz")) if p.is_dir() else [p]
    interativo = not arquivos
    if interativo:
        arquivos = escolher_arquivos()
        if not arquivos:
            print("Nenhum arquivo escolhido.")
            return 1
    fs_alvo = a.fs_alvo if a.fs_alvo is not None else (perguntar_numero("FS alvo", 1.5) if interativo else 1.5)

    erros = 0
    for caminho in arquivos:
        print("=" * 70)
        print(caminho)
        try:
            saida, resultados, faltando = processar(caminho, fs_alvo, a.saida)
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO: {e}")
            erros += 1
            continue
        for res, avisos in resultados:
            c = res.critica
            if c:
                print(f"  {res.analise}: FS = {c.fs:.3f} ({res.metodo}, superfície {c.numero}) "
                      f"→ {'OK' if c.fs >= fs_alvo else 'NÃO ATENDE'} ao alvo {fs_alvo:.2f}")
            for nivel, msg in avisos:
                print(f"    [{nivel}] {msg}")
        for f in faltando:
            print(f"  (sem resultados) {f}")
        print(f"  Saída: {saida}")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
