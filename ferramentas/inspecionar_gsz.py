#!/usr/bin/env python3
"""Inspeciona arquivos .gsz do GeoStudio sem abrir o programa (somente leitura).

Para cada arquivo mostra: versão, seções do XML, árvore de análises (pai/filha) com tipo,
método e passos salvos, materiais com os parâmetros de resistência, e cada arquivo de
resultado com as colunas que ele traz. É a base para mapear o formato (docs/formato_gsz.md).

Grava <nome>_inspecao.txt e <nome>_inspecao.json ao lado de cada .gsz.

Uso:
    python inspecionar_gsz.py                       # escolhe o(s) arquivo(s) numa janela
    python inspecionar_gsz.py talude.gsz outro.gsz
    python inspecionar_gsz.py pasta_dos_modelos     # todos os .gsz da pasta
No Windows também dá para arrastar os .gsz em cima de inspecionar_gsz.bat.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modulos.comum.gsz import ArquivoGSZ  # noqa: E402

COLUNAS_MAX = 40


def escolher_arquivos():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return []
    raiz = tk.Tk()
    raiz.withdraw()
    nomes = filedialog.askopenfilenames(title="Escolha o(s) arquivo(s) do GeoStudio",
                                        filetypes=[("GeoStudio", "*.gsz"), ("Todos", "*.*")])
    raiz.destroy()
    return [Path(n) for n in nomes]


def expandir(args):
    saida = []
    for a in args:
        p = Path(a)
        saida += sorted(p.glob("*.gsz")) if p.is_dir() else [p]
    return saida


def inspecionar(caminho: Path):
    g = ArquivoGSZ(caminho)
    r = g.resumo()
    L = [f"Arquivo: {caminho}", f"XML do modelo: {g.xml_principal}   versão: {r['versao'] or '?'}",
         f"Seções do XML: {', '.join(g.secoes)}", f"Membros no zip: {len(g.membros)}", ""]

    L.append(f"Análises ({len(g.analises)}):")
    for nivel, a in g.arvore():
        passos = g.passos(a)
        estado = f"{len(passos)} passo(s) salvo(s)" if passos else "sem resultados"
        L.append(f"  {'   ' * nivel}[{a.id}] {a.nome}  ·  {a.tipo or '?'}  ·  {a.metodo or '?'}  ·  {estado}")
    L.append("")

    L.append(f"Materiais ({len(g.materiais)}):")
    for m in g.materiais:
        modelos = " / ".join(x for x in (m.modelo_slope, m.modelo_seep, m.modelo_sigma) if x) or "?"
        L.append(f"  [{m.id}] {m.nome}  ·  {modelos}")
        if m.resistencia:
            L.append("      " + ", ".join(f"{k}={v}" for k, v in m.resistencia.items()))
    L.append("")

    detalhes = {}
    for a in g.analises:
        arquivos = g.arquivos_resultado(a)
        if not arquivos:
            continue
        L.append(f"Resultados de '{a.nome}':")
        for membro in arquivos:
            if membro.lower().endswith(".csv"):
                try:
                    cab, linhas = g.ler_csv(membro)
                except Exception as e:  # noqa: BLE001
                    L.append(f"  {membro}  (erro ao ler: {e})")
                    continue
                detalhes[membro] = {"colunas": cab, "linhas": len(linhas)}
                extra = f" ... +{len(cab) - COLUNAS_MAX}" if len(cab) > COLUNAS_MAX else ""
                L.append(f"  {membro}  ({len(linhas)} linhas)")
                L.append(f"      colunas: {', '.join(cab[:COLUNAS_MAX])}{extra}")
            else:
                L.append(f"  {membro}")
        L.append("")

    outros = [m for m in g.membros
              if m != g.xml_principal and not any(m in g.arquivos_resultado(a) for a in g.analises)]
    if outros:
        L.append("Outros membros do zip:")
        L += [f"  {m}" for m in outros]

    r["arquivos_resultado"] = detalhes
    r["outros_membros"] = outros
    return "\n".join(L) + "\n", r


def main(argv):
    arquivos = expandir(argv) if argv else escolher_arquivos()
    if not arquivos:
        print(__doc__)
        return 1
    erros = 0
    for c in arquivos:
        print("=" * 70)
        try:
            txt, dados = inspecionar(c)
        except Exception as e:  # noqa: BLE001
            print(f"{c}: {e}")
            erros += 1
            continue
        print(txt)
        base = c.with_name(c.stem + "_inspecao")
        base.with_suffix(".txt").write_text(txt, encoding="utf-8")
        base.with_suffix(".json").write_text(json.dumps(dados, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
        print(f"Gravado: {base.with_suffix('.txt')} e .json")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
