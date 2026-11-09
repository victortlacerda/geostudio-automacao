#!/usr/bin/env python3
"""Levanta as tabelas de resultado de um projeto resolvido pela API (somente leitura).  [não testado]

Para cada análise: confere se há resultados, carrega e, para cada tabela relevante ao módulo
(SLOPE/W: Slip, CriticalSlip, Column, LambdaFOS...; SEEP/W e SIGMA/W: Nodes, Elements, Gauss,
BeamGauss, FlowPath...), lista os parâmetros disponíveis (QueryTableParamsInfo) com nome e
unidade e mostra os primeiros valores de cada um. É o mapa para escrever os módulos de resultado.

Não resolve nem altera o modelo. As análises vêm do próprio .gsz.
Grava <nome>_tabelas.csv e <nome>_tabelas.txt ao lado do .gsz.

Uso:
    python tabelas_resultados.py talude.gsz
    python tabelas_resultados.py talude.gsz --analise "Estabilidade" --amostra 10
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modulos.comum.api import Projeto, descrever_erro  # noqa: E402
from modulos.comum.gsz import ArquivoGSZ  # noqa: E402

TABELAS = {
    "slope": ["CriticalSlip", "Slip", "LambdaFOS", "Column", "Intercolumn", "Reinforcement",
              "Probabilistic", "Sample", "Iteration"],
    "seep": ["Nodes", "Elements", "Gauss", "FlowPath", "SavedTimeStep", "TimeStep", "History",
             "ResultGraphs"],
    "sigma": ["Nodes", "Elements", "Gauss", "BeamGauss", "ElementNodes", "SavedTimeStep", "TimeStep",
              "History", "ResultGraphs"],
}
# tabelas que exigem número de instância (superfície, gráfico...); tenta sem e, se falhar, com 1
COM_INSTANCIA = {"Column", "Intercolumn", "Reinforcement", "ResultGraphs", "LambdaFOS"}


def tabelas_para(tipo):
    t = (tipo or "").lower()
    for chave, lista in TABELAS.items():
        if chave in t:
            return lista
    vistas = []
    for lista in TABELAS.values():
        vistas += [x for x in lista if x not in vistas]
    return vistas


def levantar(p, analise, tabela, amostra):
    """Devolve (instancia, parametros, valores) da tabela; levanta erro se não der."""
    ultimo = None
    for inst in ([None, 1] if tabela in COM_INSTANCIA else [None]):
        try:
            params = p.parametros_tabela(analise, tabela, instancia=inst)
        except Exception as e:  # noqa: BLE001
            ultimo = e
            continue
        valores = {}
        if params and amostra > 0:
            try:
                valores = p.consultar(analise, tabela, [x["parametro"] for x in params], instancia=inst)
            except Exception as e:  # noqa: BLE001
                valores = {"_erro": descrever_erro(e)}
        return inst, params, valores
    raise ultimo


def formatar(v):
    return f"{v:.6g}" if isinstance(v, float) else str(v)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gsz", type=Path)
    ap.add_argument("--analise", action="append", help="nome da análise (pode repetir); padrão: todas")
    ap.add_argument("--amostra", type=int, default=5, help="quantos valores mostrar por parâmetro (0 = nenhum)")
    a = ap.parse_args(argv)

    arquivo = ArquivoGSZ(a.gsz)
    analises = [arquivo.analise(n) for n in a.analise] if a.analise else arquivo.analises
    linhas_csv, txt = [], [f"Projeto: {a.gsz}", ""]

    with Projeto(a.gsz) as p:
        for an in analises:
            txt.append("=" * 70)
            txt.append(f"{an.nome}  ·  {an.tipo or '?'}  ·  {an.metodo or '?'}")
            txt.append("=" * 70)
            try:
                if not p.tem_resultados(an.nome):
                    txt += ["  sem resultados: resolva a análise no GeoStudio e rode de novo", ""]
                    continue
            except Exception as e:  # noqa: BLE001
                txt += [f"  não consegui conferir os resultados: {descrever_erro(e)}", ""]
                continue
            for tabela in tabelas_para(an.tipo):
                try:
                    inst, params, valores = levantar(p, an.nome, tabela, a.amostra)
                except Exception as e:  # noqa: BLE001
                    txt.append(f"  {tabela}: indisponível ({descrever_erro(e)})")
                    continue
                rotulo = f"{tabela}" + (f" (instância {inst})" if inst is not None else "")
                txt.append(f"\n  {rotulo}: {len(params)} parâmetro(s)")
                if "_erro" in valores:
                    txt.append(f"    (valores não lidos: {valores['_erro']})")
                for x in params:
                    vals = valores.get(x["parametro"], [])
                    amostra = ", ".join(formatar(v) for v in vals[:a.amostra])
                    mais = f" ... ({len(vals)} valores)" if len(vals) > a.amostra else ""
                    txt.append(f"    {x['parametro']:<34} {x['nome']:<34} {x['unidade']:<10} {amostra}{mais}")
                    linhas_csv.append([an.nome, an.tipo, tabela, "" if inst is None else inst,
                                       x["parametro"], x["nome"], x["unidade"], x["categoria"], len(vals),
                                       " | ".join(formatar(v) for v in vals[:a.amostra])])
            txt.append("")

    base = a.gsz.with_name(a.gsz.stem + "_tabelas")
    with base.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["analise", "tipo", "tabela", "instancia", "parametro", "nome", "unidade",
                    "categoria", "n_valores", "amostra"])
        w.writerows(linhas_csv)
    texto = "\n".join(txt) + "\n"
    base.with_suffix(".txt").write_text(texto, encoding="utf-8")
    print(texto)
    print(f"Gravado: {base.with_suffix('.txt')} e .csv")
    return 0 if linhas_csv else 1


if __name__ == "__main__":
    sys.exit(main())
