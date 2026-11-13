"""Diagnóstico: a API do GeoStudio (gsi) consegue abrir este .gsz?  [não testado]

Somente leitura: o arquivo original não é alterado. Tenta abrir:
  1. o arquivo no caminho original;
  2. uma cópia num caminho só com letras sem acento (%TEMP%\\gsi_teste\\teste.gsz).
Se só a 2 funcionar, o problema é acento no caminho (ex.: "Integração").
Mostra a mensagem do GeoStudio mesmo quando ela vem em cp1252.

Uso:  python ferramentas\\teste_abrir_api.py arquivo.gsz
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modulos.comum.api import descrever_erro, importar_gsi  # noqa: E402


def tentar_abrir(gsi, caminho):
    print(f"\n--- Abrindo: {caminho}")
    print(f"    só ASCII no caminho: {'sim' if str(caminho).isascii() else 'NÃO'}")
    try:
        p = gsi.OpenProject(str(caminho))
    except Exception as e:  # noqa: BLE001
        print(f"    FALHOU: {descrever_erro(e)}")
        if isinstance(e, UnicodeDecodeError):
            print(f"    bytes brutos: {bytes(e.object)!r}")
        traceback.print_exc(limit=3)
        return False
    print("    ABRIU.")
    try:
        r = p.Get(gsi.GetRequest(analysis="Análise SLOPE/W", object="Materials[1].Name"))
        print(f"    Get Materials[1].Name -> {r.data}")
    except Exception as e:  # noqa: BLE001
        print(f"    (Get falhou: {descrever_erro(e)})")
    try:
        p.Close()
    except Exception as e:  # noqa: BLE001
        print(f"    (Close falhou: {descrever_erro(e)})")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gsz")
    a = ap.parse_args(argv)
    original = Path(a.gsz).resolve()
    gsi = importar_gsi()
    print(f"Python {sys.version.split()[0]}  |  modo UTF-8: {sys.flags.utf8_mode}  |  gsi em {Path(gsi.__file__).parent}")
    try:
        print(f"GeoStudio instalado: {gsi.interface.discover_installed_geostudio_versions()}")
    except Exception as e:  # noqa: BLE001
        print(f"(não listou as versões: {descrever_erro(e)})")
    print(f"GSI_BINARY_DIRECTORY_64 = {os.environ.get('GSI_BINARY_DIRECTORY_64')}")

    ok1 = tentar_abrir(gsi, original)

    pasta = Path(tempfile.gettempdir()) / "gsi_teste"
    if not str(pasta).isascii():
        pasta = Path("C:/gsi_teste")
    pasta.mkdir(parents=True, exist_ok=True)
    copia = pasta / "teste.gsz"
    shutil.copy2(original, copia)
    ok2 = tentar_abrir(gsi, copia)

    print("\n=== Conclusão")
    if ok1:
        print("A API abre o arquivo no caminho original. Licença de estudante OK para abrir.")
    elif ok2:
        print("Só abriu a cópia sem acento: o GeoStudio não aceita acento no caminho pela API.")
        print("Use uma pasta sem acento (ex.: C:\\Projetos\\GeoStudio) para os scripts da API.")
    else:
        print("Não abriu nem a cópia. Veja a mensagem do GeoStudio acima (licença? arquivo aberto"
              " na interface? serviço da API?).")
    return 0 if (ok1 or ok2) else 1


if __name__ == "__main__":
    sys.exit(main())
