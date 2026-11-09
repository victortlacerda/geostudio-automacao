"""Conexão com o GeoStudio 2026.1 pela API Python oficial (pacote `gsi`, via gRPC).

[não testado] Os nomes de métodos e campos abaixo vêm dos fóruns da Seequent (versões 2025) e
precisam ser confirmados com `ferramentas/diagnostico_gsi.py` e os exemplos da instalação.
Cada ponto incerto passa por `tentar(...)`, que aceita alternativas e relata o que falhou,
como no plaxis3d-automacao. Toda gravação é conferida lendo o valor de volta.
"""
from __future__ import annotations

from pathlib import Path


def importar_gsi():
    try:
        import gsi  # noqa: F401
        return gsi
    except ImportError:
        raise SystemExit(
            "O pacote 'gsi' do GeoStudio não está instalado neste Python.\n"
            "1. Rode  ferramentas\\procurar_instalacao.bat  para achar o arquivo gsi-*.whl;\n"
            "2. Instale com  pip install \"<caminho>\\gsi-....whl\"  no mesmo Python dos scripts."
        )


def tentar(descricao, *alternativas):
    """Executa a primeira alternativa que funcionar; se todas falharem, lista os erros."""
    erros = []
    for i, f in enumerate(alternativas):
        try:
            r = f()
            if i > 0:
                print(f"    (aviso) '{descricao}' funcionou pela alternativa {i + 1}")
            return r
        except Exception as e:  # noqa: BLE001
            msg = str(e).strip().splitlines()
            erros.append(f"alt {i + 1}: {type(e).__name__}: {msg[-1] if msg else ''}")
    raise RuntimeError(f"Falhou: {descricao}\n    " + "\n    ".join(erros))


def para_python(resposta):
    """Converte uma resposta protobuf em dict/list/valor Python (ou devolve como veio)."""
    try:
        from google.protobuf.json_format import MessageToDict
        from google.protobuf.message import Message
        if isinstance(resposta, Message):
            return MessageToDict(resposta, preserving_proto_field_name=True)
    except ImportError:
        pass
    return resposta


def achatar(dado, prefixo=""):
    """Transforma uma árvore dict/list em linhas (caminho, valor, unidade).

    Um dicionário com 'Value' (e opcionalmente 'Units') vira uma linha só, que é o formato dos
    valores da API: {"Value": 1.0, "Units": "kPa"}.
    """
    linhas = []
    if isinstance(dado, dict):
        if "Value" in dado and set(dado) <= {"Value", "Units"}:
            return [(prefixo, dado.get("Value"), dado.get("Units", ""))]
        for k, v in dado.items():
            linhas += achatar(v, f"{prefixo}.{k}" if prefixo else str(k))
    elif isinstance(dado, list):
        for i, v in enumerate(dado):
            linhas += achatar(v, f"{prefixo}[{i}]")
    else:
        linhas.append((prefixo, dado, ""))
    return linhas


class Projeto:
    """Projeto aberto pela API.  Uso:

        with Projeto("talude.gsz") as p:
            c = p.ler("Estabilidade", 'CurrentAnalysis.Objects.Materials["Argila"].Slope.CohesionPrime')
    """

    def __init__(self, caminho):
        self.gsi = importar_gsi()
        self.caminho = Path(caminho).resolve()
        if not self.caminho.is_file():
            raise FileNotFoundError(self.caminho)
        g = self.gsi
        self.p = tentar("abrir o projeto",
                        lambda: g.OpenProject(str(self.caminho)),
                        lambda: g.Project(str(self.caminho)))

    # leitura -----------------------------------------------------------
    def ler_bruto(self, analise, objeto):
        g = self.gsi
        return tentar(f"ler {objeto}",
                      lambda: self.p.Get(g.GetRequest(analysis=analise, object=objeto)))

    def ler(self, analise, objeto):
        resp = para_python(self.ler_bruto(analise, objeto))
        if isinstance(resp, dict) and "data" in resp:
            return resp["data"]
        return resp

    # gravação ----------------------------------------------------------
    def gravar(self, analise, objeto, valor, unidade, conferir=True):
        """Grava {"Value": valor, "Units": unidade} e, por padrão, confere lendo de volta."""
        from google.protobuf import struct_pb2
        g = self.gsi
        dado = struct_pb2.Value()
        dado.struct_value.update({"Value": valor, "Units": unidade})
        tentar(f"gravar {objeto}",
               lambda: self.p.Set(g.SetRequest(analysis=analise, object=objeto, data=dado)))
        if conferir:
            lido = self.ler(analise, objeto)
            v = lido.get("Value") if isinstance(lido, dict) else lido
            if v is None or abs(float(v) - float(valor)) > 1e-9 * max(1.0, abs(float(valor))):
                raise RuntimeError(f"{objeto}: gravei {valor} {unidade} mas li {lido!r}. "
                                   "A gravação não teve efeito.")
        return True

    # cálculo ------------------------------------------------------------
    def resolver(self, analises):
        g = self.gsi
        nomes = [analises] if isinstance(analises, str) else list(analises)
        return tentar("resolver " + ", ".join(nomes),
                      lambda: self.p.SolveAnalyses(g.SolveAnalysesRequest(analyses=nomes)))

    def salvar(self):
        return tentar("salvar o projeto", lambda: self.p.Save())

    def fechar(self):
        try:
            self.p.Close()
        except Exception:  # noqa: BLE001
            pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.fechar()
