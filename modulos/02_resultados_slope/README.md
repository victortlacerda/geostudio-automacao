# Módulo 02: resultados do SLOPE/W

Lê um `.gsz` **já resolvido e salvo** e gera, sem abrir o GeoStudio e sem a API:

| Saída | Conteúdo |
|---|---|
| `resultados_slope.xlsx` | Resumo (FS, método, superfície crítica, verificação contra o FS alvo, checagens), Superfícies (todas, com o motivo das inválidas), Fatias, Entre fatias, Lambda x FS e as figuras |
| `<análise>_critica.png` | geometria, superfície crítica com fatias e centro, demais críticas guardadas, faixas de entrada e saída |
| `<análise>_fatias.png` | tensão normal efetiva, poropressão e parcelas de resistência ao longo da base |
| `<análise>_lambda.png` | FS por força e por momento x λ |

A pasta de saída é `<nome>_resultados`, ao lado do `.gsz`.

## Como rodar

- Duplo clique em `resultados_slope.bat`: escolhe o arquivo numa janela e pergunta o FS alvo (Enter = 1,5).
- Ou arraste um ou mais `.gsz` em cima do `.bat`.
- Terminal: `python resultados_slope.py talude.gsz --fs-alvo 1.5`

## Checagens

- FS crítico abaixo do alvo.
- Superfície crítica tocando a borda de uma faixa de entrada e saída (amplie a faixa), como no slide2-automacao.
- Mais da metade das superfícies inválidas (mostra os códigos: 996, 997, 998, 999).
- FS por força e por momento diferentes na última iteração de λ.

## Situação

**slope-v0.1**, validado com `docs/amostras_geostudio/slope/s00_talude5m.gsz`: superfície 369,
FS = 1,786 (Morgenstern-Price), igual ao da interface do GeoStudio 2026.1.

Só guarda fatias das N superfícies críticas definidas em *Armazenar superfícies críticas*
(Dados → Projeto → Superfície de pesquisa). Para ter as fatias de mais superfícies, aumente esse número.
