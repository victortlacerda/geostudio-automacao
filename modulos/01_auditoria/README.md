# Módulo 01 · Auditoria do projeto

Lê o `.gsz` (sem abrir o GeoStudio e sem a API, então funciona com a licença de estudante) e entrega
um relatório HTML que resume o projeto inteiro e aponta o que pede conferência, no molde do
`soiltest_auditoria` do plaxis3d-automacao: **ERRO**, **ALERTA** e **INFO**.

## Como usar

- Duplo clique em `auditoria.bat`, escolha o(s) `.gsz` e o FS alvo (Enter = 1,5). O relatório abre no navegador.
- Ou arraste o `.gsz` (ou uma pasta) em cima do `.bat`.
- Terminal: `python modulos\01_auditoria\auditoria.py talude.gsz --fs-alvo 1.5`

Saída: `<nome>_auditoria\relatorio.html` ao lado do `.gsz`, um arquivo só com as figuras embutidas
(dá para mandar por e-mail ou imprimir em PDF pelo navegador).

## O que o relatório traz

| Seção | Conteúdo |
|---|---|
| Resumo | Parecer (OK / ALERTA / ERRO), FS mínimo, contagem de achados, quadro das análises com FS e verificação |
| Comparação de métodos | Quando há mais de uma análise SLOPE/W resolvida: FS por método, diferença para o mínimo, centro, raio, entrada e saída, gráfico de barras e superfícies críticas sobrepostas |
| Geometria | Extensão, regiões coloridas pelo material, áreas |
| Materiais | γ, c', φ' e checagens |
| Cada análise | Busca de superfícies (faixas, incrementos, direção, λ), resultado da crítica, superfícies inválidas por código, figura e achados |
| Rastreabilidade | Seções do modelo e falhas de leitura |

## Checagens

| Nível | Regra |
|---|---|
| ERRO | região sem material ou com área nula; γ ≤ 0 ou ausente; c' < 0; φ' fora de 0 a 90°; c' e φ' nulos |
| ALERTA | análise não resolvida; γ fora de 14 a 23 kN/m³; φ' fora de 15 a 45°; unidades não métricas; FS abaixo do alvo; crítica na borda da faixa de entrada e saída; mais de 50 % das superfícies inválidas; FS por força e por momento diferentes; métodos rigorosos (M-P, Spencer, GLE, Sarma) diferindo mais de 2 %; poucos incrementos na busca |
| INFO | material sem uso; c' > 30 kPa (confirmar que é efetiva); sem coesão; modelo sem água; só 1 crítica guardada; variação do FS entre métodos; seções ainda não interpretadas (reforços, cargas) |

As faixas de materiais são referências de literatura, não regras de norma.

## Situação

- **auditoria-v0.1**: testado com `s00_talude5m.gsz` (FS 1,786) e com uma cópia sintética de duas análises.
- **[não testado]**: modelos com linha piezométrica, cargas e reforços (só contados); SEEP/W e SIGMA/W
  (só inventário); mais de uma geometria.
