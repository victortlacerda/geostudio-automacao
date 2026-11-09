#!/usr/bin/env python3
"""Diagnóstico da API Python do GeoStudio (pacote `gsi`), somente leitura.

Não abre modelo nem altera nada: só importa o pacote e descreve o que ele oferece.
É o equivalente, para o GeoStudio, de pedir o histórico de comandos no PLAXIS: com ele os
nomes reais de funções, pedidos (Requests), campos e enumerações ficam conhecidos antes de
escrever os módulos.

Grava, ao lado deste script:
  diagnostico_gsi.txt   leitura humana
  diagnostico_gsi.json  o mesmo em JSON (para comparar versões e para o Claude ler)

Uso:
    python diagnostico_gsi.py
"""
from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def eh_mensagem_protobuf(obj):
    d = getattr(obj, "DESCRIPTOR", None)
    return inspect.isclass(obj) and d is not None and hasattr(d, "fields")


def eh_enum_protobuf(obj):
    d = getattr(obj, "DESCRIPTOR", None)
    return (not inspect.isclass(obj)) and d is not None and hasattr(d, "values") and hasattr(obj, "keys")


def descrever_mensagem(cls):
    campos = []
    for f in cls.DESCRIPTOR.fields:
        tipo = f.message_type.full_name if f.message_type else (
            f.enum_type.full_name if f.enum_type else str(f.type))
        repetido = getattr(f, "label", None) == 3 or getattr(f, "is_repeated", False)
        campos.append({"nome": f.name, "tipo": tipo, "repetido": bool(repetido)})
    return {"tipo": "mensagem", "nome_completo": cls.DESCRIPTOR.full_name, "campos": campos}


def descrever_enum(obj):
    return {"tipo": "enum", "nome_completo": obj.DESCRIPTOR.full_name,
            "valores": {v.name: v.number for v in obj.DESCRIPTOR.values}}


def assinatura(obj):
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return "(?)"


def primeira_linha(obj):
    doc = inspect.getdoc(obj) or ""
    return doc.strip().splitlines()[0] if doc.strip() else ""


def descrever(nome, obj):
    if eh_mensagem_protobuf(obj):
        return descrever_mensagem(obj)
    if eh_enum_protobuf(obj):
        return descrever_enum(obj)
    if inspect.ismodule(obj):
        return {"tipo": "módulo", "arquivo": getattr(obj, "__file__", "")}
    if inspect.isclass(obj):
        metodos = {}
        for n, m in inspect.getmembers(obj):
            if n.startswith("_") or not callable(m):
                continue
            metodos[n] = {"assinatura": assinatura(m), "doc": primeira_linha(m)}
        return {"tipo": "classe", "doc": primeira_linha(obj), "metodos": metodos}
    if callable(obj):
        return {"tipo": "função", "assinatura": assinatura(obj), "doc": primeira_linha(obj)}
    return {"tipo": type(obj).__name__, "valor": repr(obj)[:200]}


def membros_publicos(mod):
    return {n: getattr(mod, n) for n in dir(mod) if not n.startswith("_")}


def diagnosticar(gsi):
    info = {
        "python": sys.version.split()[0],
        "pacote": getattr(gsi, "__name__", "gsi"),
        "versao": getattr(gsi, "__version__", None),
        "arquivo": getattr(gsi, "__file__", None),
        "submodulos": {},
        "nomes": {},
    }
    for n, obj in membros_publicos(gsi).items():
        try:
            info["nomes"][n] = descrever(n, obj)
        except Exception as e:  # noqa: BLE001
            info["nomes"][n] = {"tipo": "erro", "erro": repr(e)}

    caminho = getattr(gsi, "__path__", None)
    if caminho:
        for sub in pkgutil.walk_packages(caminho, prefix=gsi.__name__ + "."):
            try:
                m = importlib.import_module(sub.name)
            except Exception as e:  # noqa: BLE001
                info["submodulos"][sub.name] = {"erro": repr(e)}
                continue
            info["submodulos"][sub.name] = {
                n: descrever(n, o) for n, o in membros_publicos(m).items()
                if getattr(o, "__module__", sub.name) == sub.name or eh_enum_protobuf(o)
            }
        pasta = Path(gsi.__file__).parent
        info["arquivos_do_pacote"] = sorted(
            str(p.relative_to(pasta)) for p in pasta.rglob("*")
            if p.is_file() and p.suffix.lower() in {".py", ".pyi", ".proto", ".md", ".txt", ".json"})
    return info


def texto(info):
    L = [f"Pacote: {info['pacote']}  versão: {info['versao']}  Python: {info['python']}",
         f"Arquivo: {info['arquivo']}", ""]

    def bloco(titulo, nomes):
        L.append("=" * 70)
        L.append(titulo)
        L.append("=" * 70)
        grupos = {}
        for n, d in sorted(nomes.items()):
            grupos.setdefault(d.get("tipo", "?"), []).append((n, d))
        for tipo in ("função", "classe", "mensagem", "enum", "módulo"):
            for n, d in grupos.pop(tipo, []):
                if tipo == "função":
                    L.append(f"função   {n}{d['assinatura']}  {d['doc']}")
                elif tipo == "classe":
                    L.append(f"classe   {n}  {d['doc']}")
                    for m, md in d["metodos"].items():
                        L.append(f"           .{m}{md['assinatura']}  {md['doc']}")
                elif tipo == "mensagem":
                    campos = ", ".join(f"{c['nome']}:{c['tipo']}{'[]' if c['repetido'] else ''}"
                                       for c in d["campos"])
                    L.append(f"mensagem {n}({campos})")
                elif tipo == "enum":
                    L.append(f"enum     {n} = {', '.join(d['valores'])}")
                else:
                    L.append(f"módulo   {n}")
        for tipo, itens in grupos.items():
            for n, d in itens:
                L.append(f"{tipo:<8} {n}  {d.get('valor', d.get('erro', ''))}")
        L.append("")

    bloco("Nomes no topo do pacote", info["nomes"])
    for sub, nomes in info["submodulos"].items():
        if isinstance(nomes, dict) and "erro" not in nomes and nomes:
            bloco(f"Submódulo {sub}", nomes)
    if info.get("arquivos_do_pacote"):
        L.append("Arquivos do pacote (.py/.pyi/.proto/.md):")
        L += [f"  {a}" for a in info["arquivos_do_pacote"]]
    return "\n".join(L) + "\n"


def main():
    try:
        import gsi
    except ImportError:
        print("O pacote 'gsi' não está instalado neste Python:", sys.executable)
        print("Rode procurar_instalacao.bat, instale o gsi-*.whl indicado e rode este diagnóstico de novo.")
        return 1
    info = diagnosticar(gsi)
    txt = texto(info)
    print(txt)
    (AQUI / "diagnostico_gsi.txt").write_text(txt, encoding="utf-8")
    (AQUI / "diagnostico_gsi.json").write_text(json.dumps(info, ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    print(f"Gravado: {AQUI / 'diagnostico_gsi.txt'} e .json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
