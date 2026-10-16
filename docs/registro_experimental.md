# Registro Experimental — Trabalho Final INF 791 / PLN

**Projeto:** Impacto do pré-processamento linguístico na recuperação semântica de documentos científicos  
**Base:** AmazoniaExpert.IA / SPAmazon-QA  
**Início dos experimentos:** 08/10/2026

---

## 1. Objetivo deste registro

Este documento registra decisões metodológicas, inconsistências encontradas,
resultados intermediários e alterações realizadas durante a execução dos experimentos.

O objetivo é garantir rastreabilidade e evitar que decisões tomadas durante
o desenvolvimento sejam perdidas ou reconstruídas apenas posteriormente.

---

# 2. Auditoria do corpus P0

## 2.1 Banco vetorial original

O banco vetorial utilizado como baseline foi preservado a partir de:

`C:\TCCII\VECTOR_DB`

Foi criada uma cópia de trabalho em:

`C:\PLN_EXPERIMENTOS\VECTOR_DB_P0_FRESH`

O banco contém:

- 6.900 chunks;
- 6.900 IDs únicos;
- 38 documentos canônicos;
- nenhum documento vazio;
- nenhum registro sem metadados.

Todos os documentos armazenados apresentam a estrutura textual utilizada
na vetorização original:

`Chapter + Section + Content`

O modelo de embeddings da baseline é:

`sentence-transformers/all-mpnet-base-v2`

---

## 2.2 Inconsistência nos metadados dos Cross Chapters

Durante a auditoria foi identificado que o campo `chapter_number` do banco
original não distingue os Cross Chapters dos capítulos regulares:

- Chapter 1 → `chapter_number = "1"`
- Cross Chapter 1 → `chapter_number = "1"`
- Chapter 2 → `chapter_number = "2"`
- Cross Chapter 2 → `chapter_number = "2"`

Entretanto, o campo `source` distingue corretamente os documentos.

Por esse motivo, no novo experimento a identificação canônica do documento
é derivada prioritariamente de `source`, preservando os metadados originais
sem modificá-los.

Foram obtidos:

- Chapter 1: 243 chunks
- Cross Chapter 1: 61 chunks
- Chapter 2: 229 chunks
- Cross Chapter 2: 18 chunks

Após canonicalização, foram identificados corretamente os 38 documentos.

---

# 3. Validação do SPAmazon-QA

O SPAmazon-QA contém:

- 130 perguntas;
- 130 IDs únicos;
- 39 grafias distintas para `capitulo_alvo`;
- 38 documentos canônicos após normalização;
- 53 perguntas Direct;
- 77 perguntas Indirect.

Distribuição de dificuldade:

- Easy: 7
- Medium-Low: 28
- Medium-High: 16
- Hard: 79

A equivalência:

`Capítulo CC2 = Capítulo Cross Chapter 2 = cross_chapter_2`

foi validada antes da execução dos experimentos.

Todos os capítulos-alvo das 130 perguntas possuem correspondência no corpus P0.

---

# 4. Reprodução da baseline P0

## 4.1 Configuração

A baseline P0 utiliza:

- corpus original com 6.900 chunks;
- embeddings `all-mpnet-base-v2`;
- ChromaDB;
- consulta original sem novo pré-processamento linguístico;
- recuperação Top-10 para o novo experimento.

O Top-5 é mantido como ponto de comparação com a avaliação realizada no TCC.

---

## 4.2 Resultados P0

| Métrica | Resultado |
|---|---:|
| Hit@1 | 103/130 — 79,23% |
| Hit@3 | 117/130 — 90,00% |
| Hit@5 | 121/130 — 93,08% |
| Hit@10 | 124/130 — 95,38% |
| MRR@10 | 0,8507 |

---

## 4.3 Comparação com o resultado histórico do TCC

No experimento registrado no TCC, o indicador operacional de Recall@5
apresentou:

- 118 sucessos;
- 12 falhas;
- 90,8% de recuperação do capítulo de origem.

Na reprodução atual da P0 foram obtidos:

- 121 sucessos;
- 9 falhas;
- Hit@5 = 93,08%.

Houve concordância entre o resultado histórico e a reprodução atual em:

**127 das 130 perguntas (97,69%).**

As divergências ocorreram exclusivamente nas questões:

- ID 96
- ID 97
- ID 98

As três perguntas têm como capítulo de origem o **Annex II**.

Na base P0 atualmente preservada, o Annex II foi recuperado na primeira
posição para as três consultas.

### Interpretação

A divergência sugere uma diferença relacionada especificamente ao estado
do Annex II na base/indexação utilizada durante a avaliação histórica do TCC.

Não é possível, com os artefatos atualmente disponíveis, determinar se:

- o Annex II foi indexado posteriormente;
- houve reconstrução do ChromaDB;
- ocorreu alguma alteração do índice entre as execuções;
- ou outra diferença de estado da base produziu os resultados históricos.

Portanto, essa diferença será registrada como uma divergência de reprodução,
sem atribuição causal não comprovada.

Para o novo experimento, P0–P4 utilizarão os mesmos 6.900 chunks,
garantindo comparação controlada entre as variantes.

---

# 5. Caso sentinela — Questão 11

A Questão 11 foi definida como caso sentinela para análise de relações temporais.

A consulta solicita atividades econômicas que se expandiram na Amazônia
**"since the 1970s"**.

Entretanto, na baseline P0, os primeiros resultados foram predominantemente
provenientes do:

`Chapter 11 — Economic Drivers in the Amazon from the 19th Century to the 1970s`

Resultados P0:

- Rank 1: Chapter 11
- Rank 2: Chapter 11
- Rank 3: Chapter 11
- Rank 4: Chapter 11
- Rank 5: Chapter 11
- Rank 6: Chapter 11
- Rank 7: Chapter 14
- Rank 8: Chapter 11
- Rank 9: Chapter 11
- Rank 10: Chapter 11

O capítulo-alvo, Chapter 17, não apareceu no Top-10.

Esse caso evidencia uma possível limitação da recuperação densa na representação
de relações temporais:

`since the 1970s` ≠ `to the 1970s`

O caso será acompanhado nas variantes P1–P4 para verificar se as transformações
linguísticas alteram positiva ou negativamente o ranking.

---

# 6. Decisões metodológicas consolidadas

1. O banco original do TCC nunca será modificado.
2. P0 representa o texto armazenado originalmente no ChromaDB.
3. Todos os experimentos utilizarão os mesmos 6.900 chunks.
4. A identidade canônica do documento será derivada de `source`.
5. O `chapter_number` original será preservado para auditoria.
6. Os capítulos-alvo nunca serão utilizados como entrada da recuperação.
7. P0–P4 serão comparados com Top-10.
8. Hit@1, Hit@3, Hit@5, Hit@10 e MRR@10 serão as métricas principais.
9. Relações temporais, negações, quantidades e comparações serão acompanhadas
   qualitativamente.
10. Nenhuma conclusão causal será atribuída a divergências históricas sem
    evidência suficiente.

---

# 7. Próximos passos

- implementar P1 — lowercase;
- implementar P2 — remoção controlada de stopwords;
- implementar P3 — lematização;
- implementar P4 — stemming;
- validar linguisticamente as transformações antes da indexação;
- construir quatro novas coleções;
- executar as 130 consultas em P1–P4;
- comparar resultados pareados com P0.


## 8.1 Saída da validação linguística

A saída completa da inspeção manual das variantes P0–P4 foi preservada em:

`results/runs/preprocessing_validation.txt`

Os exemplos avaliados cobriram:

- temporalidade;
- temporalidade oposta;
- negação;
- comparação;
- quantidade e siglas.

A inspeção foi realizada antes da construção dos índices experimentais P1–P4.


## 8.2 Congelamento das regras de pré-processamento

Após a inspeção manual das variantes, as regras de pré-processamento foram
consideradas adequadas para a execução experimental.

Foram confirmadas as seguintes propriedades:

- P0 mantém o texto original;
- P1 aplica somente lowercase;
- P2 aplica lowercase e remoção controlada de stopwords;
- P3 aplica lowercase e lematização;
- P4 aplica lowercase e Porter stemming;
- números permanecem preservados;
- operadores críticos de temporalidade, negação, quantificação e comparação
  permanecem preservados quando aplicável.

Entre os operadores explicitamente verificados estão:

`since`, `before`, `not`, `same`, `all`, `between`, `and`,
`greater` e `than`.

A saída completa da inspeção foi armazenada em:

`results/runs/preprocessing_validation_final.txt`

A implementação congelada encontra-se em:

`src/preprocess.py`

O hash SHA-256 da versão utilizada nos experimentos foi armazenado em:

`results/runs/preprocess_hash.txt`

A partir deste ponto, as regras de pré-processamento não serão modificadas
com base nos resultados de recuperação, evitando ajustes pós-hoc das variantes.

## 8.3 Testes automatizados do pré-processamento

Além da inspeção manual das transformações P0–P4, foi criada uma suíte
automatizada de testes com `pytest`.

Foram verificados:

- preservação integral do texto em P0;
- aplicação de lowercase em P1;
- preservação de relações temporais;
- preservação de negação;
- preservação de operadores de comparação;
- preservação de intervalos e valores numéricos;
- remoção de stopwords em P2;
- lematização em P3;
- stemming em P4;
- garantia de que nenhuma variante produz texto vazio.

Resultado:

`10 passed`

A saída completa da execução foi armazenada em:

`results/runs/preprocessing_tests.txt`

Os testes foram executados antes da avaliação comparativa dos rankings P0–P4.




# 9. Construção dos corpora derivados

A partir dos 6.900 chunks preservados da baseline P0, foram gerados quatro
corpora derivados utilizando as regras de pré-processamento congeladas previamente.

Todas as variantes preservaram:

- 6.900 chunks;
- 6.900 IDs únicos;
- 38 documentos canônicos;
- os mesmos metadados do P0;
- zero textos vazios.

Resultados da transformação textual:

| Variante | Chunks | Redução de caracteres |
|---|---:|---:|
| P1 | 6.900 | 0,00% |
| P2 | 6.900 | 11,28% |
| P3 | 6.900 | 2,98% |
| P4 | 6.900 | 11,06% |

O fato de P1 apresentar redução de 0% é esperado, pois a transformação
lowercase altera caracteres, mas não o comprimento do texto.

Hashes SHA-256:

- P1: `0e1efcd0f921f08956529d89eb0ff267d221fbf494458c655e5e7e6eff1c3c6a`
- P2: `48dc79cf004d56c5f25905532564fc8a0f4018f6c15fdbe241c2e6b2f8103447`
- P3: `ae8b5ad596327372a3b5b6cf8e92a422db99ac45daae7e8f288e86e325302e99`
- P4: `70fd5435015ba57aea468b8148190c1cc619e69796b8b33c6871cbb55ca62ded`

A auditoria completa foi armazenada em:

`results/runs/preprocessed_corpora_audit.json`

## 9.1 Reconstrução controlada da baseline

Além dos índices P1–P4, será construído um novo índice P0 experimental
a partir de `p0_chunks.jsonl`.

O banco vetorial original do TCC permanece preservado e foi utilizado para
a etapa de reprodução histórica.

A reconstrução de P0 é necessária para que P0–P4 sejam indexados sob
condições idênticas de software, ordem de inserção, batch size e construção
do índice HNSW. Dessa forma, a variável experimental permanece restrita à
transformação linguística aplicada ao texto.

## 10. Seleção prévia dos casos críticos para análise downstream

Antes da obtenção dos resultados comparativos P1–P4, foi congelado um
subconjunto de casos críticos para análise do impacto da recuperação sobre
a geração final de respostas.

A seleção utilizou exclusivamente resultados históricos do
AmazoniaExpert.IA e seguiu a regra:

`nota histórica do Juiz LLM ∈ {1, 2, 3} OU falha histórica de recuperação`

Resultados:

- casos com nota histórica 1–3: 23;
- casos com falha histórica de recuperação: 12;
- interseção entre os grupos: 3;
- casos críticos únicos: 32.

IDs pertencentes às duas categorias:

`11, 102, 124`

Conjunto final congelado:

`9, 11, 15, 27, 34, 35, 36, 53, 58, 59, 63, 65, 67, 72, 77, 83, 90, 96, 97, 98, 99, 100, 102, 104, 105, 106, 110, 116, 117, 124, 125, 126`

Essa seleção foi realizada antes da inspeção dos resultados experimentais
das variantes P1–P4, evitando seleção pós-hoc ou cherry-picking.

Arquivos produzidos:

- `data/reference/downstream_critical_cases.jsonl`
- `results/tables/downstream_critical_cases.csv`
- `results/runs/downstream_cases_selection.json`


## 12. Construção dos índices vetoriais controlados

Foram construídos cinco índices vetoriais independentes correspondentes
às condições P0, P1, P2, P3 e P4.

Cada índice contém:

- 6.900 chunks;
- embeddings de 768 dimensões;
- modelo `sentence-transformers/all-mpnet-base-v2`;
- ChromaDB 1.5.5;
- coleção `langchain`;
- batch de indexação igual a 128.

Os cinco corpora apresentaram os mesmos IDs, a mesma ordem de inserção
e os mesmos metadados. A única diferença sistemática entre as condições
foi a representação textual aplicada aos chunks.

Ambiente:

- Python 3.13.3;
- ChromaDB 1.5.5;
- langchain-huggingface 1.2.1;
- sentence-transformers 5.3.0.

Os índices foram armazenados fora do OneDrive em:

`C:\PLN_EXPERIMENTOS\VECTOR_DB_CONTROLLED`

A auditoria completa encontra-se em:

`results/runs/controlled_vector_dbs_build.json`

A partir desta etapa, os índices P0–P4 foram considerados congelados
para a execução do experimento principal.

## 13. Resultados do experimento controlado de recuperação

Após o congelamento dos corpora, consultas e índices vetoriais, foi executado
o experimento principal de recuperação semântica.

Foram realizadas:

- 130 consultas por variante;
- 5 condições experimentais (P0–P4);
- 650 consultas no total;
- recuperação dos 10 chunks mais próximos por consulta;
- 6.500 posições de ranking analisadas.

Todos os experimentos utilizaram o mesmo encoder
`sentence-transformers/all-mpnet-base-v2`, dimensionalidade 768 e os mesmos
6.900 chunks por índice.

### 13.1 Resultados globais

Os resultados globais foram:

| Variante | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 |
|---|---:|---:|---:|---:|---:|
| P0 | 79,23% | 90,00% | 93,08% | 95,38% | 0,8507 |
| P1 | 79,23% | 90,00% | 93,08% | 95,38% | 0,8507 |
| P2 | 70,77% | 80,77% | 83,08% | 89,23% | 0,7657 |
| P3 | 73,85% | 89,23% | 90,77% | 93,85% | 0,8152 |
| P4 | 60,77% | 73,08% | 80,77% | 85,38% | 0,6909 |

A condição P0 apresentou o melhor desempenho global, empatada com P1 em
todas as métricas.

Nenhuma das estratégias tradicionais adicionais de pré-processamento
(P2–P4) produziu melhora global em relação ao texto original.

Os resultados indicam que, neste corpus e utilizando o encoder
`all-mpnet-base-v2`, transformações linguísticas clássicas podem alterar
negativamente a representação utilizada na recuperação densa.

Essa conclusão deve ser restrita ao desenho experimental utilizado e não
generalizada para outros encoders, corpora ou arquiteturas de recuperação.

### 13.2 Diferenças em relação à baseline P0

As diferenças absolutas em relação a P0 foram:

| Variante | Δ Hit@1 | Δ Hit@3 | Δ Hit@5 | Δ Hit@10 | Δ MRR@10 |
|---|---:|---:|---:|---:|---:|
| P1 | 0,00 pp | 0,00 pp | 0,00 pp | 0,00 pp | 0,0000 |
| P2 | -8,46 pp | -9,23 pp | -10,00 pp | -6,15 pp | -0,0850 |
| P3 | -5,38 pp | -0,77 pp | -2,31 pp | -1,54 pp | -0,0356 |
| P4 | -18,46 pp | -16,92 pp | -12,31 pp | -10,00 pp | -0,1598 |

Entre as transformações linguísticas adicionais, P3 (lematização) foi a
condição que permaneceu mais próxima do desempenho da baseline.

P2, baseada na remoção controlada de stopwords, apresentou redução mais
acentuada, especialmente em Hit@3 e Hit@5.

P4, baseada em stemming, apresentou a maior degradação global, com redução
de 18,46 pontos percentuais em Hit@1 e de 12,31 pontos percentuais em
Hit@5.

### 13.3 Efeito do lowercase isolado — P1

P1 apresentou exatamente os mesmos valores de P0 em todas as métricas:

- Hit@1: 79,23%;
- Hit@3: 90,00%;
- Hit@5: 93,08%;
- Hit@10: 95,38%;
- MRR@10: 0,8507.

A análise pareada por questão mostrou ainda:

- 124 perguntas com o mesmo primeiro rank relevante de P0;
- 6 perguntas que permaneceram sem o capítulo-alvo no Top-10;
- nenhuma melhora;
- nenhuma piora;
- nenhum novo acerto;
- nenhuma perda de acerto.

Assim, dentro deste experimento, a conversão isolada para lowercase foi
neutra quanto à eficácia de recuperação medida pelas métricas adotadas.

Esse resultado não implica necessariamente que todos os rankings completos
sejam textualmente idênticos, mas demonstra que a posição do primeiro
fragmento pertencente ao documento-alvo permaneceu inalterada nas 130
consultas.

### 13.4 Remoção controlada de stopwords — P2

P2 apresentou redução considerável em todas as métricas.

Em Hit@5, o desempenho caiu de:

`93,08% -> 83,08%`

correspondendo a uma redução de 10 pontos percentuais.

As mudanças individuais em relação a P0 foram:

- 5 perguntas com melhora de rank;
- 22 perguntas com piora de rank;
- 88 com o mesmo rank;
- 1 novo acerto no Top-10;
- 9 perdas de acerto no Top-10;
- 5 perguntas permaneceram sem acerto no Top-10.

Especificamente em Hit@5 ocorreram:

- 14 perdas de acerto;
- 1 ganho de acerto.

Isso indica uma assimetria predominantemente desfavorável.

A redução média do comprimento textual produzida por P2 foi de 11,28% no
corpus e 21,58% nas consultas. Entretanto, os resultados não permitem
atribuir a queda apenas à redução de comprimento. A transformação também
altera a estrutura lexical e contextual fornecida ao encoder.

### 13.5 Lematização — P3

P3 apresentou o melhor resultado entre as variantes que alteraram
linguisticamente o conteúdo além do lowercase.

Os valores foram:

- Hit@1: 73,85%;
- Hit@3: 89,23%;
- Hit@5: 90,77%;
- Hit@10: 93,85%;
- MRR@10: 0,8152.

Em comparação a P0, a redução em Hit@5 foi de apenas 2,31 pontos
percentuais.

As mudanças de rank foram:

- 6 melhorias;
- 13 pioras;
- 103 permanências no mesmo rank;
- 2 perdas de acerto no Top-10;
- nenhuma nova entrada no Top-10;
- 6 falhas permaneceram inalteradas.

Em Hit@5 foram observadas:

- 5 perdas;
- 2 ganhos.

Portanto, embora P3 não tenha superado P0 globalmente, seu impacto foi
substancialmente menor do que o observado em P2 e P4.

### 13.6 Porter stemming — P4

P4 apresentou a maior degradação entre todas as condições.

Os resultados foram:

- Hit@1: 60,77%;
- Hit@3: 73,08%;
- Hit@5: 80,77%;
- Hit@10: 85,38%;
- MRR@10: 0,6909.

As mudanças de rank em relação a P0 foram:

- 6 melhorias;
- 26 pioras;
- 79 permanências no mesmo rank;
- 13 perdas de acerto no Top-10;
- nenhuma nova entrada no Top-10;
- 6 falhas permaneceram sem alteração.

Em Hit@5 ocorreram:

- 18 perdas;
- 2 ganhos.

Os resultados sugerem que a redução morfológica agressiva produzida pelo
Porter Stemmer remove ou modifica informação lexical relevante para as
representações densas utilizadas pelo MPNet.

Não se conclui que stemming seja inadequado para recuperação de informação
em geral. A evidência é específica ao encoder denso, corpus e protocolo
avaliados neste trabalho.

### 13.7 Análise por tipo de pergunta

A análise de Hit@5 por tipo mostrou:

| Variante | Direct | Indirect |
|---|---:|---:|
| P0 | 94,34% | 92,21% |
| P1 | 94,34% | 92,21% |
| P2 | 79,25% | 85,71% |
| P3 | 92,45% | 89,61% |
| P4 | 90,57% | 74,03% |

P3 permaneceu relativamente próximo da baseline nos dois tipos.

P4 apresentou comportamento particularmente desfavorável nas perguntas
Indirect, em que Hit@5 caiu de 92,21% para 74,03%.

Como as perguntas Indirect tendem a demandar maior composição semântica,
esse comportamento será investigado qualitativamente, sem assumir que o
tipo da pergunta seja isoladamente a causa da degradação.

### 13.8 Análise por dificuldade

Hit@5 por nível de dificuldade:

| Variante | Easy | Medium-Low | Medium-High | Hard |
|---|---:|---:|---:|---:|
| P0 | 85,71% | 92,86% | 100,00% | 92,41% |
| P1 | 85,71% | 92,86% | 100,00% | 92,41% |
| P2 | 71,43% | 78,57% | 93,75% | 83,54% |
| P3 | 85,71% | 89,29% | 100,00% | 89,87% |
| P4 | 71,43% | 92,86% | 100,00% | 73,42% |

A maior queda de P4 ocorreu nas perguntas Hard, que constituem também o
maior grupo do SPAmazon-QA.

As categorias possuem tamanhos diferentes, especialmente Easy (N=7), e
por isso as análises estratificadas são interpretadas principalmente de
forma descritiva.

### 13.9 Análise dos 32 casos críticos downstream

Os 32 casos críticos foram selecionados previamente, utilizando apenas
informações históricas do TCC, antes da observação dos resultados P1–P4.

Por isso, eles constituem um subconjunto pré-definido para análise de
causa-raiz, e não uma amostra escolhida após observar quais casos favoreceram
alguma variante.

Resultados:

| Variante | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 |
|---|---:|---:|---:|---:|---:|
| P0 | 65,63% | 71,88% | 71,88% | 81,25% | 0,7024 |
| P1 | 65,63% | 71,88% | 71,88% | 81,25% | 0,7024 |
| P2 | 50,00% | 65,63% | 65,63% | 71,88% | 0,5764 |
| P3 | 62,50% | 78,13% | 78,13% | 78,13% | 0,6927 |
| P4 | 50,00% | 59,38% | 71,88% | 71,88% | 0,5781 |

Nesse subconjunto, P3 apresenta um comportamento particularmente
interessante.

Embora não tenha superado P0 globalmente, Hit@5 aumentou nos casos críticos:

`P0: 71,88%`
`P3: 78,13%`

Esse resultado não significa superioridade global de P3. O subconjunto foi
construído deliberadamente com casos problemáticos e, portanto, não representa
a distribuição completa das 130 perguntas.

Ele demonstra, entretanto, que determinadas consultas podem se beneficiar
da lematização mesmo quando a tendência agregada do benchmark é negativa.

Esse comportamento justifica a análise downstream com geração de respostas.

### 13.10 Casos 65 e 83

Os casos 65 e 83 apresentam um padrão particularmente útil para a análise
de causa-raiz.

Nos dois casos:

- P0: primeiro documento-alvo na posição 6;
- P1: posição 6;
- P2: documento-alvo ausente do Top-10;
- P3: posição 3;
- P4: posição 2.

Assim, P3 e P4 transformam esses casos de falha em Hit@5 para sucesso em
Hit@5.

Esses casos serão utilizados na análise downstream para verificar se a
melhora na posição de recuperação resulta também em melhora da resposta
gerada pelo ClimateChat.

### 13.11 Caso 124

O Caso 124 apresenta uma situação distinta.

O capítulo-alvo estava ausente do Top-10 em P0 e P1.

Em P2, passou a ocupar a posição 3:

- P0: >10;
- P1: >10;
- P2: 3;
- P3: >10;
- P4: >10.

Portanto, P2 produziu um novo acerto de recuperação para esse caso, apesar
de apresentar pior desempenho global.

Isso evidencia a importância de analisar tanto métricas agregadas quanto
casos individuais: uma transformação globalmente desfavorável pode corrigir
consultas específicas.

O Caso 124 será também submetido à análise downstream de geração.

### 13.12 Caso sentinela 11 — restrição temporal

O Caso 11 foi previamente selecionado como caso sentinela devido à
restrição temporal presente na expressão:

`since the 1970s`

O documento-alvo é o Chapter 17.

Nenhuma variante recuperou o Chapter 17 dentro do Top-10.

Em P0:

- posições 1–6: Chapter 11;
- posição 7: Chapter 14;
- posições 8–10: Chapter 11.

P1 reproduziu o mesmo comportamento.

Em P2, nove dos dez resultados pertencem ao Chapter 11 e um ao Chapter 14.

Em P3, todos os dez resultados pertencem ao Chapter 11.

Em P4 ocorreu uma mudança acentuada: oito das dez primeiras posições
pertencem ao Chapter 18, uma ao Chapter 11 e o Chapter 17 continua ausente.

Assim, a preservação explícita do termo `since` nas regras de
pré-processamento não foi suficiente para corrigir a recuperação.

Esse resultado sugere que o problema não decorre simplesmente da remoção
do operador temporal. A forte proximidade temática entre os fragmentos
concorrentes continua dominando a representação vetorial.

O caso evidencia uma limitação relevante da recuperação semântica densa:
similaridade temática elevada não garante representação adequada de relações
semânticas direcionais, como a diferença entre:

`since the 1970s`

e

`to the 1970s`.

Essa interpretação será tratada como evidência qualitativa e não como uma
conclusão geral sobre todos os embeddings densos.

### 13.13 Testes estatísticos pareados

Como as cinco variantes são avaliadas exatamente sobre as mesmas 130
perguntas, as comparações são pareadas.

Para Hit@1, Hit@3, Hit@5 e Hit@10 é utilizado o teste exato de McNemar,
considerando as mudanças de sucesso para falha e de falha para sucesso.

Para MRR@10 é utilizado o teste de Wilcoxon para amostras pareadas.

Para controlar o erro decorrente de múltiplas comparações, é aplicada a
correção de Holm-Bonferroni.

Adotando de forma conservadora as 20 comparações P1–P4 × cinco métricas
como uma única família:

- P1 não apresenta qualquer diferença em relação a P0;
- P2 apresenta diferença estatisticamente detectável em Hit@5 e MRR@10
  após correção;
- P3 não mantém diferença estatisticamente significativa após a correção
  conjunta das 20 comparações;
- P4 apresenta diferenças estatisticamente significativas em todas as
  cinco métricas.

Para P2:

- Hit@5: p ajustado por Holm ≈ 0,0146;
- MRR@10: p ajustado por Holm ≈ 0,0153.

Para P4:

- Hit@1: p ajustado < 0,001;
- Hit@3: p ajustado < 0,001;
- Hit@5: p ajustado ≈ 0,0064;
- Hit@10: p ajustado ≈ 0,0042;
- MRR@10: p ajustado < 0,001.

P3 apresentou redução descritiva, especialmente em Hit@1 e MRR@10, mas
as diferenças não permaneceram significativas sob a correção conservadora
aplicada às 20 comparações.

Os valores completos dos testes são armazenados em:

`results/tables/controlled_statistical_tests_vs_p0.csv`

### 13.14 Interpretação geral

O experimento não sustenta a hipótese de que operações tradicionais de
normalização linguística necessariamente favoreçam a recuperação semântica
com embeddings contextuais.

P0, sem novo pré-processamento, apresentou o melhor resultado global,
empatado com P1.

A ausência de diferença entre P0 e P1 mostra que lowercase isolado foi
neutro no protocolo adotado.

A remoção de stopwords em P2 degradou a recuperação global, indicando que
palavras funcionais podem contribuir para a representação contextual produzida
pelo encoder mesmo quando parecem pouco informativas em abordagens lexicais
tradicionais.

A lematização P3 apresentou impacto global relativamente pequeno e mostrou
ganhos localizados entre os casos críticos, o que sugere um comportamento
dependente da consulta.

O stemming P4 apresentou a maior degradação, especialmente em perguntas
Indirect e Hard, indicando que transformações morfológicas agressivas podem
prejudicar a geometria semântica esperada pelo modelo de embeddings.

Outro resultado relevante é que o grau de redução textual não explica
isoladamente o desempenho. P2 e P4 produziram reduções de tamanho de ordem
semelhante no corpus, porém P4 apresentou uma degradação substancialmente
maior. Assim, o tipo de transformação lexical parece ser mais importante
do que simplesmente a quantidade de texto removida.

De forma geral, os resultados favorecem a preservação da linguagem natural
original para recuperação com `all-mpnet-base-v2`, ao mesmo tempo em que
mostram que algumas transformações, particularmente a lematização, podem
beneficiar casos individuais específicos.

A etapa seguinte avaliará se essas mudanças de recuperação possuem impacto
downstream sobre a geração de respostas pelo ClimateChat nos 32 casos
críticos previamente congelados.

### 13.15 Validação computacional da análise

A análise quantitativa foi reproduzida automaticamente pelo script:

`scripts/analyze_controlled_results.py`

A execução confirmou:

- 650 observações pergunta-variante;
- 32 casos críticos downstream;
- métricas globais P0–P4;
- alterações pareadas de rank;
- testes exatos de McNemar para Hit@k;
- teste de Wilcoxon pareado para MRR@10;
- correção de Holm-Bonferroni.

Para interpretação inferencial principal foi utilizada a correção
`p_holm_all_20`, considerando conjuntamente as 20 comparações
P1–P4 × cinco métricas.

Sob α = 0,05:

- P1 não diferiu de P0;
- P2 apresentou diferença significativa em Hit@5 e MRR@10;
- P3 não apresentou diferenças significativas após correção;
- P4 apresentou diferenças significativas em Hit@1, Hit@3, Hit@5,
  Hit@10 e MRR@10.

A saída consolidada da análise encontra-se em:

`results/runs/controlled_analysis_summary.txt`

## 14. Preparação da análise downstream do AmazoniaExpert.IA

Após a conclusão da avaliação de recuperação P0–P4, foi preparada uma
análise downstream destinada a verificar se alterações no ranking de recuperação
se propagam para a qualidade da resposta final gerada pelo sistema RAG.

A análise utiliza exclusivamente os 32 casos críticos previamente congelados.

Para cada caso são avaliadas as cinco condições:

- P0;
- P1;
- P2;
- P3;
- P4.

Portanto, são previstas 160 novas respostas do AmazoniaExpert.IA.

### 14.1 Controle da variável experimental

A etapa de geração não executa uma nova busca vetorial.

Os rankings Top-5 utilizados foram previamente congelados em:

`results/cases/downstream_retrieval_top5.csv`

Para cada posição recuperada, o `chunk_id` é utilizado para localizar o
conteúdo correspondente no corpus original P0.

Dessa forma, P1–P4 são utilizados somente para determinar quais fragmentos
são recuperados. O texto transformado por lowercase, remoção de stopwords,
lematização ou stemming não é fornecido ao modelo gerador.

O contexto entregue ao ClimateChat contém sempre o texto original do chunk.

A pergunta entregue ao gerador também corresponde sempre à pergunta
original do SPAmazon-QA.

Assim, a única diferença sistemática entre P0–P4 na etapa de geração é o
conjunto e a ordenação dos cinco fragmentos recuperados.

### 14.2 Configuração do AmazoniaExpert.IA

Foi reproduzida a configuração utilizada na bateria experimental original
do TCC, presente no script `gerar_respostas_climate2.py`.

Modelo:

`ClimateChat.i1-Q4_K_M.gguf`

Parâmetros:

- temperature = 0.1;
- max_tokens = 2048;
- n_ctx = 8192;
- n_gpu_layers = 0;
- repeat_penalty = 1.15;
- top_p = 0.9;
- stop tokens = `</s>`, `Question:` e `[INST]`.

Foi utilizado exclusivamente o prompt RAG do AmazoniaExpert.IA.

Nenhuma resposta ClimateChat Zero-Shot é gerada nesta etapa.

### 14.3 Validação prévia

Antes da geração foi executada uma auditoria automática das entradas.

Resultados:

- corpus P0: 6.900 chunks;
- casos críticos: 32;
- linhas Top-5: 800;
- combinações questão-variante: 160;
- 32 IDs coincidentes entre seleção e recuperação;
- todos os 800 `chunk_id` recuperados encontrados no corpus P0;
- nenhuma nova recuperação vetorial executada.

A validação foi concluída sem erros antes do início da geração.


### 14.4 Controle de aleatoriedade da geração

Durante uma execução piloto da análise downstream, observou-se que
prompts idênticos podiam produzir respostas distintas devido à amostragem
do modelo gerador.

Como o objetivo desta etapa é isolar o efeito da alteração do contexto
recuperado, foi fixada `seed=42` nas novas gerações controladas.

Foram mantidos os demais parâmetros da bateria experimental original:

- temperature = 0.1;
- top_p = 0.9;
- repeat_penalty = 1.15;
- max_tokens = 2048;
- n_ctx = 8192.

As respostas produzidas antes da fixação da seed foram preservadas apenas
como execução piloto e não serão utilizadas na análise comparativa final.

A resposta histórica do TCC permanece disponível como referência externa,
enquanto a comparação experimental principal é realizada entre P0, P1,
P2, P3 e P4 sob a mesma seed fixa.


## 15. Geração downstream e auditoria das respostas P0–P4

Após a conclusão da recuperação controlada e a validação do protocolo de
determinismo, foi executada a etapa downstream do experimento.

O objetivo desta etapa é investigar se alterações produzidas pelo
pré-processamento na recuperação semântica podem se propagar para a resposta
final do AmazoniaExpert.IA.

A geração foi realizada somente para os 32 casos críticos previamente
selecionados e congelados.

Foram consideradas cinco condições:

- P0 — recuperação utilizando o texto original;
- P1 — lowercase;
- P2 — lowercase + remoção controlada de stopwords;
- P3 — lowercase + lematização;
- P4 — lowercase + Porter stemming.

Assim, foram previstas:

`32 perguntas × 5 variantes = 160 respostas RAG`

A execução foi concluída com:

- 160 respostas geradas;
- 32 questões distintas;
- 32 respostas para cada variante;
- nenhuma combinação questão-variante duplicada;
- nenhuma resposta vazia;
- `generation_seed = 42` em todas as respostas;
- protocolo único `downstream-rag-fixed-seed-v2`.

Os resultados brutos foram armazenados em:

`results/raw/downstream_responses_rag.csv`

e

`results/raw/downstream_responses_rag.jsonl`

A configuração completa da execução foi registrada em:

`results/runs/downstream_generation_run.json`


### 15.1 Arquitetura utilizada na geração

Todas as 160 respostas foram produzidas pelo AmazoniaExpert.IA, isto é,
pelo ClimateChat integrado ao pipeline RAG.

Não foram produzidas respostas ClimateChat zero-shot nesta etapa.

Também não foi realizada uma nova busca vetorial durante a geração.

Os Top-5 de cada combinação questão-variante foram consumidos diretamente
do ranking previamente congelado em:

`results/cases/downstream_retrieval_top5.csv`

O pipeline utilizado foi:

`consulta processada Pk -> Top-5 congelado -> IDs dos chunks -> texto
original P0 -> prompt RAG -> ClimateChat -> resposta`

Dessa forma, o texto transformado por P1, P2, P3 ou P4 foi utilizado
somente para determinar a recuperação.

O ClimateChat nunca recebeu chunks em lowercase, sem stopwords,
lematizados ou stemizados.

Após a seleção dos cinco `chunk_id`, o conteúdo correspondente foi
recuperado a partir do corpus P0 e fornecido ao gerador em sua forma
textual original.

A pergunta entregue ao ClimateChat também foi sempre a pergunta original
do SPAmazon-QA, e não sua versão pré-processada.

Essa decisão permite atribuir as diferenças entre as respostas ao contexto
recuperado, mantendo constantes as demais entradas do gerador.


### 15.2 Configuração do gerador

Foi utilizado o modelo:

`ClimateChat.i1-Q4_K_M.gguf`

integrado ao AmazoniaExpert.IA.

A configuração utilizada foi:

- temperature = 0.1;
- max_tokens = 2048;
- n_ctx = 8192;
- n_gpu_layers = 0;
- repeat_penalty = 1.15;
- top_p = 0.9;
- top_k = 40;
- seed = 42;
- stop tokens = `</s>`, `Question:` e `[INST]`.

A seed foi reinicializada em cada completion utilizando o protocolo:

`reset -> set_seed(42) -> create_completion(seed=42)`

Essa configuração foi adotada após um teste piloto demonstrar que manter a
seed apenas no construtor do modelo não era suficiente para garantir respostas
idênticas em chamadas sequenciais com prompts idênticos.


### 15.3 Controle de determinismo

Antes da execução completa foi utilizado o Caso 9 como teste de controle.

P0 e P1 apresentavam:

- os mesmos cinco `chunk_id`;
- o mesmo contexto;
- a mesma pergunta original;
- o mesmo prompt completo.

Com a reinicialização da seed em cada completion, P0 e P1 produziram
respostas textualmente idênticas.

O hash SHA-256 obtido para ambas foi:

`824d4089da46a66e6590e832222b0d696f1e381bff38a74485477ff4f440bc02`

O teste foi considerado aprovado antes da geração das 160 respostas.

Durante a auditoria posterior do conjunto completo, foram identificados
31 grupos nos quais duas ou mais variantes de uma mesma pergunta receberam
exatamente o mesmo prompt.

Em todos esses grupos, prompts idênticos produziram respostas idênticas.

Esse resultado confirma que o controle de aleatoriedade permaneceu efetivo
durante a execução completa e reduz o risco de atribuir à mudança de
pré-processamento diferenças causadas apenas pela amostragem do modelo.


### 15.4 Relação entre P0 e P1

P0 e P1 apresentaram o mesmo prompt em 31 dos 32 casos críticos.

Nesses 31 casos, as respostas também foram exatamente iguais.

A única exceção foi a Questão 58.

Na Q58, embora P0 e P1 já tivessem apresentado o mesmo desempenho nas
métricas baseadas na posição do primeiro documento-alvo, o conteúdo completo
do Top-5 não foi idêntico.

Em P0, os capítulos do Top-5 foram:

`4 | 4 | 4 | 28 | Annex I`

Em P1:

`4 | 4 | 4 | Annex I | 18`

Portanto, o lowercase não alterou a posição do primeiro documento relevante
nesse caso, mas modificou os fragmentos presentes nas posições inferiores do
ranking.

Essa observação é metodologicamente importante: igualdade em Hit@k ou no
primeiro rank relevante não implica necessariamente identidade de todo o
ranking recuperado.

Apesar de P0 e P1 apresentarem métricas globais idênticas no experimento
principal, pequenas alterações no conjunto de contexto ainda podem ocorrer.


### 15.5 Caso 11 — falha temporal persistente

O Caso 11 tem como capítulo-alvo o Chapter 17 e contém uma restrição
temporal importante associada à expressão:

`since the 1970s`

Na geração downstream, os cinco chunks utilizados em P0 foram todos
provenientes do Chapter 11:

`P0 -> 11 | 11 | 11 | 11 | 11`

P1 apresentou exatamente o mesmo contexto:

`P1 -> 11 | 11 | 11 | 11 | 11`

P2 também permaneceu inteiramente no Chapter 11:

`P2 -> 11 | 11 | 11 | 11 | 11`

P3 igualmente não corrigiu a recuperação:

`P3 -> 11 | 11 | 11 | 11 | 11`

P4 alterou substancialmente o contexto recuperado, porém todos os cinco
chunks passaram a pertencer ao Chapter 18:

`P4 -> 18 | 18 | 18 | 18 | 18`

Assim, nenhuma das cinco variantes forneceu ao gerador um chunk do
Chapter 17 dentro do Top-5.

O caso mostra que as operações de pré-processamento foram capazes de
alterar o tipo de erro de recuperação, especialmente em P4, mas não
resolveram a falha relacionada ao capítulo-alvo.

A avaliação pelo Juiz LLM será utilizada posteriormente para verificar
se essa mudança de contexto, mesmo sem recuperar o documento-alvo, produz
alguma alteração mensurável na qualidade da resposta.


### 15.6 Caso 65 — entrada do documento-alvo no Top-5

O Caso 65 tem como alvo o Cross Chapter 1.

Em P0, os cinco chunks vieram do Chapter 6:

`P0 -> 6 | 6 | 6 | 6 | 6`

P1 apresentou o mesmo contexto:

`P1 -> 6 | 6 | 6 | 6 | 6`

P2 também permaneceu restrito ao Chapter 6:

`P2 -> 6 | 6 | 6 | 6 | 6`

Em P3 ocorreu uma mudança relevante:

`P3 -> 6 | 6 | Cross Chapter 1 | 6 | 6`

Assim, o documento-alvo passou a integrar o contexto do gerador na terceira
posição.

Em P4:

`P4 -> 6 | Cross Chapter 1 | 4 | 6 | 6`

o documento-alvo passou para a segunda posição.

Devido ao problema histórico de metadados identificado anteriormente,
o campo `chapter_number` registra Cross Chapter 1 como `1`.

Por esse motivo, a identificação deste caso deve ser feita utilizando
preferencialmente o campo `source`, que confirma que os fragmentos das
posições indicadas pertencem ao arquivo:

`Part_I_Cap_01_Cross Chapter 1 The Amazon Carbon Budget.pdf`

Esse caso constitui um exemplo particularmente importante para a etapa
seguinte, pois P3 e P4 transformaram uma falha em Hit@5 em uma recuperação
que efetivamente fornece ao ClimateChat conteúdo do documento-alvo.

A avaliação downstream permitirá testar se essa melhora da recuperação
também produz uma melhora na qualidade da resposta final.


### 15.7 Caso 83 — aumento progressivo da presença do capítulo-alvo

O Caso 83 tem como alvo o Chapter 27.

Em P0:

`16 | 28 | 16 | 28 | 19`

nenhum fragmento do Chapter 27 foi enviado ao gerador.

P1 reproduziu o mesmo contexto.

P2 apresentou:

`16 | 16 | 16 | 16 | 16`

também sem qualquer fragmento do capítulo-alvo.

P3 modificou significativamente o contexto:

`16 | 19 | 27 | 27 | 28`

passando a incluir dois fragmentos do Chapter 27 nas posições 3 e 4.

P4 apresentou:

`28 | 27 | 27 | 27 | 27`

com quatro dos cinco fragmentos provenientes do capítulo-alvo.

Esse caso fornece um contraste particularmente útil para a análise
downstream.

Há uma progressão clara na presença de evidência proveniente do documento
correto:

- P0/P1: 0 de 5 chunks do alvo;
- P2: 0 de 5;
- P3: 2 de 5;
- P4: 4 de 5.

A etapa de julgamento permitirá verificar se o aumento da presença do
documento-alvo no contexto também se reflete em notas mais altas de
qualidade da resposta.


### 15.8 Caso 124 — ganho específico produzido por P2

O Caso 124 tem como alvo o Chapter 15.

P0 recuperou:

`19 | 19 | 19 | 19 | 19`

P1 apresentou o mesmo conjunto.

P3 também permaneceu restrito ao Chapter 19:

`19 | 19 | 19 | 19 | 19`

P4 apresentou:

`19 | 19 | 19 | 19 | 14`

sem inclusão do capítulo-alvo.

P2 foi a única variante que introduziu o Chapter 15 no contexto:

`19 | 19 | 15 | 19 | 17`

O documento-alvo aparece na terceira posição.

Esse resultado é particularmente relevante porque P2 apresentou pior
desempenho global que P0, mas corrigiu esta consulta específica.

O Caso 124 demonstra que uma transformação globalmente desfavorável pode
produzir ganhos localizados.

A análise pelo Juiz LLM permitirá investigar se esse ganho de recuperação
se traduz também em uma resposta de maior qualidade.


### 15.9 Caso 117 — convergência entre P0, P1 e P3

Na Questão 117, P0, P1 e P3 produziram exatamente o mesmo conjunto
ordenado de chunks.

Os três contextos foram compostos por cinco fragmentos do Chapter 11.

Consequentemente, os prompts enviados ao ClimateChat foram idênticos.

Sob o protocolo determinístico adotado, P0, P1 e P3 produziram também
exatamente a mesma resposta.

Esse caso funciona como um controle interno adicional do experimento:
quando a transformação linguística não altera efetivamente o conjunto e
a ordem dos documentos entregues ao gerador, a resposta downstream também
permanece inalterada.


### 15.10 Interpretação prévia da geração downstream

A etapa atual ainda não permite afirmar que uma variante produz respostas
melhores ou piores.

Até este ponto, a análise demonstra apenas que:

1. o pipeline downstream foi executado de forma controlada;
2. prompts idênticos produzem respostas idênticas;
3. alterações no pré-processamento podem modificar os documentos que
   compõem o Top-5;
4. essas mudanças alteram o contexto recebido pelo AmazoniaExpert.IA;
5. existem casos em que o documento-alvo entra ou sai da janela de
   contexto conforme a variante utilizada.

Os Casos 65, 83 e 124 são exemplos particularmente úteis de situações em
que uma variante introduz o documento-alvo no Top-5.

O Caso 11 representa uma situação complementar, na qual nenhuma variante
recupera o documento-alvo, embora P4 produza uma mudança substancial no
tipo de conteúdo fornecido ao gerador.

Esses resultados justificam a etapa seguinte do experimento: avaliar cada
resposta individualmente por meio do mesmo paradigma de Juiz LLM utilizado
no TCC.

A qualidade das respostas ainda não será inferida apenas a partir da
presença do capítulo-alvo.

Uma recuperação aparentemente melhor pode não necessariamente produzir
uma resposta melhor, e uma recuperação sem o capítulo-alvo pode ainda
conter fragmentos semanticamente suficientes para responder à pergunta.

Portanto, somente após o julgamento será possível analisar a cadeia:

`pré-processamento -> recuperação -> contexto RAG -> qualidade da resposta`


### 15.11 Próxima etapa

A próxima etapa consiste na avaliação das respostas geradas.

Serão submetidas ao Juiz LLM:

- 160 respostas controladas correspondentes a P0–P4;
- 32 respostas históricas do AmazoniaExpert.IA utilizadas no TCC.

Total previsto:

`192 avaliações`

Cada avaliação produzirá:

- nota Likert inteira de 1 a 5;
- justificativa técnica textual.

A escala Likert será mantida igual à utilizada no TCC, sem introdução de
valores intermediários, para preservar a comparabilidade metodológica.

As 32 respostas históricas serão reavaliadas pelo juiz atual e mantidas
separadas de suas notas históricas. Essa comparação será utilizada para
verificar possível variação do comportamento do Juiz LLM ao longo do tempo.

As novas notas P0–P4 serão então relacionadas aos resultados de recuperação,
permitindo investigar situações como:

- recuperação melhora e resposta melhora;
- recuperação melhora e resposta permanece equivalente;
- recuperação piora e resposta piora;
- recuperação muda sem alterar a avaliação final;
- capítulo-alvo permanece ausente, mas a resposta muda qualitativamente.
