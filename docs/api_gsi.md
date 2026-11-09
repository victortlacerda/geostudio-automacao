# API Python do GeoStudio (`gsi`)

Registro do que se sabe da API e de onde veio. Só entra como **confirmado** o que foi visto no
`diagnostico_gsi.txt`, num exemplo da instalação ou numa rodada real na 2026.1.

## Confirmado (fontes públicas)

| Fato | Fonte |
|---|---|
| A API existe desde a 2025.1; é distribuída como wheel `gsi-<versão>` com o GeoStudio | [Seequent Community 3196](https://community.seequent.com/discussion/3196/geostudio-api-python), [2250](https://community.seequent.com/discussion/2250/the-programming-capabilities-of-geostudio) |
| Usa `grpcio`; citado com Python 3.12 no Windows 11 | [3196](https://community.seequent.com/discussion/3196/geostudio-api-python) |
| Leitura e gravação por `GetRequest` / `SetRequest`; valores no formato `{"Value": ..., "Units": ...}` | [3259](https://community.seequent.com/discussion/3259/geostudio-api-gsi-setrequest) |
| Caminhos de objetos como `CurrentAnalysis.Objects.ReinforcementLines[1]...`, descobertos em Sketch → Text → Insert Field | [3196](https://community.seequent.com/discussion/3196/geostudio-api-python) |
| 2025.2: consulta da malha em qualquer coordenada; solve mais rápido via script; remalha ao salvar ou resolver pela API | [Notas da 2025.2](https://files.seequent.com/PDFs/GeoStudio-2025.2-Release-Notes-A4-EN-201125-V1.pdf) |
| Bug (2025): valor adimensional não aceita gravação com `Units` vazio | [3259](https://community.seequent.com/discussion/3259/geostudio-api-gsi-setrequest) |

## A confirmar na 2026.1

| Item | Usado em | Situação |
|---|---|---|
| `gsi.OpenProject(caminho)` | `comum/api.py` | [não testado] |
| `projeto.Get(gsi.GetRequest(analysis=, object=))` | `comum/api.py` | [não testado] |
| `projeto.Set(gsi.SetRequest(analysis=, object=, data=))` com `data` = `google.protobuf.Value` | `comum/api.py` | [não testado] |
| `projeto.SolveAnalyses(gsi.SolveAnalysesRequest(analyses=[...]))` | `comum/api.py` | [não testado] |
| Consulta de resultados (`QueryResults`?) e seus campos | módulo 02 | a descobrir |
| A interface precisa estar aberta? | todos | a descobrir |
| Bug dos adimensionais corrigido? | módulo 03 | a testar |

Preencher com o `diagnostico_gsi.txt` da máquina do usuário.
