# API Python do GeoStudio (`gsi`)

Resumo da documentação oficial da 2026.1, que fica na pasta API da instalação
(menu Iniciar → "GeoStudio 2026.1.0 API Folder") e em
<https://aka.bentley.com/GeoStudio.url.ScriptingAPIDocs/1>. Os documentos da Bentley não são
copiados para cá: este arquivo registra só os nomes usados no projeto e o que já foi conferido.

## Instalação

- Python **>= 3.12.1 e < 3.13**.
- `pip install -r "C:\Program Files\Seequent\GeoStudio 2026.1\API\requirements.txt"`
  (instala `gsi-1.0-py3-none-any.whl` da mesma pasta).
- O GeoStudio precisa estar **licenciado**. A API conversa por gRPC com um serviço do GeoStudio em
  segundo plano; não é preciso abrir a interface.
- Com várias versões instaladas: `gsi.set_target_version("26.1")` **antes** do primeiro `OpenProject`.

## Objetos (Get / Set / Add / Delete)

| Item | Detalhe |
|---|---|
| Abrir / fechar | `gsi.OpenProject(r"...\modelo.gsz")` → `project.Close()` (sempre em `finally`) |
| Caminhos | `Materials["Argila"]`, `Materials["Argila"].UnitWeight`, `CurrentAnalysis.GeometryItems.Regions[1].Material`, `CurrentAnalysis.Objects.PiezometricSurfaces["..."]` |
| Índices | começam em **1** |
| Descobrir caminhos | SketchText no GeoStudio; `ferramentas/mapa_objetos.py` |
| Ler | `project.Get(gsi.GetRequest(analysis=, object=))` → `.data` (`google.protobuf.Value`): `.number_value`, `.string_value` ou `MessageToDict(.data.struct_value)` |
| Gravar | `project.Set(gsi.SetRequest(analysis=, object=, data=gsi.Value(number_value=20.0)))`; também `string_value`, `bool_value` |
| Unidades | `data.struct_value.update({"Value": 120.0, "Units": "lbf/ft³"})` converte para as unidades da análise; sem `Units` ou com `""` = já nas unidades da análise |
| Adimensional | nunca levar unidade (dá erro) |
| Vários campos | ler o objeto inteiro, `update` no struct e gravar o objeto |
| Criar / apagar | `AddRequest(analysis, object, data)` / `DeleteRequest(analysis, object, force_delete)` |

## Cálculo

- `project.SolveAnalyses(gsi.SolveAnalysesRequest(analyses=[...], solve_dependencies=True))`.
- Resposta: `all_succeeded` e `completion_status[nome]` com `succeeded` e `error_message`.
- `solve_dependencies` é `True` por padrão; `step` só vale para uma análise com dependências desligadas.
- **O SolveAnalyses salva o projeto** antes de resolver (e remalha se a geometria mudou). Estudos
  paramétricos devem trabalhar numa cópia do `.gsz`.

## Resultados

| Chamada | Uso |
|---|---|
| `QueryResultsAvailability(analysis)` | `has_results` |
| `LoadResults(analysis)` | obrigatório antes de consultar |
| `QueryTableParamsInfo(analysis, table, instance?)` | parâmetros disponíveis na tabela: `dataparam`, `display`, `units`, `unit_category` |
| `QueryResults(analysis, step, table, dataparams, instance?, run?, result_ids?)` | `results[int(dataparam)].values` |
| `QueryResultsAtCoordinates(analysis, step, dataparams, points)` | valores em coordenadas quaisquer (`gsi.Point(x, y, z)`) |

- `step=1` para análise permanente.
- `instance` identifica a superfície de deslizamento (tabelas `Column`, `Intercolumn`...) ou o
  gráfico (`ResultGraphs`).

### Tabelas (`gsi.ResultType`)

| Módulo | Tabelas |
|---|---|
| SLOPE/W | `Slip`, `CriticalSlip`, `Column`, `Intercolumn`, `LambdaFOS`, `Reinforcement`, `Probabilistic`, `Sample`, `Iteration` |
| SEEP/W | `Nodes`, `Elements`, `Gauss`, `FlowPath`, `TimeStep`, `SavedTimeStep`, `History`, `ResultGraphs` |
| SIGMA/W | `Nodes`, `Elements`, `Gauss`, `ElementNodes`, `BeamGauss`, `TimeStep`, `SavedTimeStep`, `History` |

### Parâmetros mais úteis (`gsi.DataParamType`)

| Uso | Parâmetros |
|---|---|
| Coordenadas | `eXCoord`, `eYCoord`, `eZCoord`, `eNodeNum`, `eElemNum` |
| FS e superfície | `eRawSlipFOS`, `eSlipNum`, `eSlipCenterX/Y`, `eSlipRadius`, `eSlipVolume`, `eSlipWeight`, `eResistingMoment`, `eActivatingMoment` |
| Lambda × FS | `eLambda`, `eFOSByForce`, `eFOSByMoment` |
| Fatias | `eSliceNum`, `eColumnWeight`, `ePoreWaterForce`, `eBaseNormalForce`, `eBaseNormalStress`, `eShearMob`, `eShearStrength`, `eBaseCohesion`, `eBasePhi`, `eBaseLength`, `eBaseNormalizedAngle`, `eIntersliceNormalForce`, `eIntersliceShearForce` |
| Reforços | `eReinforcementForce`, `eReinforcementShearForce` |
| Probabilístico | `eSlipFOSMean`, `eSlipFOSStdDev`, `eSlipReliabilityIndex`, `eSlipProbOfFailure` |
| Percolação | `eWaterPressure`, `eWaterPressureHead`, `eWaterTotalHead`, `eWaterGradient`, `eWaterFlux`, `eWaterCumulativeVolume` |
| Tensão-deformação | `eXDisplacement`, `eYDisplacement`, `eXYDisplacement`, `eXEffectiveStress`, `eYEffectiveStress`, `eXYShearStress`, `eMaxShearStrain` |
| Vigas (cortina) | `eAxialForce`, `eShearForce`, `eMoment`, `eRotation` |

## Conferido no GeoStudio real

| Item | Situação |
|---|---|
| `OpenProject`, `Get`, `Set`, `SolveAnalyses`, `LoadResults`, `QueryResults` | documentados; falta rodada real |
| Quais parâmetros cada tabela traz num modelo real | rodar `ferramentas/tabelas_resultados.py` |
| Geometria da superfície crítica (pontos) | a descobrir com `tabelas_resultados` |
| FS por método (Bishop, Spencer, M-P) numa mesma análise | a descobrir |
