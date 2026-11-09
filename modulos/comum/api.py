"""Conexão com o GeoStudio pela API Python oficial (pacote `gsi`, via gRPC).

Nomes conferidos na documentação oficial da 2026.1 (gsi_project.proto, Scripting API Documentation,
DataParam Types), que fica na pasta API da instalação. Resumo em docs/api_gsi.md.

Pontos da API que este módulo trata:
  - caminhos de objetos: 'Materials["Argila"].UnitWeight', 'CurrentAnalysis.GeometryItems.Regions[1]';
    índices começam em 1;
  - Get devolve GetResponse.data (google.protobuf.Value); Set recebe gsi.Value;
  - valor com unidade: struct {"Value": x, "Units": "kPa"} é convertido para as unidades da análise;
    sem "Units" (ou number_value) já está nas unidades da análise; adimensional nunca leva unidade;
  - SolveAnalyses devolve all_succeeded e completion_status[nome].error_message;
  - resultados: LoadResults antes de QueryResults; QueryResults devolve results[int(DataParam)].values;
  - QueryTableParamsInfo lista os parâmetros disponíveis numa tabela de resultado;
  - SolveAnalyses SALVA o projeto antes de resolver: paramétricos devem trabalhar numa cópia.

[não testado] no GeoStudio real até a primeira rodada do usuário; os testes usam uma API falsa.
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
            "Instale com o requirements.txt da pasta API do GeoStudio (Python 3.12):\n"
            '  pip install -r "C:\\Program Files\\Seequent\\GeoStudio 2026.1\\API\\requirements.txt"\n'
            "(no menu Iniciar: 'GeoStudio 2026.1.0 API Folder' abre essa pasta)."
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
            erros.append(f"alt {i + 1}: {descrever_erro(e)}")
    raise RuntimeError(f"Falhou: {descricao}\n    " + "\n    ".join(erros))


def descrever_erro(e):
    """Mensagem curta de um erro, inclusive de gRPC (que traz o detalhe em .details())."""
    detalhe = None
    if hasattr(e, "details") and callable(e.details):
        try:
            detalhe = e.details()
        except Exception:  # noqa: BLE001
            detalhe = None
    msg = detalhe or str(e).strip().splitlines()[-1:] or [""]
    if isinstance(msg, list):
        msg = msg[0] if msg else ""
    return f"{type(e).__name__}: {msg}"


def para_python(valor):
    """google.protobuf.Value (ou outra mensagem) -> dict/list/float/str/bool do Python."""
    try:
        from google.protobuf.json_format import MessageToDict
        from google.protobuf.message import Message
        if isinstance(valor, Message):
            return MessageToDict(valor, preserving_proto_field_name=True)
    except ImportError:
        pass
    return valor


def achatar(dado, prefixo=""):
    """Árvore dict/list -> linhas (caminho, valor, unidade), no formato de caminho da API.

    {"Value": 18, "Units": "kN/m³"} vira uma linha só. Listas usam índice a partir de 1,
    como nos caminhos do GeoStudio (Regions[1]).
    """
    linhas = []
    if isinstance(dado, dict):
        if "Value" in dado and set(dado) <= {"Value", "Units"}:
            return [(prefixo, dado.get("Value"), dado.get("Units", ""))]
        for k, v in dado.items():
            linhas += achatar(v, f"{prefixo}.{k}" if prefixo else str(k))
    elif isinstance(dado, list):
        for i, v in enumerate(dado, start=1):
            linhas += achatar(v, f"{prefixo}[{i}]")
    else:
        linhas.append((prefixo, dado, ""))
    return linhas


def valor_numerico(lido):
    """Número de uma leitura: 18.0 ou {"Value": 18.0, "Units": ...} -> 18.0; senão None."""
    if isinstance(lido, dict):
        lido = lido.get("Value")
    if isinstance(lido, bool):
        return None
    try:
        return float(lido)
    except (TypeError, ValueError):
        return None


def enum(tipo, nome_ou_valor):
    """Converte 'eRawSlipFOS' (ou o próprio valor) no valor do enum da API."""
    if isinstance(nome_ou_valor, str):
        try:
            return getattr(tipo, nome_ou_valor)
        except AttributeError:
            pass
        if hasattr(tipo, "Value"):
            return tipo.Value(nome_ou_valor)
        raise KeyError(f"'{nome_ou_valor}' não existe em {getattr(tipo, '__name__', tipo)}")
    return nome_ou_valor


def nome_enum(tipo, valor):
    """Nome de um valor de enum ('eRawSlipFOS'), ou o número como texto se não achar."""
    if hasattr(tipo, "Name"):
        try:
            return tipo.Name(int(valor))
        except Exception:  # noqa: BLE001
            pass
    if hasattr(valor, "name"):
        return valor.name
    for n in dir(tipo):
        if not n.startswith("_") and getattr(tipo, n) == valor:
            return n
    return str(valor)


class Projeto:
    """Projeto aberto pela API.  Uso:

        with Projeto(r"C:\\modelos\\talude.gsz") as p:
            gama = p.ler("Estabilidade", 'Materials["Argila"].UnitWeight')
            p.gravar("Estabilidade", 'Materials["Argila"].UnitWeight', 19.0)
            p.resolver("Estabilidade")
            p.carregar_resultados("Estabilidade")
            fs = p.consultar("Estabilidade", "CriticalSlip", ["eRawSlipFOS"])
    """

    def __init__(self, caminho, versao=None):
        self.gsi = importar_gsi()
        self.caminho = Path(caminho).resolve()
        if self.caminho.suffix.lower() != ".gsz" or not self.caminho.is_file():
            raise FileNotFoundError(f"Projeto .gsz não encontrado: {self.caminho}")
        if versao:
            self.gsi.set_target_version(str(versao))
        self.p = tentar("abrir o projeto", lambda: self.gsi.OpenProject(str(self.caminho)))
        self._carregadas = set()

    # ------------------------------------------------------------ objetos
    def ler_bruto(self, analise, objeto):
        g = self.gsi
        return tentar(f"ler {objeto}", lambda: self.p.Get(g.GetRequest(analysis=analise, object=objeto)))

    def ler(self, analise, objeto):
        """Valor de um objeto ou propriedade, já em tipos do Python."""
        return para_python(self.ler_bruto(analise, objeto).data)

    def _montar(self, valor, unidade=None):
        """gsi.Value para gravar: número, texto, booleano ou número com unidade."""
        g = self.gsi
        if isinstance(valor, bool):
            return g.Value(bool_value=valor)
        if isinstance(valor, str):
            return g.Value(string_value=valor)
        if unidade:
            v = g.Value()
            v.struct_value.update({"Value": float(valor), "Units": unidade})
            return v
        return g.Value(number_value=float(valor))

    def gravar(self, analise, objeto, valor, unidade=None, conferir=True):
        """Grava um valor e, por padrão, confere lendo de volta.

        Sem unidade, o valor está nas unidades da análise e a leitura tem que bater.
        Com unidade, o GeoStudio converte; a conferência só exige que o valor tenha mudado
        (ou que bata, se as unidades forem as mesmas). Devolve o valor lido depois de gravar.
        """
        g = self.gsi
        antes = self.ler(analise, objeto) if conferir else None
        dado = self._montar(valor, unidade)
        tentar(f"gravar {objeto}",
               lambda: self.p.Set(g.SetRequest(analysis=analise, object=objeto, data=dado)))
        if not conferir:
            return None
        depois = self.ler(analise, objeto)
        if isinstance(valor, (bool, str)):
            ok = depois == valor or (isinstance(depois, dict) and depois.get("Value") == valor)
        else:
            vd, va = valor_numerico(depois), valor_numerico(antes)
            if vd is None:
                ok = False
            elif not unidade or (isinstance(depois, dict) and depois.get("Units") == unidade):
                ok = abs(vd - float(valor)) <= 1e-9 * max(1.0, abs(float(valor)))
            else:
                ok = va is None or vd != va or abs(vd - float(valor)) < 1e-12
        if not ok:
            raise RuntimeError(f"{objeto}: gravei {valor} {unidade or ''} mas li {depois!r} "
                               f"(antes: {antes!r}). A gravação não teve o efeito esperado.")
        return depois

    # -------------------------------------------------------------- cálculo
    def resolver(self, analises, dependencias=True):
        """Resolve e confere o resultado de cada análise; levanta erro com as mensagens do solver."""
        g = self.gsi
        nomes = [analises] if isinstance(analises, str) else list(analises)
        resp = tentar("resolver " + ", ".join(nomes), lambda: self.p.SolveAnalyses(
            g.SolveAnalysesRequest(analyses=nomes, solve_dependencies=dependencias)))
        self._carregadas.clear()
        status = getattr(resp, "completion_status", None) or {}
        falhas = {n: getattr(r, "error_message", "") for n, r in dict(status).items()
                  if not getattr(r, "succeeded", True)}
        if getattr(resp, "all_succeeded", True) is False or falhas:
            raise RuntimeError("O solve falhou:\n" + "\n".join(f"  {n}: {m}" for n, m in falhas.items()))
        return resp

    # ----------------------------------------------------------- resultados
    def tem_resultados(self, analise):
        g = self.gsi
        r = tentar(f"conferir resultados de {analise}",
                   lambda: self.p.QueryResultsAvailability(g.QueryResultsAvailabilityRequest(analysis=analise)))
        return bool(getattr(r, "has_results", False))

    def carregar_resultados(self, analise):
        if analise in self._carregadas:
            return
        g = self.gsi
        tentar(f"carregar resultados de {analise}",
               lambda: self.p.LoadResults(g.LoadResultsRequest(analysis=analise)))
        self._carregadas.add(analise)

    def parametros_tabela(self, analise, tabela, instancia=None):
        """Parâmetros disponíveis numa tabela de resultado (QueryTableParamsInfo)."""
        g = self.gsi
        self.carregar_resultados(analise)
        kw = {"analysis": analise, "table": enum(g.ResultType, tabela)}
        if instancia is not None:
            kw["instance"] = int(instancia)
        r = self.p.QueryTableParamsInfo(g.QueryTableParamsInfoRequest(**kw))
        saida = []
        for info in r.params_info:
            saida.append({
                "parametro": nome_enum(g.DataParamType, info.dataparam),
                "chave": getattr(info, "key", ""),
                "nome": getattr(info, "display", ""),
                "unidade": getattr(info, "units", ""),
                "categoria": nome_enum(getattr(g, "UnitCategory", object), getattr(info, "unit_category", "")),
            })
        return saida

    def consultar(self, analise, tabela, parametros, passo=1, instancia=None, rodada=None, ids=None):
        """Valores de uma tabela de resultado: {'eXCoord': [...], ...}. passo 1 = permanente."""
        g = self.gsi
        self.carregar_resultados(analise)
        params = [enum(g.DataParamType, p) for p in parametros]
        kw = {"analysis": analise, "step": int(passo), "table": enum(g.ResultType, tabela),
              "dataparams": params}
        if instancia is not None:
            kw["instance"] = int(instancia)
        if rodada is not None:
            kw["run"] = int(rodada)
        if ids:
            kw["result_ids"] = [int(i) for i in ids]
        r = self.p.QueryResults(g.QueryResultsRequest(**kw))
        return {nome_enum(g.DataParamType, p): list(r.results[int(p)].values) if int(p) in r.results else []
                for p in params}

    def consultar_em_pontos(self, analise, parametros, pontos, passo=1, instancia=None, rodada=None):
        """Valores em coordenadas quaisquer: pontos = [(x, y), ...] ou [(x, y, z), ...]."""
        g = self.gsi
        self.carregar_resultados(analise)
        params = [enum(g.DataParamType, p) for p in parametros]
        pts = [g.Point(x=float(p[0]), y=float(p[1]), z=float(p[2]) if len(p) > 2 else 0.0) for p in pontos]
        kw = {"analysis": analise, "step": int(passo), "dataparams": params, "points": pts}
        if instancia is not None:
            kw["instance"] = int(instancia)
        if rodada is not None:
            kw["run"] = int(rodada)
        r = self.p.QueryResultsAtCoordinates(g.QueryResultsAtCoordinatesRequest(**kw))
        return {nome_enum(g.DataParamType, p): list(r.results[int(p)].values) if int(p) in r.results else []
                for p in params}

    # --------------------------------------------------------------- arquivo
    def fechar(self):
        try:
            self.p.Close()
        except Exception:  # noqa: BLE001
            pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.fechar()
