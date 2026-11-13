# Roadmap

Ordem: entender a API e o arquivo, extrair o SLOPE/W (maior parte dos relatórios), depois SEEP/W e
SIGMA/W. Nenhuma fase avança sem o critério de saída conferido no GeoStudio real.

## Fase 0: descoberta (em andamento)
- [x] `procurar_instalacao`: acha a instalação, o `gsi-*.whl`, exemplos e o `GeoCmd.exe`.
- [x] `diagnostico_gsi`: descreve funções, pedidos, campos e enumerações da API.
- [x] `inspecionar_gsz`: análises, materiais e colunas de cada CSV de resultado.
- [x] `mapa_objetos` [não testado]: caminhos de objetos com valor e unidade pela API.
- [x] Documentação oficial da API 2026.1 resumida em `docs/api_gsi.md`; `comum/api.py` com os nomes reais.
- [x] `tabelas_resultados` [não testado]: tabelas, parâmetros e amostra de valores por análise.
- [ ] Rodar as ferramentas na máquina do usuário (SLOPE/W primeiro) e registrar o que cada tabela traz.
- [ ] Ver os scripts prontos em aka.bentley.com/GeoStudio.url.ScriptingAPIDocs/1.
- [ ] Amostras com uma única mudança em `docs/amostras_geostudio/` (lista no README da pasta).
- [x] A API usa um serviço em segundo plano; não exige a interface aberta (documentação oficial).
- [x] Adimensionais: gravar sem unidade (documentação 2026.1).

**Critério de saída:** a API lê e grava um parâmetro de cada módulo, conferido lendo de volta.

## Fase 1: inventário (módulo 01)
- [ ] Análises (árvore pai/filha, tipo, método), materiais e parâmetros de uma pasta de modelos em xlsx.

**Critério:** bate com o que a interface mostra.

## Fase 2: resultados do SLOPE/W (módulo 02) (em andamento)
- [x] FS por análise e superfície crítica, lidos do `.gsz` (slope-v0.1, validado: FS 1,786).
- [x] Superfície crítica e as N guardadas desenhadas sobre a geometria.
- [x] Fatias (σ', poropressão, parcelas de resistência), entre fatias e λ x FS.
- [x] Checagens: FS abaixo do alvo, crítica na borda da faixa de entrada e saída, muitas inválidas.
- [x] xlsx com figuras + PNG por análise.
- [ ] Validar com mais amostras: grid and radius, Bishop/Spencer, NA, sobrecarga, reforço.
- [ ] Cores dos materiais na figura (associação região × material fica em `Contexts`).

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

## Pendências da licença de estudante
- Malha limitada a 500 elementos: modelos de teste pequenos.
- A API (`gsi`) ainda não foi testada com essa licença: `rodar_teste_slope.bat` passos 3 e 4.

## Decisões tomadas
- GeoStudio 2026.1; módulos SLOPE/W, SEEP/W e SIGMA/W.
- API `gsi` como via principal; leitura do `.gsz` como apoio e para testes sem o programa.
- Scripts rodam fora do GeoStudio, por terminal ou `.bat`.
