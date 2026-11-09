# GeoStudio Automação

Automação do **GeoStudio 2026.1** (SLOPE/W, SEEP/W e SIGMA/W) com Python: extrair resultados de
modelos resolvidos, gerar gráficos e valores calculados, e rodar estudos em lote.

Tudo roda na sua máquina, de graça, sem chave de API nem IA. As duas vias usadas:

- **API Python oficial do GeoStudio** (pacote `gsi`, que vem com o programa desde a 2025.1): abre o
  projeto, lê e altera propriedades, resolve e consulta resultados. Funciona como o servidor de
  scripts do PLAXIS.
- **Leitura direta do `.gsz`**: o arquivo do GeoStudio é um ZIP com o XML do modelo e, depois de
  resolvido, os CSV de resultados. Dá para ler sem abrir o programa, como o `.slim` do Slide2.

Segue o mesmo molde de [slide2-automacao](https://github.com/victortlacerda/slide2-automacao) e
[plaxis3d-automacao](https://github.com/victortlacerda/plaxis3d-automacao).

## Situação

| Pasta | O que faz | Situação |
|---|---|---|
| [`ferramentas/procurar_instalacao`](ferramentas/procurar_instalacao.py) | Acha a instalação do GeoStudio, o pacote `gsi-*.whl`, exemplos e o `GeoCmd.exe` | **v0.1**, testado sem GeoStudio |
| [`ferramentas/diagnostico_gsi`](ferramentas/diagnostico_gsi.py) | Descreve funções, pedidos, campos e enumerações da API (somente leitura) | **v0.1**, testado com API falsa |
| [`ferramentas/inspecionar_gsz`](ferramentas/inspecionar_gsz.py) | Lê um `.gsz`: análises, materiais, arquivos de resultado e suas colunas | **v0.1**, testado com `.gsz` sintético |
| [`ferramentas/mapa_objetos`](ferramentas/mapa_objetos.py) | Pela API, lista caminhos de objetos com valor e unidade | **[não testado]** no GeoStudio real |
| [`ferramentas/tabelas_resultados`](ferramentas/tabelas_resultados.py) | Pela API, lista as tabelas de resultado de cada análise, os parâmetros (nome, unidade) e os primeiros valores | **[não testado]** no GeoStudio real |
| `modulos/01_inventario` … `06_relatorio` | Ver [`docs/roadmap.md`](docs/roadmap.md) | A fazer |

## Instalação

Windows com o GeoStudio 2026.1 instalado e licenciado, e **Python 3.12** (a API exige
3.12.1 ou mais novo, e menor que 3.13).

```bat
git clone https://github.com/victortlacerda/geostudio-automacao.git
cd geostudio-automacao
pip install -r requirements.txt
pip install -r "C:\Program Files\Seequent\GeoStudio 2026.1\API\requirements.txt"
```

A segunda linha instala o pacote da API (`gsi`) que vem com o GeoStudio. Se a pasta for outra,
procure "GeoStudio 2026.1.0 API Folder" no menu Iniciar, ou rode `ferramentas\procurar_instalacao.bat`.

Para conferir: `python -c "import gsi; print('ok')"`.

## Como rodar

Os scripts rodam **fora** do GeoStudio, num terminal ou pelos `.bat` (duplo clique, ou arraste o
`.gsz` em cima do `.bat`). A API conversa com um serviço do GeoStudio em segundo plano; a interface
não precisa estar aberta. Feche o modelo na interface antes de rodar um script sobre ele.

> **Atenção:** resolver pela API (`SolveAnalyses`) **salva o projeto**. Os estudos em lote vão
> sempre trabalhar numa cópia do `.gsz`; as ferramentas de leitura não resolvem nem gravam nada.

```bat
rem Ler um modelo resolvido sem abrir o GeoStudio (não usa a API)
python ferramentas\inspecionar_gsz.py C:\modelos\talude.gsz

rem Tabelas e parâmetros de resultado de cada análise (API, somente leitura)
python ferramentas\tabelas_resultados.py C:\modelos\talude.gsz

rem Caminhos de objetos com valor e unidade (API, somente leitura)
python ferramentas\mapa_objetos.py C:\modelos\talude.gsz
```

## Primeira rodada (Fase 0)

Com um `.gsz` de SLOPE/W **já resolvido**, rode e mande para o Claude:

1. `tabelas_resultados.bat` → `<nome>_tabelas.txt` (o mais importante: mostra de onde sai cada resultado);
2. `mapa_objetos.bat` → `<nome>_mapa_objetos.csv` e o `_log.txt`;
3. `inspecionar_gsz.bat` → `<nome>_inspecao.txt`;
4. o FS que o GeoStudio mostra para esse modelo (gabarito).

Depois, o mesmo para um modelo de SEEP/W e um de SIGMA/W. O que for confirmado vai para
[`docs/api_gsi.md`](docs/api_gsi.md) e [`docs/formato_gsz.md`](docs/formato_gsz.md).

## Testes (sem GeoStudio)

```bash
pip install pytest
pytest -q testes
```

Os testes usam um `.gsz` sintético e um pacote `gsi` falso; o GitHub Actions roda tudo a cada envio.

> **Responsabilidade técnica.** O formato interno do `.gsz` não é documentado pela Seequent e a
> documentação pública da API ainda é curta. Confira sempre os resultados no GeoStudio. A ferramenta
> acelera o trabalho, mas não substitui a verificação do projetista.
