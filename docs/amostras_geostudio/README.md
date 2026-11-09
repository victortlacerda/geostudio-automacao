# Amostras do GeoStudio 2026.1

Mesmo método do slide2-automacao: cada amostra parte de um modelo-base e tem **uma única mudança**,
para que a diferença no arquivo mostre onde aquele dado fica. Salve cada uma **antes e depois de
resolver** (`_resolvido` no nome) e anote abaixo o valor digitado.

## slope/
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
