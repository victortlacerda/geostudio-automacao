# Registro de mudanças

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
