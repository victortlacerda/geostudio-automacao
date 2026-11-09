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
| `modulos/01_inventario` … `06_relatorio` | Ver [`docs/roadmap.md`](docs/roadmap.md) | A fazer |

## Instalação

Windows com o GeoStudio 2026.1 instalado e licenciado, e Python 3.10 ou mais novo
(a Seequent cita Python 3.12).

```bat
git clone https://github.com/victortlacerda/geostudio-automacao.git
cd geostudio-automacao
pip install -r requirements.txt
```

Depois, instale o pacote da API que vem com o GeoStudio:

1. Dê duplo clique em `ferramentas\procurar_instalacao.bat`. Ele mostra onde está o `gsi-*.whl` e o
   comando `pip install` pronto.
2. Rode esse comando no mesmo Python dos scripts.
3. Dê duplo clique em `ferramentas\diagnostico_gsi.bat`. Ele grava `diagnostico_gsi.txt` com tudo o
   que a API oferece na sua versão.

## Como rodar

Os scripts rodam **fora** do GeoStudio: num terminal ou pelos `.bat` (duplo clique, ou arraste o
`.gsz` em cima do `.bat`). Não há menu de scripts dentro do programa.

```bat
rem Ler um modelo resolvido sem abrir o GeoStudio
python ferramentas\inspecionar_gsz.py C:\modelos\talude.gsz

rem Mapa de objetos pela API (somente leitura)
python ferramentas\mapa_objetos.py C:\modelos\talude.gsz
```

## Primeira rodada (Fase 0)

Rode e mande para o Claude:

1. `procurar_instalacao.txt` (gerado em `ferramentas\`);
2. `diagnostico_gsi.txt` (gerado em `ferramentas\`);
3. o `_inspecao.txt` de um `.gsz` resolvido de cada módulo (SLOPE/W, SEEP/W, SIGMA/W).

Com isso os nomes reais da API e o formato dos resultados ficam registrados em
[`docs/api_gsi.md`](docs/api_gsi.md) e [`docs/formato_gsz.md`](docs/formato_gsz.md), e os módulos
de resultado começam a ser escritos.

## Testes (sem GeoStudio)

```bash
pip install pytest
pytest -q testes
```

Os testes usam um `.gsz` sintético e um pacote `gsi` falso; o GitHub Actions roda tudo a cada envio.

> **Responsabilidade técnica.** O formato interno do `.gsz` não é documentado pela Seequent e a
> documentação pública da API ainda é curta. Confira sempre os resultados no GeoStudio. A ferramenta
> acelera o trabalho, mas não substitui a verificação do projetista.
