#!/usr/bin/env python3
"""Procura a instalação do GeoStudio e o que a automação precisa (somente leitura).

Lista, para cada pasta do GeoStudio encontrada:
  - o pacote da API Python (gsi-*.whl) e o comando pip para instalar;
  - scripts de exemplo (.py) e definições da API (.proto), se houver;
  - o solver de linha de comando (GeoCmd.exe).
Grava tudo em procurar_instalacao.txt, ao lado deste script.

Uso:
    python procurar_instalacao.py                  # procura nas pastas de programas do Windows
    python procurar_instalacao.py "D:\\Programas"  # procura também numa pasta escolhida
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI / "procurar_instalacao.txt"
FABRICANTES = ("seequent", "geo-slope", "geoslope", "bentley", "geostudio")
MAX_EXEMPLOS = 200


def raizes_padrao():
    nomes = ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)", "ProgramData", "LOCALAPPDATA")
    vistos, saida = set(), []
    for n in nomes:
        p = os.environ.get(n)
        if p and Path(p).is_dir() and p.lower() not in vistos:
            vistos.add(p.lower())
            saida.append(Path(p))
    for p in (Path(r"C:\Program Files"), Path(r"C:\Program Files (x86)")):
        if p.is_dir() and str(p).lower() not in vistos:
            vistos.add(str(p).lower())
            saida.append(p)
    return saida


def pastas_geostudio(raiz: Path):
    """Pastas com 'GeoStudio' no nome até 2 níveis abaixo de uma pasta de fabricante (ou da raiz)."""
    achadas = []
    try:
        filhos = [p for p in raiz.iterdir() if p.is_dir()]
    except OSError:
        return achadas
    for p in filhos:
        nome = p.name.lower()
        if "geostudio" in nome:
            achadas.append(p)
        elif any(f in nome for f in FABRICANTES):
            try:
                achadas += [q for q in p.iterdir() if q.is_dir() and "geostudio" in q.name.lower()]
            except OSError:
                pass
    return achadas


def varrer(pasta: Path):
    rodas, exemplos, protos, geocmd = [], [], [], []
    for dirpath, _dirs, arquivos in os.walk(pasta):
        for a in arquivos:
            al = a.lower()
            caminho = Path(dirpath) / a
            if al.startswith("gsi") and al.endswith(".whl"):
                rodas.append(caminho)
            elif al.endswith(".py") and len(exemplos) < MAX_EXEMPLOS:
                exemplos.append(caminho)
            elif al.endswith(".proto"):
                protos.append(caminho)
            elif al == "geocmd.exe":
                geocmd.append(caminho)
    return rodas, exemplos, protos, geocmd


def main(argv):
    raizes = [Path(a) for a in argv] + raizes_padrao()
    linhas = []

    def sai(t=""):
        print(t)
        linhas.append(t)

    pastas = []
    for r in raizes:
        if Path(r).is_dir():
            if "geostudio" in Path(r).name.lower():
                pastas.append(Path(r))
            pastas += pastas_geostudio(Path(r))
    pastas = sorted(set(pastas))

    if not pastas:
        sai("Nenhuma pasta do GeoStudio encontrada em:")
        for r in raizes:
            sai(f"  {r}")
        sai("Rode de novo passando a pasta onde ele está instalado, por exemplo:")
        sai('  python procurar_instalacao.py "D:\\Programas"')
    for p in pastas:
        sai("=" * 70)
        sai(f"GeoStudio: {p}")
        sai("=" * 70)
        rodas, exemplos, protos, geocmd = varrer(p)
        sai(f"\nPacote da API (gsi-*.whl): {len(rodas)}")
        for w in rodas:
            sai(f"  {w}")
        if rodas:
            sai("\n  Para instalar no Python dos scripts:")
            sai(f'    pip install "{sorted(rodas)[-1]}"')
        sai(f"\nSolver de linha de comando (GeoCmd.exe): {len(geocmd)}")
        for g in geocmd:
            sai(f"  {g}")
        sai(f"\nDefinições da API (.proto): {len(protos)}")
        for x in protos:
            sai(f"  {x}")
        sai(f"\nScripts Python (.py), possíveis exemplos: {len(exemplos)}"
            + (f" (mostrando os {MAX_EXEMPLOS} primeiros)" if len(exemplos) >= MAX_EXEMPLOS else ""))
        for x in exemplos:
            sai(f"  {x}")
        sai()

    SAIDA.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"\nResumo gravado em {SAIDA}")
    return 0 if pastas else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
