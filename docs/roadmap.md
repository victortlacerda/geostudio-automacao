# Roadmap

Ordem: entender a API e o arquivo, extrair o SLOPE/W (maior parte dos relatórios), depois SEEP/W e
SIGMA/W. Nenhuma fase avança sem o critério de saída conferido no GeoStudio real.

## Fase 0: descoberta (em andamento)
- [x] `procurar_instalacao`: acha a instalação, o `gsi-*.whl`, exemplos e o `GeoCmd.exe`.
- [x] `diagnostico_gsi`: descreve funções, pedidos, campos e enumerações da API.
- [x] `inspecionar_gsz`: análises, materiais e colunas de cada CSV de resultado.
- [x] `mapa_objetos` [não testado]: caminhos de objetos com valor e unidade pela API.
- [ ] Rodar os quatro na máquina do usuário e registrar em `docs/api_gsi.md` e `docs/formato_gsz.md`.
- [ ] Copiar os exemplos da instalação para `docs/referencia_api/`.
- [ ] Amostras com uma única mudança em `docs/amostras_geostudio/` (lista no README da pasta).
- [ ] Confirmar se a API exige a interface aberta ou só o programa instalado.
- [ ] Testar a gravação de valores adimensionais (bug das versões 2025).

**Critério de saída:** a API lê e grava um parâmetro de cada módulo, conferido lendo de volta.

## Fase 1: inventário (módulo 01)
- [ ] Análises (árvore pai/filha, tipo, método), materiais e parâmetros de uma pasta de modelos em xlsx.

**Critério:** bate com o que a interface mostra.

## Fase 2: resultados do SLOPE/W (módulo 02)
- [ ] FS por análise e método.
- [ ] Superfície crítica (coordenadas) e as N seguintes; desenho sobre a geometria.
- [ ] Forças por fatia (peso, normal, cisalhante, poropressão) e gráficos ao longo da superfície.
- [ ] Checagens como no Slide2: mínimo na borda da grelha, superfície no limite, FS abaixo do alvo.
- [ ] Saída em xlsx com figuras + PNG por análise, no formato do módulo 04 do Slide2.

**Critério:** FS igual ao do GeoStudio (±0,001).

## Fase 3: lote e paramétrico (módulo 03)
- [ ] Variar c', φ', γ, NA ou sobrecarga a partir de uma planilha, resolver pela API e ler o FS.
- [ ] Curvas FS × parâmetro e gráfico tornado (sensibilidade).
- [ ] Esforços em reforços (tirantes, grampos, geossintéticos).
- [ ] Probabilístico: histograma do FS e P(FS < 1).

**Critério:** caso do Slope Stability Verification Manual reproduzido.

## Fase 4: resultados do SEEP/W (módulo 04)
- [ ] Poropressão e carga total em pontos e perfis verticais; séries no tempo (transiente).
- [ ] Vazão nas seções de fluxo; gradiente de saída no pé (piping).
- [ ] Rebaixamento rápido: FS × tempo com o SLOPE/W filho.

**Critério:** perfil confere com a interface.

## Fase 5: resultados do SIGMA/W (módulo 05)
- [ ] Deslocamentos e tensões por etapa construtiva.
- [ ] Esforços em vigas (cortina): diagramas de momento e cortante.
- [ ] Recalques em pontos de controle.

**Critério:** M e V da cortina conferem à mão.

## Fase 6: relatório e comparação (módulo 06)
- [ ] Memorial Word/HTML com tabelas, figuras e verificações (FS mínimo, NBR 11682).
- [ ] Mesmo caso no GeoStudio, Slide2 e PLAXIS 3D lado a lado (formato comum de colunas).

**Critério:** memorial revisado num projeto real.

## Decisões tomadas
- GeoStudio 2026.1; módulos SLOPE/W, SEEP/W e SIGMA/W.
- API `gsi` como via principal; leitura do `.gsz` como apoio e para testes sem o programa.
- Scripts rodam fora do GeoStudio, por terminal ou `.bat`.
