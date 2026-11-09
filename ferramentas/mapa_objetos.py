#!/usr/bin/env python3
"""Mapa de objetos de um projeto pela API do GeoStudio (somente leitura).  [não testado]

Abre o projeto pela API, e para cada análise pede os objetos a partir de uma ou mais raízes
(padrão: CurrentAnalysis.Objects e CurrentAnalysis). A resposta é achatada em linhas
caminho · valor · unidade e gravada em <nome>_mapa_objetos.csv ao lado do .gsz.

Não grava nada no modelo. As análises vêm do próprio .gsz (leitura direta do arquivo).
Se uma raiz não puder ser lida inteira, o erro vai para o log e o script segue (regra do
plaxis3d-automacao: não abortar na primeira falha). Nesse caso, passe caminhos mais
específicos com --caminho, copiados de Sketch → Text → Insert Field no GeoStudio.

Uso:
    python mapa_objetos.py talude.gsz
    python mapa_objetos.py talude.gsz --analise "Estabilidade"
    python mapa_objetos.py talude.gsz --caminho 'CurrentAnalysis.Objects.Materials["Argila"]'
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modulos.comum.api import Projeto, achatar  # noqa: E402
from modulos.comum.gsz import ArquivoGSZ  # noqa: E402

RAIZES_PADRAO = ["CurrentAnalysis.Objects", "CurrentAnalysis"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gsz", type=Path)
    ap.add_argument("--analise", action="append", help="nome da análise (pode repetir); padrão: todas")
    ap.add_argument("--caminho", action="append", help="caminho de objeto a ler (pode repetir)")
    a = ap.parse_args(argv)

    arquivo = ArquivoGSZ(a.gsz)
    analises = a.analise or [x.nome for x in arquivo.analises]
    raizes = a.caminho or RAIZES_PADRAO
    saida = a.gsz.with_name(a.gsz.stem + "_mapa_objetos.csv")
    log = a.gsz.with_name(a.gsz.stem + "_mapa_objetos_log.txt")
    linhas, falhas = [], []

    with Projeto(a.gsz) as p:
        for nome in analises:
            for raiz in raizes:
                try:
                    dado = p.ler(nome, raiz)
                except Exception as e:  # noqa: BLE001
                    falhas.append(f"{nome} · {raiz}: {e}")
                    print(f"  (falhou) {nome} · {raiz}")
                    continue
                novas = achatar(dado, raiz)
                linhas += [(nome, c, v, u) for c, v, u in novas]
                print(f"  {nome} · {raiz}: {len(novas)} valores")

    with saida.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["analise", "caminho", "valor", "unidade"])
        w.writerows(linhas)
    log.write_text("\n".join(falhas) + "\n" if falhas else "sem falhas\n", encoding="utf-8")
    print(f"\n{len(linhas)} valores em {saida}")
    print(f"{len(falhas)} leitura(s) com falha; detalhes em {log}")
    return 0 if linhas else 1


if __name__ == "__main__":
    sys.exit(main())
