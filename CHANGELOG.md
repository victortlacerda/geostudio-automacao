# Registro de mudanças

## Módulo 01 · auditoria

### auditoria-v0.1
- Relatório HTML do projeto (um arquivo, figuras embutidas): resumo com parecer, análises, comparação de
  métodos, geometria com materiais, materiais com checagens, busca de superfícies, resultado e achados.
- Comparação de métodos entre vários `.gsz` (`comparacao_metodos.html`), para a licença de estudante.
- `comum/modelo.py`: leitura do XML (regiões, materiais com cores, contextos, busca, água).

## Ferramentas

### ferramentas-v0.2
- `teste_abrir_api` [não testado]: testa se a API abre o `.gsz` no caminho original e numa cópia sem acento.
- `comum/api.py`: mensagens de erro do GeoStudio em cp1252 passam a aparecer legíveis.

## Módulo 02 · resultados do SLOPE/W

### slope-v0.2
- Lê Bishop, Janbu e Fellenius (colunas de λ vazias viram `None`; antes a checagem quebrava).
- Figura FS x λ só para métodos que varrem λ (M-P, Spencer).
- `nome_metodo`: "Ordinary" do XML aparece como "Fellenius (Ordinário)".

### slope-v0.1
- Lê do `.gsz` resolvido todas as superfícies, a crítica, fatias, entre fatias e λ x FS
  (`modulos/comum/slope.py`), sem GeoStudio e sem API.
- Gera `resultados_slope.xlsx` e figuras (crítica sobre a geometria, fatias, λ x FS).
- Checagens: FS alvo, crítica na borda da faixa de entrada e saída, superfícies inválidas, força x momento.
- Validado com `s00_talude5m.gsz` (licença de estudante): FS 1,786 igual ao da interface.
- `instalar_ambiente.bat` sem a atualização do pip (era cancelada no Windows); `rodar_teste_slope.bat`
  roda testes, módulo 02 e as ferramentas da API na amostra resolvida.

## v0.2 (API conferida na documentação oficial 2026.1)
- `comum/api.py`: nomes reais da API. Leitura por `GetResponse.data`; gravação com `gsi.Value`
  (número, texto, booleano ou número com unidade), conferida lendo de volta; `resolver` confere
  `all_succeeded` e mostra a mensagem de erro do solver; `tem_resultados`, `carregar_resultados`,
  `parametros_tabela` (QueryTableParamsInfo), `consultar` (QueryResults) e `consultar_em_pontos`;
  `versao=` chama `set_target_version`.
- `tabelas_resultados` [não testado]: tabelas de resultado de cada análise com parâmetros, unidades
  e os primeiros valores.
- `mapa_objetos`: raízes `Materials`, `CurrentAnalysis`, `.Objects`, `.GeometryItems`; índices a partir de 1.
- README: instalação pelo requirements.txt da pasta API (Python 3.12); aviso de que o solve salva o projeto.
- `docs/api_gsi.md`: resumo da referência oficial (tabelas e parâmetros de SLOPE/W, SEEP/W e SIGMA/W).

## Ferramentas da Fase 0

### v0.1
- `procurar_instalacao`: acha as pastas do GeoStudio, o `gsi-*.whl` (com o `pip install` pronto),
  scripts de exemplo, arquivos `.proto` e o `GeoCmd.exe`. Testado sem GeoStudio.
- `diagnostico_gsi`: descreve funções, classes, mensagens protobuf (campos) e enumerações do pacote
  `gsi`, em `.txt` e `.json`. Testado com uma API falsa.
- `inspecionar_gsz`: lê o `.gsz` sem abrir o programa (análises em árvore, materiais com parâmetros,
  arquivos de resultado com colunas). Testado com `.gsz` sintético.
- `mapa_objetos` [não testado]: caminhos de objetos com valor e unidade pela API, com log de falhas.
- `.bat` para cada ferramenta (duplo clique ou arrastar o arquivo em cima).

## Comum

### v0.1
- `gsz.py`: leitor do `.gsz` (XML do modelo, passos salvos, CSV de resultados; `/` → `&3`).
- `api.py` [não testado]: `Projeto` com abrir, ler, gravar conferindo de volta, resolver, salvar e
  fechar; `tentar` com alternativas; `achatar` para respostas em árvore.
