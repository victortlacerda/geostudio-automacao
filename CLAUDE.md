# Instruções para o Claude neste repositório

Automação do **GeoStudio 2026.1** (SLOPE/W, SEEP/W, SIGMA/W) em Python. O usuário é engenheiro
geotécnico, escreve em português e confere os resultados no GeoStudio e à mão.
Repositórios irmãos, com o mesmo método: `victortlacerda/slide2-automacao` (edição e leitura do
arquivo do modelo, solver por linha de comando) e `victortlacerda/plaxis3d-automacao` (API por
servidor de scripts, mock, diagnóstico).

## Vias de automação
- **API `gsi`** (gRPC, vem com o GeoStudio): via principal para alterar, resolver e consultar.
  Nomes de métodos e campos só valem depois de confirmados em `docs/api_gsi.md` (diagnóstico,
  exemplos da instalação ou rodada real). Até lá, passam por `tentar(...)` e ficam **[não testado]**.
- **Leitura do `.gsz`** (`modulos/comum/gsz.py`): ZIP com `<nome>.xml`, `mesh_<id>.ply` e
  `<Análise>/<NNN>/*.csv` ('/' no nome vira '&3'). Só biblioteca padrão.
- `GeoCmd.exe`: reserva para solve em lote sem a API.

## Regras de ouro (herdadas do plaxis3d-automacao)
1. Nada que já foi validado no GeoStudio real muda de comportamento; função nova entra como opção
   com padrão equivalente ao anterior.
2. Marcar tudo que não foi validado como **[não testado]**, no script, no README e na resposta.
3. Toda gravação pela API é conferida lendo o valor de volta (`Projeto.gravar(conferir=True)`).
4. Em modelos grandes, não abortar na primeira falha: registrar, seguir e listar o que faltou.
5. Nome desconhecido: pedir ao usuário o `diagnostico_gsi.txt`, um exemplo da instalação ou o
   caminho de Sketch → Text → Insert Field. Nunca inventar.
6. Scripts interativos: Enter aceita o padrão; aceitar vírgula ou ponto; `--config` repete a rodada.

## Engenharia reversa do formato (herdada do slide2-automacao)
- Amostras em `docs/amostras_geostudio/<módulo>/`, cada uma com **uma única mudança** a partir de um
  modelo-base, salvas antes e depois de resolver; anotar no README da pasta o que foi mudado.
- O que for descoberto vai para `docs/formato_gsz.md`, com a amostra que comprova.

## A cada atualização
1. `pytest -q testes` (sem GeoStudio) tem que passar.
2. Atualizar `docs/roadmap.md` (marcar [x], anotar pendências) e `CHANGELOG.md` (versão por módulo).
3. Commit em português, descrevendo a etapa, e push para `main`.

Unidades: kN, m, kPa, kN/m³, graus. Textos e mensagens em português.
