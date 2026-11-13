# Formato do arquivo `.gsz`

O `.gsz` não é documentado pela Seequent. Este registro junta o que vem de fontes abertas e o que
for confirmado nas amostras de `docs/amostras_geostudio/`. Cada item confirmado cita a amostra.

## Estrutura conhecida

```text
<nome>.xml                    modelo (o nome pode diferir se o arquivo foi renomeado)
mesh_<id>.ply                 malha de cada geometria (PLY binário)
<Análise>/<NNN>/node.csv      resultados nodais do passo salvo NNN (000 = permanente)
<Análise>/<NNN>/*.csv         outras tabelas de resultado
```

- No nome da pasta de resultados, `/` do nome da análise vira `&3`.
- O XML tem, na raiz: `FileInfo` (atributo `Version`), `Geometries`, `Analyses`, `Contexts`,
  `Materials`, `Reinforcements`, `Functions`, `DataSets`. Cada seção tem atributo `Len`.
- `Analysis`: filhos `ID`, `Name`, `Kind`, `Method`, `ParentID`, `GeometryId`, `TimeIncrements`...
- `Material`: filhos `ID`, `Name`, `SlopeModel`, `SeepModel`, `StressModel`; parâmetros como
  atributos de `<StressStrain>` (`UnitWeight`, `CohesionPrime`, `PhiPrime`, `YoungsPrimeModulus`,
  `EffectivePoissonsRatio`...) e `<Hydraulic>`.
- Gráficos definidos no programa gravam CSV com dois números no nome (cache e sequência), ligados
  no XML.

Fontes: código do [PyGeoStudio](https://github.com/MoiseRousseau/PyGeoStudio) (consultado, não
copiado) e [Seequent Community 1769](https://community.seequent.com/discussion/1769/how-to-induce-the-permeability-random-fields-into-geostudio-seep-w).

## Confirmado com `s00_talude5m.gsz` (GeoStudio 2026.1, SLOPE/W)

- XML do modelo com o nome do arquivo; `FileInfo` traz `FileVersion` (11.15) e `AppVersion` (26.1.0.1261).
- Resultados em `Análise SLOPE&3W/001/` (passo `001` no SLOPE/W), além de `Mesh.ply` e uma cópia do XML.
- `slip_surface.csv`: uma linha por superfície testada. Colunas `SlipNum, SlipFOS, SlipCenterX,
  SlipCenterY, SlipRadiusX, SlipVolume, SlipWeight, SlipOrigSearchMethod, ResistingForceX,
  ActivatingForceX, ResistingMomentX, ActivatingMomentX, MobilizedShearDirection, LambdaX, CustomParam1..9`.
  `SlipFOS` ≥ 900 é código de erro (998 = volume/profundidade abaixo do mínimo).
- Para cada uma das N críticas guardadas (*Armazenar superfícies críticas*): `column_<n>.csv` (fatias:
  `X, Y, XLeft, XRight, YBackBotLeft/Right, ColumnWeight, PoreWaterPressure, NormalEffectiveStress,
  CohesiveStrength, FrictionalStrength, ResistingForceX, ActivatingForceX...`), `intercolumn_<n>.csv`,
  `lambdafos_<n>.csv` (`LambdaX, FOSByForce, FOSByMoment`) e `mobilizedsheardirectionfos_<n>.csv`.
- Busca de superfícies em `StabilityItems/StabilityItem/Entry/SlipSurface`: `EntryExit` (faixas),
  `Limit`, `DirectionOfSlip`, `NumberOfCriticalSlipsToKeep`.
- O tamanho padrão da malha não fica gravado quando não foi alterado. Tag `MeshDefaultEdgeLength` na
  geometria (citada no PyGeoStudio) **não** teve efeito na 2026.1.

## Métodos (confirmado com `s04a` a `s04d`)

- `Method` no XML: `Morgenstern-Price`, `Spencer`, `Bishop`, `Janbu` e `Ordinary` (Fellenius no menu).
- Todos gravam `slip_surface.csv` com as mesmas colunas; `SlipFOS` é o FS do método escolhido.
- `lambdafos_<n>.csv`: M-P e Spencer varrem λ (várias linhas, `FOSByForce` e `FOSByMoment`); Bishop e
  Janbu gravam duas linhas com λ = 0 e só a coluna `FOSByForce` preenchida (`FOSByMoment` vazio);
  Fellenius grava só o cabeçalho. Fellenius não grava `mobilizedsheardirectionfos_<n>.csv`.
- Renomear uma análise na interface apaga os resultados dela.

## Licença de estudante

- Limite de 500 elementos na malha do SLOPE/W: o arquivo nem abre se passar. Modelos de teste pequenos
  (o talude de 5 m gera menos de 500 com a malha padrão).
- No máximo 2 análises SLOPE/W por arquivo: "O número máximo de análises suportado em uma licença
  Estudante do SLOPE/W é 2" (ao salvar).

## A confirmar com as amostras da 2026.1

- [x] Nomes e colunas dos CSV do SLOPE/W (superfícies, fatias, λ x FS).
- [ ] Colunas do `node.csv` do SEEP/W e do SIGMA/W; arquivos por elemento e de vigas.
- [ ] Como as etapas do SIGMA/W e os passos do transiente aparecem nas pastas `NNN`.
- [ ] Estrutura do `mesh_<id>.ply`.
