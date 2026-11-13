# Amostras do GeoStudio 2026.1

Mesmo método do slide2-automacao: cada amostra parte de um modelo-base e tem **uma única mudança**,
para que a diferença no arquivo mostre onde aquele dado fica. Salve cada uma **antes e depois de
resolver** (`_resolvido` no nome) e anote abaixo o valor digitado.

## slope/

| Arquivo | Situação |
|---|---|
| `s00_talude5m.gsz` | **resolvido**: talude 5 m 1V:1H, argila γ 18, c' 10, φ' 30, M-P, entrada e saída. FS = 1,786 (superfície 369). Também em `testes/dados/` |
| `s00_base.gsz` | talude 10 m; não abre na licença de estudante (malha > 500 elementos) |

| Arquivo | Mudança a partir do base | Valor |
|---|---|---|
| `s00_base.gsz` | talude simples, 1 material, Morgenstern-Price, grid and radius | |
| `s01_dois_materiais.gsz` | 2º material com c', φ' diferentes | |
| `s02_na.gsz` | linha piezométrica | |
| `s03_sobrecarga.gsz` | carga distribuída na crista | |
| `s04_metodos.gsz` | Bishop, Janbu e Spencer ligados | |
| `s05_entry_exit.gsz` | busca entry and exit | |
| `s06_tirante.gsz` | um reforço (tirante ou grampo) | |

## seep/
| Arquivo | Mudança | Valor |
|---|---|---|
| `p00_permanente.gsz` | fluxo permanente, carga a montante e jusante | |
| `p01_secao_fluxo.gsz` | uma seção de fluxo (flux section) | |
| `p02_transiente.gsz` | rebaixamento com 5 passos salvos | |
| `p03_slope_filho.gsz` | SLOPE/W filho usando a poropressão | |

## sigma/
| Arquivo | Mudança | Valor |
|---|---|---|
| `g00_in_situ.gsz` | análise in situ | |
| `g01_escavacao.gsz` | escavação em 2 etapas | |
| `g02_cortina.gsz` | viga (cortina) com escavação | |
