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

## A confirmar com as amostras da 2026.1

- [ ] Nomes e colunas dos CSV do SLOPE/W (superfícies, FS por método, fatias).
- [ ] Colunas do `node.csv` do SEEP/W e do SIGMA/W; arquivos por elemento e de vigas.
- [ ] Como as etapas do SIGMA/W e os passos do transiente aparecem nas pastas `NNN`.
- [ ] Estrutura do `mesh_<id>.ply`.
