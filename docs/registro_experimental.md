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