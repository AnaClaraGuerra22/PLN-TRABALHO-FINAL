# Registro Experimental — Trabalho Final INF 791 / PLN


**Projeto:** Impacto do pré-processamento linguístico na recuperação semântica de documentos científicos  

**Base:** AmazoniaExpert.IA / SPAmazon-QA  

**Início dos experimentos:** 08/10/2026  
**Última atualização:** 20/10/2026  
**Status atual:** experimento principal, análise downstream e extensão mecanística RQ3 concluídos; etapa experimental encerrada e resultados consolidados para redação do artigo.


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


\| Métrica | Resultado |

\|---|---:|

\| Hit@1 | 103/130 — 79,23% |

\| Hit@3 | 117/130 — 90,00% |

\| Hit@5 | 121/130 — 93,08% |

\| Hit@10 | 124/130 — 95,38% |

\| MRR@10 | 0,8507 |


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


1\. O banco original do TCC nunca será modificado.

2\. P0 representa o texto armazenado originalmente no ChromaDB.

3\. Todos os experimentos utilizarão os mesmos 6.900 chunks.

4\. A identidade canônica do documento será derivada de `source`.

5\. O `chapter_number` original será preservado para auditoria.

6\. Os capítulos-alvo nunca serão utilizados como entrada da recuperação.

7\. P0–P4 serão comparados com Top-10.

8\. Hit@1, Hit@3, Hit@5, Hit@10 e MRR@10 serão as métricas principais.

9\. Relações temporais, negações, quantidades e comparações serão acompanhadas

   qualitativamente.

10\. Nenhuma conclusão causal será atribuída a divergências históricas sem

    evidência suficiente.


---


# 7. Plano experimental definido antes das execuções P1–P4

Esta seção preserva o plano de execução definido naquele momento do experimento. As etapas listadas abaixo foram posteriormente concluídas e são documentadas nas Seções 8–16.


- implementar P1 — lowercase;

- implementar P2 — remoção controlada de stopwords;

- implementar P3 — lematização;

- implementar P4 — stemming;

- validar linguisticamente as transformações antes da indexação;

- construir quatro novas coleções;

- executar as 130 consultas em P1–P4;

- comparar resultados pareados com P0.


# 8. Validação e congelamento do pré-processamento

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


\| Variante | Chunks | Redução de caracteres |

\|---|---:|---:|

\| P1 | 6.900 | 0,00% |

\| P2 | 6.900 | 11,28% |

\| P3 | 6.900 | 2,98% |

\| P4 | 6.900 | 11,06% |


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


Além dos índices P1–P4, foi construído um novo índice P0 experimental

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


\| Variante | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 |

\|---|---:|---:|---:|---:|---:|

\| P0 | 79,23% | 90,00% | 93,08% | 95,38% | 0,8507 |

\| P1 | 79,23% | 90,00% | 93,08% | 95,38% | 0,8507 |

\| P2 | 70,77% | 80,77% | 83,08% | 89,23% | 0,7657 |

\| P3 | 73,85% | 89,23% | 90,77% | 93,85% | 0,8152 |

\| P4 | 60,77% | 73,08% | 80,77% | 85,38% | 0,6909 |


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


\| Variante | Δ Hit@1 | Δ Hit@3 | Δ Hit@5 | Δ Hit@10 | Δ MRR@10 |

\|---|---:|---:|---:|---:|---:|

\| P1 | 0,00 pp | 0,00 pp | 0,00 pp | 0,00 pp | 0,0000 |

\| P2 | -8,46 pp | -9,23 pp | -10,00 pp | -6,15 pp | -0,0850 |

\| P3 | -5,38 pp | -0,77 pp | -2,31 pp | -1,54 pp | -0,0356 |

\| P4 | -18,46 pp | -16,92 pp | -12,31 pp | -10,00 pp | -0,1598 |


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


\| Variante | Direct | Indirect |

\|---|---:|---:|

\| P0 | 94,34% | 92,21% |

\| P1 | 94,34% | 92,21% |

\| P2 | 79,25% | 85,71% |

\| P3 | 92,45% | 89,61% |

\| P4 | 90,57% | 74,03% |


P3 permaneceu relativamente próximo da baseline nos dois tipos.


P4 apresentou comportamento particularmente desfavorável nas perguntas

Indirect, em que Hit@5 caiu de 92,21% para 74,03%.


Como as perguntas Indirect tendem a demandar maior composição semântica,

esse comportamento será investigado qualitativamente, sem assumir que o

tipo da pergunta seja isoladamente a causa da degradação.


### 13.8 Análise por dificuldade


Hit@5 por nível de dificuldade:


\| Variante | Easy | Medium-Low | Medium-High | Hard |

\|---|---:|---:|---:|---:|

\| P0 | 85,71% | 92,86% | 100,00% | 92,41% |

\| P1 | 85,71% | 92,86% | 100,00% | 92,41% |

\| P2 | 71,43% | 78,57% | 93,75% | 83,54% |

\| P3 | 85,71% | 89,29% | 100,00% | 89,87% |

\| P4 | 71,43% | 92,86% | 100,00% | 73,42% |


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


\| Variante | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 |

\|---|---:|---:|---:|---:|---:|

\| P0 | 65,63% | 71,88% | 71,88% | 81,25% | 0,7024 |

\| P1 | 65,63% | 71,88% | 71,88% | 81,25% | 0,7024 |

\| P2 | 50,00% | 65,63% | 65,63% | 71,88% | 0,5764 |

\| P3 | 62,50% | 78,13% | 78,13% | 78,13% | 0,6927 |

\| P4 | 50,00% | 59,38% | 71,88% | 71,88% | 0,5781 |


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


Esses casos foram utilizados na análise downstream para verificar se a melhora na posição de recuperação também se propagava para a resposta gerada pelo ClimateChat. Os resultados finais são documentados na Seção 16.


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


O Caso 124 foi também submetido à análise downstream de geração; o resultado final é documentado na Seção 16.16.


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


A etapa downstream subsequente avaliou se essas mudanças de recuperação possuíam impacto sobre a geração de respostas pelo ClimateChat nos 32 casos críticos previamente congelados. Os resultados estão documentados nas Seções 15 e 16.


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

- stop tokens = `\</s>`, `Question:` e `[INST]`.


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

- stop tokens = `\</s>`, `Question:` e `[INST]`.


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


### 15.10 Interpretação prévia da geração downstream (antes do julgamento)


A etapa atual ainda não permite afirmar que uma variante produz respostas

melhores ou piores.


Até este ponto, a análise demonstra apenas que:


1\. o pipeline downstream foi executado de forma controlada;

2\. prompts idênticos produzem respostas idênticas;

3\. alterações no pré-processamento podem modificar os documentos que

   compõem o Top-5;

4\. essas mudanças alteram o contexto recebido pelo AmazoniaExpert.IA;

5\. existem casos em que o documento-alvo entra ou sai da janela de

   contexto conforme a variante utilizada.


Os Casos 65, 83 e 124 são exemplos particularmente úteis de situações em

que uma variante introduz o documento-alvo no Top-5.


O Caso 11 representa uma situação complementar, na qual nenhuma variante

recupera o documento-alvo, embora P4 produza uma mudança substancial no

tipo de conteúdo fornecido ao gerador.


Esses resultados justificaram a etapa seguinte do experimento: avaliar cada resposta individualmente pelo mesmo paradigma LLM-as-a-Judge e com reprodução literal do prompt utilizado no TCC. Como o modelo histórico não estava mais disponível para a conta atual, o avaliador precisou ser substituído, conforme documentado na Seção 16.1.


A qualidade das respostas ainda não será inferida apenas a partir da

presença do capítulo-alvo.


Uma recuperação aparentemente melhor pode não necessariamente produzir

uma resposta melhor, e uma recuperação sem o capítulo-alvo pode ainda

conter fragmentos semanticamente suficientes para responder à pergunta.


Portanto, somente após o julgamento será possível analisar a cadeia:


`pré-processamento -> recuperação -> contexto RAG -> qualidade da resposta`


### 15.11 Plano de julgamento definido após a geração


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


A etapa descrita nesta subseção foi posteriormente concluída integralmente. A execução e os resultados são apresentados a seguir.

---

## 16. Avaliação downstream pelo Juiz LLM


Após a conclusão da geração das respostas downstream para os 32 casos

críticos, foi realizada a avaliação semântica das respostas produzidas pelas

cinco variantes P0–P4.


A finalidade desta etapa não é estimar novamente o desempenho global do

AmazoniaExpert.IA sobre as 130 perguntas do SPAmazon-QA. O objetivo é analisar,

em um subconjunto previamente selecionado de casos críticos, se alterações na

recuperação semântica decorrentes do pré-processamento se propagam para a

qualidade da resposta final produzida pelo sistema RAG.


Foram avaliados:


- 160 resultados controlados, correspondentes a 32 questões × 5 variantes;

- 32 respostas históricas do AmazoniaExpert.IA utilizadas no TCC;

- total de 192 registros finais de avaliação.


As respostas históricas foram reavaliadas com o objetivo específico de mensurar

a sensibilidade dos resultados à substituição do modelo utilizado como Juiz LLM.


### 16.1 Substituição necessária do Juiz LLM


No TCC original, o paradigma LLM-as-a-Judge utilizou o modelo:


`llama-3.3-70b-versatile`


via Groq, com:


`temperature = 0.0`


e com a persona:


`Professor Doutor especialista na Amazônia`


O prompt efetivamente utilizado no código original

`C:\TCCII\JUIZ\juiz_climatechatrag.py` foi recuperado e preservado literalmente

no novo experimento.


A escala utilizada permaneceu:


1\. Incorreta;

2\. Macia, conforme o texto literal do código original;

3\. Parcial;

4\. Boa;

5\. Excelente.


Também foi preservado o formato JSON:


`{"nota": ..., "justificativa": "..."}`


Entretanto, durante a reprodução do protocolo, a API da Groq retornou HTTP 404

para o modelo histórico, indicando que `llama-3.3-70b-versatile` não estava

disponível para a conta utilizada no momento da nova execução.


Por esse motivo, foi necessária a substituição do avaliador por:


`openai/gpt-oss-120b`


mantendo-se constantes:


- o prompt original;

- a escala Likert de 1 a 5;

- `temperature = 0.0`;

- a entrada composta por pergunta, gabarito e resposta;

- o formato de saída JSON.


Para o novo modelo também foi explicitamente congelado:


`reasoning_effort = medium`


A substituição do modelo avaliador constitui uma diferença metodológica em

relação ao TCC e, portanto, as notas atuais não são tratadas como diretamente

equivalentes às notas históricas.


### 16.2 Avaliação cega


O Juiz LLM atual recebeu exclusivamente:


`pergunta + gabarito + resposta avaliada`


Não foram enviados ao juiz:


- identificador da variante P0–P4;

- indicação de resposta histórica ou controlada;

- nota histórica;

- metadados de recuperação;

- posição do capítulo-alvo;

- informações sobre o pré-processamento;

- informações da geração.


Assim, o modelo avaliador não tinha conhecimento de qual estratégia havia

produzido cada resposta.


Essa decisão reduz o risco de o julgamento ser influenciado pelo conhecimento

da condição experimental.


### 16.3 Deduplicação das avaliações


Os 192 registros finais continham respostas que, em alguns casos, eram

textualmente idênticas para a mesma pergunta e o mesmo gabarito.


Para evitar que duas entradas exatamente iguais recebessem avaliações

diferentes devido à variabilidade residual da API, foi adotada uma regra de

deduplicação:


`mesma pergunta + mesmo gabarito + mesma resposta = um único julgamento`


O veredito produzido foi posteriormente propagado para todas as condições

equivalentes.


Dos 192 registros finais:


- 154 correspondiam a entradas únicas para o juiz;

- 38 registros reutilizaram um julgamento já realizado.


A estratégia é especialmente relevante em condições como P0 e P1, que

frequentemente produziram exatamente a mesma resposta.


### 16.4 Auditoria computacional da avaliação


A execução foi concluída com:


- 192 registros finais;

- 160 avaliações referentes a P0–P4;

- 32 reavaliações de respostas históricas;

- 154 chamadas únicas ao Juiz LLM;

- 38 vereditos reutilizados;

- nenhuma justificativa vazia;

- todas as notas pertencentes ao conjunto `{1, 2, 3, 4, 5}`;

- modelo solicitado e retornado: `openai/gpt-oss-120b`.


O protocolo foi registrado como:


`judge-tcc-prompt-gptoss120b-dedup-v3`


O SHA-256 do arquivo final de avaliações foi:


`fff3d19e4a702b6b03efcd743457bc626f75019d1a767da89b4b63533d6d5fa6`


Os resultados foram armazenados em:


`results/raw/downstream_judge_evaluations.csv`


e


`results/raw/downstream_judge_evaluations.jsonl`


A auditoria da execução foi registrada em:


`results/runs/downstream_judge_run.json`


### 16.5 Sensibilidade à substituição do Juiz LLM


Para investigar o efeito da mudança do avaliador, foram utilizadas as mesmas

32 respostas históricas do AmazoniaExpert.IA.


Cada resposta possui:


- a nota atribuída originalmente no TCC pelo Llama-3.3-70B-Versatile;

- uma nova nota atribuída ao mesmo texto pelo GPT-OSS-120B.


No subconjunto de 32 casos críticos, as notas históricas apresentaram:


- média = 3,125;

- mediana = 3;

- desvio padrão = 0,793.


As mesmas respostas, reavaliadas pelo juiz atual, apresentaram:


- média = 1,969;

- mediana = 2;

- desvio padrão = 0,695.


A diferença média foi:


`1,969 - 3,125 = -1,156 ponto`


Das 32 respostas:


- 29 receberam nota menor com o juiz atual;

- 3 receberam exatamente a mesma nota;

- nenhuma recebeu nota maior.


Isso corresponde a:


- 90,6% de reduções;

- 9,4% de empates;

- 0% de aumentos.


A distribuição das diferenças foi:


\| Delta atual − histórico | Número de questões |

\|---:|---:|

\| -3 | 1 |

\| -2 | 6 |

\| -1 | 22 |

\| 0 | 3 |


O teste pareado de Wilcoxon resultou em:


`p ≈ 6,60 × 10⁻⁷`


indicando uma diferença sistemática entre os julgamentos produzidos pelos dois

modelos neste subconjunto.


Portanto, no conjunto analisado, o GPT-OSS-120B apresentou comportamento

substancialmente mais severo que o Llama-3.3-70B-Versatile utilizado no TCC.


Esse resultado impede que valores absolutos produzidos pelos dois juízes sejam

comparados diretamente.


As notas históricas permanecem como os resultados oficiais do experimento do

TCC, enquanto as notas atuais são utilizadas apenas dentro do novo protocolo

experimental.


### 16.6 Relação com a média histórica do AmazoniaExpert.IA


A média global histórica do AmazoniaExpert.IA reportada no TCC foi **4,14/5**, calculada sobre as 130 questões do SPAmazon-QA sob o protocolo de avaliação original e utilizando o Juiz LLM histórico.


Essa média histórica não deve ser recalculada ou substituída pelas notas obtidas

nesta etapa.


Existem duas diferenças fundamentais entre os experimentos.


Primeiro, a avaliação atual utiliza apenas 32 casos críticos. Esse subconjunto foi

deliberadamente construído para concentrar questões com baixa nota histórica,

falha de recuperação ou comportamento considerado informativo para análise de

causa-raiz. Portanto, sua distribuição não representa o conjunto completo das

130 perguntas.


Segundo, o modelo utilizado como Juiz LLM foi substituído e apresentou

severidade significativamente maior sobre as mesmas respostas históricas.


Consequentemente, a média de 1,969 obtida na reavaliação das 32 respostas

históricas não representa uma nova estimativa do desempenho global do

AmazoniaExpert.IA.


Ela representa apenas:


`desempenho das 32 respostas críticas sob o novo avaliador`


e deve ser utilizada como controle metodológico da mudança de juiz.


A média histórica do TCC e as novas avaliações devem, portanto, permanecer separadas. Em particular, as notas atuais dos 32 casos críticos **não substituem, não recalculam e não reduzem retroativamente a média histórica global de 4,14/5**.


### 16.7 Resultados das variantes P0–P4 nos casos críticos


Considerando somente as 160 respostas produzidas no experimento controlado,

foram obtidos os seguintes resultados:


\| Variante | N | Média | Mediana | Desvio padrão |

\|---|---:|---:|---:|---:|

\| P0 | 32 | 2,188 | 2 | 0,896 |

\| P1 | 32 | 2,156 | 2 | 0,884 |

\| P2 | 32 | 2,250 | 2 | 0,984 |

\| P3 | 32 | 2,000 | 2 | 0,622 |

\| P4 | 32 | 2,406 | 2 | 0,979 |


Descritivamente, a ordenação das médias foi:


`P4 > P2 > P0 > P1 > P3`


Entretanto, todas as variantes apresentaram mediana igual a 2.


### 16.8 Distribuição das notas P0–P4


A distribuição completa foi:


\| Variante | Nota 1 | Nota 2 | Nota 3 | Nota 4 | Nota 5 |

\|---|---:|---:|---:|---:|---:|

\| P0 | 5 | 20 | 4 | 2 | 1 |

\| P1 | 5 | 21 | 3 | 2 | 1 |

\| P2 | 5 | 20 | 2 | 4 | 1 |

\| P3 | 5 | 23 | 3 | 1 | 0 |

\| P4 | 4 | 17 | 6 | 4 | 1 |


P4 apresentou a melhor distribuição descritiva dentro do subconjunto crítico,

com menor número de notas 1 e maior presença relativa de notas 3 e 4.


Isso não deve ser interpretado como superioridade global de P4, pois o

experimento de recuperação sobre as 130 questões mostrou que P4 apresentou

a maior degradação global das métricas de retrieval.


Os dois resultados medem fenômenos diferentes:


- o experimento com 130 questões mede desempenho global de recuperação;

- o experimento com 32 questões mede comportamento downstream em um

  subconjunto deliberadamente crítico.


### 16.9 Comparações pareadas em relação a P0


Para cada questão foi calculado:


`DeltaJudge(Pk) = Nota(Pk) - Nota(P0)`


Os resultados foram:


\| Variante | Melhorou | Empatou | Piorou | Delta médio |

\|---|---:|---:|---:|---:|

\| P1 | 0 | 31 | 1 | -0,031 |

\| P2 | 6 | 19 | 7 | +0,063 |

\| P3 | 5 | 18 | 9 | -0,188 |

\| P4 | 10 | 15 | 7 | +0,219 |


P1 mostrou comportamento praticamente idêntico a P0.


Isso é coerente com a análise estrutural anterior: em 31 dos 32 casos P0 e P1

produziram exatamente o mesmo prompt para o gerador e, consequentemente, a

mesma resposta.


A única divergência P1 × P0 ocorreu na Questão 58.


P2 apresentou comportamento misto, com seis melhorias e sete perdas.


P3 apresentou maior número de perdas do que ganhos.


P4 apresentou o maior número de melhorias individuais, com 10 questões

melhorando, sete piorando e 15 permanecendo iguais.


### 16.10 Testes estatísticos das notas downstream


Foi aplicado o teste não paramétrico de Friedman às cinco condições pareadas:


`P0, P1, P2, P3 e P4`


O resultado foi:


`p = 0,303`


Assim, não houve evidência estatística de diferença global entre as cinco

variantes no subconjunto de 32 questões.


Também foram realizados testes pareados de Wilcoxon entre cada variante e P0.


Os valores de p não corrigidos foram aproximadamente:


- P1 × P0: p = 0,317;

- P2 × P0: p = 0,744;

- P3 × P0: p = 0,237;

- P4 × P0: p = 0,224.


Após correção de Holm para as quatro comparações, nenhuma diferença permaneceu

estatisticamente significativa.


Portanto, o maior valor médio observado em P4 deve ser tratado como resultado

descritivo e exploratório, e não como evidência de superioridade estatística.


### 16.11 Presença do capítulo-alvo e qualidade da resposta


As notas do Juiz LLM foram cruzadas com a métrica Hit@5 da recuperação.


Nos 160 registros controlados:


- 115 possuíam o capítulo-alvo no Top-5;

- 45 não possuíam o capítulo-alvo no Top-5.


A média da nota quando o capítulo-alvo estava no Top-5 foi:


`2,209`


A média quando o capítulo-alvo estava ausente foi:


`2,178`


As médias são muito próximas.


Também foi calculada a correlação de Spearman entre o Reciprocal Rank@10 do

capítulo-alvo e a nota do Juiz LLM:


`rho = 0,091`


`p = 0,253`


Não foi identificada associação monotônica estatisticamente significativa entre

a posição do capítulo-alvo e a nota final da resposta neste subconjunto crítico.


Esse resultado não implica que a recuperação seja irrelevante.


Ele indica que a variável binária ou ordinal utilizada para medir a recuperação

do capítulo de origem não é suficiente, isoladamente, para explicar a qualidade

da resposta produzida pelo sistema RAG.


Entre a recuperação e o julgamento final existem outras etapas, incluindo:


- o conteúdo específico dos chunks recuperados;

- a quantidade de informação relevante presente nesses chunks;

- redundância entre os fragmentos;

- posição das evidências no contexto;

- capacidade do ClimateChat de interpretar a informação recuperada;

- conhecimento paramétrico do modelo;

- possíveis erros de síntese ou inferência.


### 16.12 Entrada e saída do capítulo-alvo no Top-5


Foram examinadas as comparações P1–P4 contra P0 em que o status Hit@5 foi

alterado.


Houve cinco situações em que uma transformação fez o capítulo-alvo entrar no

Top-5, embora estivesse ausente em P0.


Nesses cinco casos:


- a nota melhorou em 2;

- permaneceu igual em 2;

- piorou em 1.


Também houve cinco situações em que o capítulo-alvo estava presente em P0 e

deixou o Top-5 após uma transformação.


Nesses casos:


- a nota melhorou em 0;

- permaneceu igual em 2;

- piorou em 3.


Descritivamente, perder o documento-alvo mostrou comportamento mais

consistentemente prejudicial do que a entrada do documento-alvo mostrou

comportamento automaticamente benéfico.


Entretanto, ambos os grupos possuem apenas cinco observações e, portanto,

essa análise deve ser interpretada exclusivamente como evidência exploratória.


### 16.13 Caso 11 — falha temporal persistente


A Questão 11 possui como capítulo-alvo o Chapter 17 e inclui uma restrição

temporal associada à expressão:


`since the 1970s`


Nenhuma variante recuperou o capítulo-alvo dentro do Top-5.


Os contextos foram dominados pelo Chapter 11 em P0, P1, P2 e P3.


P4 alterou substancialmente o resultado e passou a recuperar cinco fragmentos

do Chapter 18, mas também não recuperou o Chapter 17.


As notas foram:


\| Variante | Nota |

\|---|---:|

\| P0 | 1 |

\| P1 | 1 |

\| P2 | 2 |

\| P3 | 2 |

\| P4 | 2 |


O caso demonstra que as transformações linguísticas alteraram parcialmente

a resposta final, mas nenhuma resolveu a falha de recuperação associada à

restrição temporal.


A preservação explícita de termos como `since` durante o pré-processamento não

foi suficiente para garantir que a recuperação densa distinguisse adequadamente

o período solicitado.


### 16.14 Caso 65 — melhora de retrieval sem melhora automática da resposta


A Questão 65 possui como alvo o Cross Chapter 1.


A posição do primeiro documento-alvo foi:


\| Variante | Primeiro rank do alvo |

\|---|---:|

\| P0 | 6 |

\| P1 | 6 |

\| P2 | >10 |

\| P3 | 3 |

\| P4 | 2 |


P3 e P4 transformaram uma falha em Hit@5 em sucesso.


Entretanto, as notas foram:


\| Variante | Nota |

\|---|---:|

\| P0 | 1 |

\| P1 | 1 |

\| P2 | 2 |

\| P3 | 1 |

\| P4 | 2 |


P3 melhorou substancialmente a recuperação, trazendo o Cross Chapter 1 para a

terceira posição, mas a qualidade julgada da resposta permaneceu igual a P0.


A inspeção da resposta mostra que a presença do capítulo correto não foi

suficiente para evitar uma interpretação conceitualmente incorreta pelo gerador.


Esse caso demonstra de forma clara que:


`melhora do retrieval ≠ melhora automática da resposta`


O sistema RAG depende não apenas de fornecer documentos relevantes, mas também

da capacidade do LLM de utilizar corretamente a evidência recuperada.


### 16.15 Caso 83 — aumento da evidência correta e melhora parcial


A Questão 83 possui como alvo o Chapter 27.


A posição do primeiro documento-alvo foi:


\| Variante | Primeiro rank do alvo |

\|---|---:|

\| P0 | 6 |

\| P1 | 6 |

\| P2 | >10 |

\| P3 | 3 |

\| P4 | 2 |


No Top-5:


- P0/P1 continham zero chunks do Chapter 27;

- P2 continha zero;

- P3 continha dois;

- P4 continha quatro.


As notas foram:


\| Variante | Nota |

\|---|---:|

\| P0 | 2 |

\| P1 | 2 |

\| P2 | 2 |

\| P3 | 2 |

\| P4 | 3 |


P3 introduziu o capítulo-alvo no contexto, mas não modificou a nota.


P4, além de colocar o primeiro fragmento correto na segunda posição, forneceu

quatro de cinco chunks provenientes do Chapter 27 e apresentou aumento de nota

de 2 para 3.


Esse caso sugere que não apenas a presença, mas também a quantidade e a

composição da evidência relevante no contexto podem influenciar a geração.


### 16.16 Caso 124 — melhora do retrieval acompanhada de piora da resposta


A Questão 124 possui como alvo o Chapter 15.


A posição do primeiro documento-alvo foi:


\| Variante | Primeiro rank do alvo |

\|---|---:|

\| P0 | >10 |

\| P1 | >10 |

\| P2 | 3 |

\| P3 | >10 |

\| P4 | >10 |


P2 foi a única variante que introduziu o Chapter 15 no Top-5.


Entretanto, as notas foram:


\| Variante | Nota |

\|---|---:|

\| P0 | 3 |

\| P1 | 3 |

\| P2 | 2 |

\| P3 | 2 |

\| P4 | 2 |


Portanto, neste caso, a melhora objetiva do retrieval foi acompanhada por uma

redução da qualidade julgada da resposta.


Esse resultado reforça que Hit@5 mede somente a presença do documento-alvo na

janela de recuperação.


A métrica não garante que:


- o chunk selecionado contenha a evidência necessária;

- essa evidência esteja completa;

- o modelo dê prioridade ao trecho correto;

- o modelo interprete corretamente a informação;

- a síntese final seja aderente ao gabarito.


### 16.17 Interpretação integrada do downstream


Os resultados indicam que os efeitos do pré-processamento sobre a recuperação

não se propagaram de forma linear para a qualidade das respostas.


P1 permaneceu praticamente neutro, tanto na recuperação quanto na geração.


P2 produziu efeitos mistos.


P3 também apresentou comportamento heterogêneo, com ganhos localizados de

retrieval, mas sem vantagem downstream global.


P4 apresentou a maior média de nota e o maior número de melhorias individuais

no subconjunto crítico, embora tenha sido a estratégia com pior desempenho

global de recuperação nas 130 questões.


Essa aparente divergência não constitui contradição.


O conjunto downstream foi deliberadamente selecionado para concentrar casos

problemáticos e não representa a distribuição completa do SPAmazon-QA.


Assim, os resultados de P4 nos 32 casos críticos não anulam a conclusão do

experimento global de recuperação.


A conclusão conjunta é:


`pré-processamento -> retrieval -> contexto -> geração`


constitui uma cadeia de efeitos, mas a relação entre as etapas não é

determinística.


Uma transformação pode melhorar a posição do documento-alvo e ainda assim não

melhorar a resposta.


Da mesma forma, mudanças no contexto podem ocasionalmente beneficiar a geração

mesmo quando as métricas globais de retrieval da transformação são inferiores.


### 16.18 Conclusão da etapa


A avaliação downstream confirma três resultados principais.


Primeiro, a simples aplicação de pré-processamentos linguísticos tradicionais

não produz uma melhora sistemática da qualidade final das respostas RAG.


Segundo, alterações no retrieval podem se propagar para a geração, mas essa

propagação depende do conteúdo efetivamente recuperado e da capacidade do

gerador de utilizar a evidência.


Terceiro, a substituição do Juiz LLM produziu uma mudança sistemática na

severidade das avaliações, razão pela qual as notas atuais não devem ser

comparadas diretamente às notas globais históricas do TCC.


Consequentemente, a análise downstream deve privilegiar comparações internas

entre P0–P4 sob o mesmo juiz atual e deltas pareados dentro de cada pergunta.


As notas históricas do TCC permanecem preservadas como resultados do

experimento original.

### 16.19 Validação computacional final da análise downstream

Após o julgamento das 192 linhas, a análise downstream foi reproduzida
automaticamente pelo script:

`scripts/analyze_downstream_results.py`

O script realiza validações de integridade antes de calcular qualquer resultado.
A execução final confirmou:

- 192 avaliações finais;
- 160 avaliações controladas e 32 históricas;
- 32 avaliações por variante P0–P4;
- 154 entradas únicas para o Juiz LLM;
- notas restritas ao conjunto `{1, 2, 3, 4, 5}`;
- zero justificativas vazias;
- SHA-256 do CSV de avaliações consistente com a auditoria do Juiz;
- 160 linhas de métricas de recuperação para os 32 casos críticos;
- 800 posições correspondentes aos Top-5 congelados usados na geração.

A análise reproduziu os principais resultados downstream:

| Variante | Média | Mediana | DP |
|---|---:|---:|---:|
| P0 | 2,188 | 2 | 0,896 |
| P1 | 2,156 | 2 | 0,884 |
| P2 | 2,250 | 2 | 0,984 |
| P3 | 2,000 | 2 | 0,622 |
| P4 | 2,406 | 2 | 0,979 |

O teste de Friedman entre as cinco condições resultou em:

`χ²_F = 4,8500; p = 0,303038`

Portanto, não foi detectada diferença global estatisticamente significativa
entre P0–P4 nas 32 perguntas críticas.

Nas comparações pareadas Pk × P0, os resultados foram:

| Variante | Melhorou | Igual | Piorou | Δ médio | p bruto | p Holm |
|---|---:|---:|---:|---:|---:|---:|
| P1 | 0 | 31 | 1 | -0,031 | 0,317311 | 0,895243 |
| P2 | 6 | 19 | 7 | +0,062 | 0,743584 | 0,895243 |
| P3 | 5 | 18 | 9 | -0,188 | 0,237175 | 0,895243 |
| P4 | 10 | 15 | 7 | +0,219 | 0,223811 | 0,895243 |

Nenhuma das comparações downstream Pk × P0 permaneceu significativa após
correção de Holm.

A análise também reproduziu a sensibilidade à substituição do Juiz LLM:

- média histórica nas mesmas 32 respostas: 3,125;
- média do juiz atual nas mesmas respostas: 1,969;
- diferença média: -1,156;
- 29 de 32 respostas (90,6%) receberam nota menor;
- Wilcoxon: `p = 6,5989679 × 10⁻⁷`.

Esses valores confirmam que a severidade absoluta do novo avaliador é
substancialmente diferente da observada no TCC. Por esse motivo, os valores
absolutos dos dois juízes não são tratados como intercambiáveis.

A relação retrieval × nota também foi reproduzida:

- capítulo-alvo ausente do Top-5: `n = 45`, média do juiz = 2,178;
- capítulo-alvo presente no Top-5: `n = 115`, média do juiz = 2,209;
- correlação de Spearman entre RR@10 e nota:
  `rho = 0,0908; p = 0,253312`.

Assim, no subconjunto crítico, a posição do capítulo-alvo isoladamente não
explica a qualidade final da resposta.

Quando o capítulo-alvo entrou no Top-5 em relação a P0, houve cinco casos:

- nota melhorou em 2;
- permaneceu igual em 2;
- piorou em 1.

Quando o capítulo-alvo deixou o Top-5, também houve cinco casos:

- nota melhorou em 0;
- permaneceu igual em 2;
- piorou em 3.

Esses resultados permanecem descritivos, pois os grupos possuem apenas cinco
observações cada.


### 16.20 Correlações exploratórias entre mudança de retrieval e mudança de nota

Como análise complementar, foi examinada a associação entre:

`ΔRR@10 = RR@10(Pk) - RR@10(P0)`

e

`ΔJudge = Nota(Pk) - Nota(P0)`.

Ao agrupar as comparações P1–P4 contra P0, obteve-se:

`rho = 0,1762; p = 0,046697`

Esse valor **não é utilizado como evidência inferencial principal**, pois o
agrupamento contém até quatro observações derivadas da mesma pergunta, de modo
que as observações não devem ser tratadas como independentes.

Nas análises separadas por variante:

- P1 × P0: correlação não definida, pois uma das variáveis permaneceu constante;
- P2 × P0: `rho = 0,1826; p = 0,317122`;
- P3 × P0: `rho = -0,0036; p = 0,984477`;
- P4 × P0: `rho = 0,4200; p = 0,016690`.

P4 apresentou, portanto, uma associação positiva moderada descritiva entre
melhora de RR@10 e melhora da nota.

Entretanto, como P2, P3 e P4 constituem três correlações variant-specific
efetivamente calculáveis, foi considerada também uma correção de Holm para
essa família exploratória:

| Variante | p bruto | p ajustado por Holm |
|---|---:|---:|
| P2 | 0,317122 | 0,634244 |
| P3 | 0,984477 | 0,984477 |
| P4 | 0,016690 | 0,050070 |

Assim, a associação observada em P4 fica no limite, mas não permanece
estritamente significativa sob `α = 0,05` após a correção.

Consequentemente, essa correlação é registrada como **tendência exploratória**,
e não como evidência confirmatória de que melhorar RR@10 cause melhora da
resposta final.


### 16.21 Artefatos gerados pela análise final

A execução de `scripts/analyze_downstream_results.py` gerou os seguintes
artefatos principais:

**Métricas e tabelas**

- `results/metrics/downstream_summary.csv`
- `results/metrics/downstream_pairwise_vs_p0.csv`
- `results/metrics/downstream_global_tests.csv`
- `results/metrics/judge_sensitivity_summary.csv`
- `results/metrics/judge_sensitivity_per_question.csv`
- `results/metrics/retrieval_answer_relationship.csv`
- `results/metrics/retrieval_change_answer_change.csv`
- `results/metrics/retrieval_change_answer_change_per_question.csv`
- `results/metrics/retrieval_delta_answer_delta_correlations.csv`
- `results/tables/downstream_score_distribution.csv`
- `results/tables/downstream_key_cases.csv`

**Auditoria**

- `results/runs/downstream_analysis_summary.txt`
- `results/runs/downstream_analysis_run.json`

O arquivo `downstream_analysis_run.json` registra as versões das bibliotecas,
os hashes dos arquivos de entrada e saída e os principais resultados calculados.


### 16.22 Geração e padronização das figuras finais

Após o fechamento das análises quantitativas, as figuras destinadas ao
repositório, ao artigo e à apresentação foram regeneradas por meio do script:

`scripts/generate_final_figures.py`

Foi adotada uma identidade visual única, baseada exclusivamente em tons de
azul e cinza, com:

- fundo branco;
- tipografia consistente;
- grades discretas;
- títulos e eixos padronizados;
- arquivos PNG em alta resolução;
- arquivos PDF vetoriais.

Para evitar conflitos de escrita observados durante o salvamento direto em
arquivos sincronizados pelo OneDrive, o script final salva cada figura
primeiro em arquivo temporário local e posteriormente copia o artefato pronto
para o diretório final.

Os artefatos visuais oficiais encontram-se em:

`results/figures_final/`

e são:

- `fig01_downstream_likert.png`
- `fig01_downstream_likert.pdf`
- `fig02_downstream_delta.png`
- `fig02_downstream_delta.pdf`
- `fig03_judge_sensitivity.png`
- `fig03_judge_sensitivity.pdf`
- `fig04_hit5_vs_score.png`
- `fig04_hit5_vs_score.pdf`
- `fig05_retrieval_global.png`
- `fig05_retrieval_global.pdf`

O conteúdo das figuras é:

1. `fig01_downstream_likert` — distribuição percentual das notas 1–5 em P0–P4;
2. `fig02_downstream_delta` — número de casos que melhoraram, permaneceram iguais ou pioraram em relação a P0;
3. `fig03_judge_sensitivity` — matriz de sensibilidade entre a nota histórica do TCC e a nota do juiz atual;
4. `fig04_hit5_vs_score` — nota média downstream quando o capítulo-alvo está ausente ou presente no Top-5;
5. `fig05_retrieval_global` — Hit@1, Hit@3, Hit@5 e Hit@10 nas cinco variantes.

Para o artigo científico final, foram selecionadas como figuras principais:

- `fig05_retrieval_global`;
- `fig02_downstream_delta`;
- `fig04_hit5_vs_score`.

As figuras `fig01_downstream_likert` e `fig03_judge_sensitivity` permanecem
disponíveis como material complementar e para possível uso na apresentação.


---

# 17. Encerramento da etapa experimental

Com a conclusão da análise reproduzível downstream, a etapa experimental
principal deste trabalho é considerada concluída.

O desenho experimental final contém três níveis complementares de evidência:

1. **Recuperação global nas 130 perguntas**
   - 650 consultas P0–P4;
   - 6.500 posições de ranking;
   - Hit@1, Hit@3, Hit@5, Hit@10 e MRR@10;
   - testes pareados com correção de Holm.

2. **Análise de 32 casos críticos pré-selecionados**
   - subconjunto congelado antes da inspeção dos resultados P1–P4;
   - análise de alterações no ranking e no contexto Top-5;
   - casos sentinela e análise de causa-raiz.

3. **Avaliação downstream**
   - 160 respostas RAG controladas;
   - 32 respostas históricas reavaliadas;
   - 192 registros finais de julgamento;
   - comparações pareadas P0–P4 sob o mesmo juiz atual;
   - análise retrieval → contexto → geração → nota.

A conclusão experimental principal é que, neste corpus, com
`sentence-transformers/all-mpnet-base-v2` e sob o protocolo adotado, as
transformações linguísticas tradicionais avaliadas não produziram melhora
global da recuperação em relação ao texto original.

Lowercase isolado foi neutro. A remoção de stopwords apresentou degradação
estatisticamente detectável em parte das métricas. A lematização foi a
transformação adicional de menor impacto global e apresentou ganhos
localizados. O Porter stemming apresentou a degradação global mais forte e
consistente.

Na etapa downstream, as mudanças na recuperação não se propagaram de forma
determinística para a qualidade das respostas. A presença ou melhor posição do
capítulo-alvo pode beneficiar determinados casos, mas não garante que o modelo
gerador selecione, interprete ou sintetize corretamente a evidência.

A avaliação atual também demonstrou que a substituição do Juiz LLM altera
substancialmente a severidade das notas. Por isso:

- a média histórica global de **4,14/5** do AmazoniaExpert.IA no TCC permanece
  preservada como resultado do experimento original;
- as novas notas dos 32 casos críticos não substituem nem recalculam essa média;
- não será aplicada correção aditiva ou recalibração artificial das notas atuais;
- as comparações downstream principais são internas entre P0–P4 sob o mesmo
  GPT-OSS-120B;
- a diferença entre o juiz histórico e o atual é reportada explicitamente como
  limitação e análise de sensibilidade.

Não estão planejadas novas variantes de pré-processamento nem novas avaliações
com outro Juiz LLM apenas para modificar as médias observadas. Qualquer análise
adicional deverá ser claramente identificada como estudo de robustez separado,
sem substituir os resultados já congelados.

A partir deste ponto, os resultados principais permaneceram congelados. A extensão mecanística exploratória pós-resultados, descrita na Seção 18, foi posteriormente executada sem modificar variantes, índices, rankings, respostas RAG ou resultados principais. Com sua conclusão, a etapa experimental completa do trabalho é considerada encerrada.

---

# 18. Extensão mecanística exploratória pós-resultados

## 18.1 Motivação e natureza da extensão

Após o encerramento do experimento principal P0–P4 e da análise downstream,
foi definida uma extensão adicional com finalidade **mecanística e exploratória**.

Essa análise foi motivada pelos resultados já observados no experimento principal,
em especial pelo contraste entre:

- neutralidade de P1;
- degradação de P2;
- impacto relativamente pequeno de P3;
- degradação mais intensa de P4.

Por ter sido planejada **após a observação dos resultados principais**, esta frente
não será apresentada como hipótese pré-registrada nem como confirmação causal
das explicações levantadas anteriormente.

Seu objetivo é investigar uma etapa intermediária ainda não observada diretamente:

`pré-processamento -> tokenização -> embedding -> ranking`

A extensão não altera:

- as variantes P0–P4;
- os corpora já congelados;
- as 130 perguntas;
- o encoder;
- os índices vetoriais;
- os rankings já produzidos;
- as respostas RAG;
- o Juiz LLM;
- os resultados estatísticos principais.

Nenhuma nova resposta será gerada e nenhum índice será reconstruído.


## 18.2 Nova questão de pesquisa exploratória

Foi definida a seguinte questão complementar:

> **RQ3 — Em que medida as estratégias de pré-processamento alteram a tokenização
> e a representação vetorial produzida pelo `all-mpnet-base-v2`, e essas alterações
> estão associadas à estabilidade do ranking e ao desempenho de recuperação?**

A RQ3 será operacionalizada em três frentes:

- **RQ3a:** quanto P1–P4 alteram a tokenização em relação a P0?
- **RQ3b:** quanto P1–P4 deslocam as representações vetoriais em relação a P0?
- **RQ3c:** maior alteração da representação está associada a maior alteração do ranking?


## 18.3 Artefatos de entrada congelados

A extensão utilizará exclusivamente artefatos já produzidos no experimento:

- corpus P0 com 6.900 chunks;
- corpora P1–P4 com os mesmos 6.900 IDs;
- 130 perguntas do SPAmazon-QA;
- consultas P0–P4 já transformadas pelo código congelado de pré-processamento;
- rankings controlados P0–P4 já produzidos;
- métricas por questão já calculadas.

O modelo de representação permanecerá:

`sentence-transformers/all-mpnet-base-v2`

Não será utilizado outro encoder nesta extensão.


## 18.4 Unidade de análise

Serão analisados dois níveis.

### Consultas

Para as 130 perguntas serão calculadas quatro comparações contra P0:

`P0 x P1`
`P0 x P2`
`P0 x P3`
`P0 x P4`

Total:

`130 perguntas x 4 comparações = 520 observações`

As consultas constituirão a unidade principal para relacionar alteração da
representação e alteração do retrieval.

### Corpus

Para os 6.900 chunks serão calculadas as mesmas quatro comparações:

`6.900 chunks x 4 comparações = 27.600 observações`

A análise do corpus terá caráter predominantemente descritivo e será utilizada
para caracterizar o efeito das transformações sobre a representação documental.

As 27.600 observações de chunks não serão tratadas como experimentos
independentes para produzir inferências artificiais baseadas apenas no grande N.


## 18.5 Análise de tokenização

A tokenização será executada com o **tokenizer real associado ao
`all-mpnet-base-v2`**, e não com divisão simples por espaços.

Para cada texto serão registrados, quando tecnicamente disponíveis:

- número de caracteres;
- número de palavras para descrição textual;
- número de tokens/subwords antes do truncamento;
- número de tokens efetivamente fornecidos ao encoder;
- diferença de tokens em relação a P0;
- razão entre número de subwords e número de palavras;
- igualdade exata ou não da sequência tokenizada entre P0 e Pk;
- ocorrência de truncamento.

Também serão registrados no arquivo de auditoria:

- classe do tokenizer;
- `model.max_seq_length`;
- versão de `sentence-transformers`;
- versão de `transformers`;
- versão de Python.


## 18.6 Análise de deriva dos embeddings

Os textos P0–P4 serão codificados novamente exclusivamente para fins de análise,
usando o mesmo encoder do experimento principal.

Nenhuma normalização adicional será introduzida além do comportamento já
adotado no pipeline do encoder.

Para cada comparação P0 x Pk serão calculadas:

- similaridade cosseno;
- distância cosseno `1 - cosine_similarity`;
- distância Euclidiana/L2 como medida complementar.

A medida principal de deriva será:

`embedding_drift = 1 - cosine(P0, Pk)`

Os vetores completos de 768 dimensões não precisam ser persistidos em disco.
Serão salvas apenas as métricas derivadas necessárias à análise e à auditoria.


## 18.7 Estabilidade do ranking

A estabilidade será calculada utilizando os rankings Top-10 já congelados.

Para cada pergunta e variante Pk serão comparados os conjuntos Top-10 de P0 e Pk.

Serão calculadas:

- quantidade de `chunk_id` compartilhados no Top-10;
- proporção de overlap Top-10;
- índice de Jaccard entre os dois conjuntos Top-10.

Definições:

`overlap_top10 = |Top10(P0) inter Top10(Pk)| / 10`

`jaccard_top10 = |intersecao| / |uniao|`

Essa análise mede mudanças no ranking completo e complementa as métricas já
existentes baseadas exclusivamente na posição do capítulo-alvo.


## 18.8 Integração representação x retrieval

Para cada uma das 520 combinações pergunta-variante será criada uma linha
integrada contendo, no mínimo:

- `id_questao`;
- variante P1–P4;
- métricas de alteração da tokenização;
- `cosine_similarity_p0`;
- `embedding_drift`;
- distância L2;
- `top10_overlap`;
- `top10_jaccard`;
- primeiro rank relevante em P0;
- primeiro rank relevante em Pk;
- `delta_rr_10`;
- mudança de Hit@5;
- status de entrada/saída/permanência no Top-5.

O objetivo é investigar associações entre:

`alteracao da tokenizacao -> deriva do embedding`

`deriva do embedding -> estabilidade do Top-10`

`deriva do embedding -> |delta RR@10|`

`deriva do embedding -> transicao de Hit@5`


## 18.9 Plano estatístico congelado antes da execução

A inferência estatística será concentrada nas 130 consultas pareadas.

### Comparação da deriva entre P1–P4

Será aplicado teste de Friedman às quatro condições de deriva de embedding:

`P1, P2, P3 e P4`

Se houver diferença global, serão realizadas comparações pareadas de Wilcoxon
entre variantes, com correção de Holm para múltiplas comparações.

### Associação entre deriva e estabilidade do ranking

Para cada variante P1–P4 será calculada correlação de Spearman entre:

- `embedding_drift` e `top10_jaccard`;
- `embedding_drift` e `abs(delta_rr_10)`.

Cada família de quatro correlações receberá correção de Holm.

Se uma das variáveis apresentar variância zero para determinada variante, a
correlação será registrada como não definida.

### Hit@5

As transições de Hit@5 serão analisadas de forma descritiva em função da deriva
de embedding, evitando inferência excessiva em grupos com poucas observações.


## 18.10 Casos qualitativos previamente definidos

A inspeção qualitativa utilizará prioritariamente casos já relevantes nas análises
anteriores, evitando selecionar exemplos apenas depois de observar os novos
resultados.

Serão acompanhados:

- Q11 — falha temporal persistente;
- Q58 — P0/P1 com mesmo primeiro rank, mas composição Top-5 diferente;
- Q65 — entrada do documento-alvo em P3/P4;
- Q83 — aumento progressivo da presença do capítulo-alvo;
- Q124 — ganho específico de retrieval produzido por P2.

Esses casos terão função ilustrativa e não substituirão a análise quantitativa global.


## 18.11 Artefatos planejados

A implementação será concentrada em:

`scripts/analyze_representation_shift.py`

Arquivos planejados:

**Dados derivados**

- `results/raw/representation_shift_queries.csv`
- `results/raw/representation_shift_chunks.csv`

**Métricas**

- `results/metrics/representation_shift_summary.csv`
- `results/metrics/representation_tokenization_summary.csv`
- `results/metrics/representation_ranking_stability.csv`
- `results/metrics/representation_retrieval_correlations.csv`
- `results/metrics/representation_statistical_tests.csv`

**Casos**

- `results/tables/representation_key_cases.csv`

**Auditoria**

- `results/runs/representation_shift_run.json`
- `results/runs/representation_shift_summary.txt`

**Figuras candidatas**

- `results/figures_final/fig06_query_embedding_drift.png`
- `results/figures_final/fig06_query_embedding_drift.pdf`
- `results/figures_final/fig07_ranking_stability.png`
- `results/figures_final/fig07_ranking_stability.pdf`

Uma terceira figura só será produzida se acrescentar informação não redundante.


## 18.12 Critérios de interpretação

A extensão é exploratória.

Mesmo que sejam observadas associações entre deriva de embedding e mudança de
ranking, elas não serão descritas automaticamente como relações causais.

Formulações aceitáveis incluem:

- "maior deriva esteve associada a menor estabilidade do ranking";
- "o resultado é consistente com a hipótese de que a transformação da
  representação contribua para a alteração do retrieval";
- "a associação observada ajuda a explicar o padrão experimental".

Formulações a evitar incluem:

- "a deriva causou a queda";
- "stemming sempre destrói embeddings";
- "stopwords são necessárias em todos os encoders densos".

As conclusões permanecerão restritas ao corpus, encoder, idioma dos documentos
e protocolo adotados neste estudo.


## 18.13 Preflight computacional

Antes do cálculo das novas métricas foi executado o preflight definido no
protocolo.

A validação confirmou:

- 6.900 chunks em P0–P4;
- hashes SHA-256 esperados para os cinco corpora;
- igualdade dos IDs entre os cinco corpora;
- 130 perguntas em cada variante;
- P0 idêntica às perguntas originais do SPAmazon-QA;
- 650 combinações questão-variante;
- 6.500 posições Top-10;
- IDs consistentes entre perguntas, rankings e métricas;
- encoder `sentence-transformers/all-mpnet-base-v2`;
- dimensionalidade igual a 768;
- tokenizer `MPNetTokenizer`;
- `model.max_seq_length = 384`.

Ambiente da execução:

- Python 3.13.3;
- sentence-transformers 5.3.0;
- transformers 5.4.0;
- torch 2.11.0;
- numpy 2.4.4;
- pandas 3.0.2;
- scipy 1.17.1.

O preflight foi aprovado integralmente antes do início do cálculo dos embeddings.

## 18.14 Execução da extensão mecanística

Após a aprovação do preflight, foi executado:

`scripts/analyze_representation_shift.py`

O protocolo foi registrado como:

`representation-shift-exploratory-v1`

Foram analisadas:

- 130 consultas em P0–P4;
- 520 comparações P0 × P1–P4 no nível das consultas;
- 6.900 chunks em P0–P4;
- 27.600 comparações P0 × P1–P4 no nível do corpus.

A execução completa levou aproximadamente 180,8 minutos em CPU.

Não foi realizada nova recuperação vetorial. Os rankings Top-10 utilizados na
análise de estabilidade foram os mesmos já congelados no experimento principal.


## 18.15 Resultados de tokenização

A tokenização foi obtida diretamente com o `MPNetTokenizer` associado ao
`all-mpnet-base-v2`.

### 18.15.1 Consultas

| Variante | Subwords P0 | Subwords Pk | Δ médio | Mudança relativa média | Sequência alterada |
|---|---:|---:|---:|---:|---:|
| P1 | 21,469 | 21,469 | 0,000 | 0,00% | 0,0% |
| P2 | 21,469 | 15,238 | -6,231 | 29,24% | 100,0% |
| P3 | 21,469 | 21,500 | +0,031 | 0,75% | 99,2% |
| P4 | 21,469 | 25,915 | +4,446 | 21,61% | 100,0% |

P1 produziu exatamente a mesma sequência tokenizada de P0 nas 130 perguntas.

P2 removeu, em média, 6,23 subwords por consulta.

P3 alterou a sequência de tokens em 129 das 130 perguntas, mas o número médio
de subwords permaneceu praticamente inalterado.

P4 aumentou o comprimento tokenizado em aproximadamente 4,45 subwords por
consulta.

### 18.15.2 Chunks

| Variante | Subwords P0 | Subwords Pk | Δ médio | Mudança relativa média | Sequência alterada |
|---|---:|---:|---:|---:|---:|
| P1 | 177,581 | 177,581 | 0,000 | 0,00% | 0,0% |
| P2 | 177,581 | 152,824 | -24,756 | 14,36% | 99,29% |
| P3 | 177,581 | 177,105 | -0,476 | 0,76% | 99,81% |
| P4 | 177,581 | 204,007 | +26,427 | 16,03% | 100,0% |

A razão média entre subwords e palavras nos chunks foi:

- P0/P1: 1,554;
- P2: 1,673;
- P3: 1,549;
- P4: 1,786.

P4 apresentou a maior fragmentação subword.

O número de chunks que ultrapassou o limite efetivo de sequência foi:

- P0/P1: 21;
- P2: 14;
- P3: 21;
- P4: 31.

Assim, a remoção de stopwords em P2 reduziu ocorrências de truncamento, enquanto
o stemming em P4 aumentou o número de textos truncados.


## 18.16 Resultados de deriva dos embeddings

A medida principal foi:

`embedding_drift = 1 - cosine(P0, Pk)`

### 18.16.1 Consultas

| Variante | Cosseno médio | Drift médio | Drift mediano |
|---|---:|---:|---:|
| P1 | 1,000000 | ≈ 0,000000 | 0,000000 |
| P2 | 0,930832 | 0,069168 | 0,064964 |
| P3 | 0,960339 | 0,039661 | 0,030069 |
| P4 | 0,812659 | 0,187341 | 0,160366 |

### 18.16.2 Chunks

| Variante | Cosseno médio | Drift médio | Drift mediano |
|---|---:|---:|---:|
| P1 | 1,000000 | ≈ 0,000000 | 0,000000 |
| P2 | 0,976116 | 0,023884 | 0,017332 |
| P3 | 0,984132 | 0,015868 | 0,011972 |
| P4 | 0,878721 | 0,121279 | 0,108292 |

A ordenação descritiva da perturbação foi a mesma para consultas e chunks:

`P1 < P3 < P2 < P4`

Os resíduos numéricos de drift observados em P1 são da ordem de precisão de
ponto flutuante e não representam uma mudança substantiva da representação.

O resultado de P1 é particularmente informativo: o lowercase externo não alterou
a sequência produzida pelo tokenizer e, consequentemente, produziu embeddings
numericamente equivalentes a P0.

P3 alterou quase todas as sequências tokenizadas, mas manteve baixa deriva vetorial.
Isso demonstra que alterar tokens não implica necessariamente grande deslocamento
na representação semântica.

P4 apresentou simultaneamente:

- maior fragmentação subword;
- maior número médio de subwords;
- maior número de chunks truncados;
- maior deriva dos embeddings.

Esses resultados fornecem uma explicação mecanística plausível para a forte
degradação de retrieval observada em P4, sem estabelecer causalidade.


## 18.17 Testes estatísticos da deriva das consultas

A comparação global entre P1–P4 foi realizada com Friedman:

`χ² = 344,196305; p = 2,693528 × 10⁻74`

A diferença global foi estatisticamente significativa.

Conforme o plano congelado, foram realizados testes pareados de Wilcoxon entre
as quatro variantes com correção de Holm:

| Comparação | p bruto | p Holm |
|---|---:|---:|
| P1 × P2 | 4,460 × 10⁻23 | 2,676 × 10⁻22 |
| P1 × P3 | 6,513 × 10⁻23 | 2,676 × 10⁻22 |
| P1 × P4 | 4,460 × 10⁻23 | 2,676 × 10⁻22 |
| P2 × P3 | 6,448 × 10⁻13 | 6,448 × 10⁻13 |
| P2 × P4 | 4,139 × 10⁻20 | 8,278 × 10⁻20 |
| P3 × P4 | 7,956 × 10⁻23 | 2,676 × 10⁻22 |

Todas as seis comparações permaneceram significativas sob `α = 0,05`.

Esses testes indicam que as quatro condições produziram níveis estatisticamente
distinguíveis de perturbação da representação das consultas.


## 18.18 Deriva vetorial e estabilidade do ranking

A estabilidade do Top-10 foi analisada por overlap e índice de Jaccard entre os
conjuntos recuperados em P0 e Pk.

A associação principal definida no protocolo foi:

`embedding_drift × top10_jaccard`

Resultados:

- P1: `rho = 0,0527; p = 0,551557; p_Holm = 0,757760`;
- P2: `rho = -0,0778; p = 0,378880; p_Holm = 0,757760`;
- P3: `rho = -0,1970; p = 0,024691; p_Holm = 0,074074`;
- P4: `rho = -0,3375; p = 0,0000859; p_Holm = 0,000344`.

Somente P4 permaneceu estatisticamente significativa após correção.

Assim, dentro de P4, maior afastamento da representação em relação a P0 esteve
associado à menor estabilidade do conjunto Top-10.

A segunda família examinou:

`embedding_drift × |ΔRR@10|`

Resultados:

- P1: correlação não definida devido à ausência de variação relevante;
- P2: `rho = 0,0415; p = 0,638854; p_Holm = 1,000000`;
- P3: `rho = 0,1228; p = 0,164062; p_Holm = 0,492187`;
- P4: `rho = 0,2075; p = 0,017844; p_Holm = 0,071377`.

Nenhuma variante permaneceu significativa nessa segunda família após correção
de Holm.

Portanto, a associação mais robusta observada na extensão é entre a deriva de P4
e a estabilidade do ranking completo, e não entre deriva e mudança do
Reciprocal Rank do capítulo-alvo isolado.


## 18.19 Transições de Hit@5

As transições de Hit@5 foram mantidas como análise descritiva.

Em P4:

- casos que permaneceram Hit@5: `n = 103`, drift médio = 0,179678;
- casos que deixaram o Top-5: `n = 18`, drift médio = 0,224391;
- casos que entraram no Top-5: `n = 2`, drift médio = 0,131028;
- casos que permaneceram fora: `n = 7`, drift médio = 0,220907.

Descritivamente, os casos em que o documento-alvo deixou o Top-5 apresentaram
maior deriva média que os casos que permaneceram com sucesso.

Nenhum teste inferencial adicional foi introduzido para esses pequenos grupos.


## 18.20 Figuras da extensão

A execução produziu:

- `results/figures_final/fig06_query_embedding_drift.png`
- `results/figures_final/fig06_query_embedding_drift.pdf`
- `results/figures_final/fig07_ranking_stability.png`
- `results/figures_final/fig07_ranking_stability.pdf`

Após inspeção visual, foi produzida também uma figura combinada pelo script:

`scripts/generate_mechanistic_combined_figure.py`

Arquivos:

- `results/figures_final/fig08_representation_mechanism_combined.png`
- `results/figures_final/fig08_representation_mechanism_combined.pdf`

A figura combinada apresenta:

1. painel (a): distribuição da deriva dos embeddings das consultas em P1–P4;
2. painel (b): relação entre `embedding_drift` e Jaccard do Top-10, com destaque
   para a associação significativa observada em P4.

Para o artigo científico final, a seleção principal de figuras passa a ser:

- `fig05_retrieval_global`;
- `fig08_representation_mechanism_combined`;
- `fig02_downstream_delta`.

`fig04_hit5_vs_score`, `fig06_query_embedding_drift` e
`fig07_ranking_stability` permanecem como resultados complementares.


## 18.21 Artefatos produzidos

**Dados derivados**

- `results/raw/representation_shift_queries.csv`
- `results/raw/representation_shift_chunks.csv`

**Métricas**

- `results/metrics/representation_shift_summary.csv`
- `results/metrics/representation_tokenization_summary.csv`
- `results/metrics/representation_ranking_stability.csv`
- `results/metrics/representation_retrieval_correlations.csv`
- `results/metrics/representation_statistical_tests.csv`

**Casos**

- `results/tables/representation_key_cases.csv`

**Auditoria**

- `results/runs/representation_shift_run.json`
- `results/runs/representation_shift_summary.txt`

A execução principal foi realizada por:

`scripts/analyze_representation_shift.py`


## 18.22 Interpretação integrada da RQ3

A extensão mecanística mostrou que o efeito das transformações não pode ser
descrito apenas pela quantidade de caracteres ou tokens removidos.

P1 foi representacionalmente neutro: as sequências tokenizadas permaneceram
idênticas a P0 e os embeddings foram numericamente equivalentes.

P3 modificou quase todas as sequências tokenizadas, porém preservou melhor a
geometria semântica do encoder, apresentando a menor deriva entre as variantes
que realmente alteraram a entrada do MPNet.

P2 removeu uma parcela substancial dos subwords e apresentou deriva intermediária.
A redução de truncamento observada em P2 não impediu a degradação do retrieval,
indicando que o comprimento do texto, isoladamente, não explica o resultado.

P4 produziu o padrão mais disruptivo: aumentou a fragmentação subword, o número
de tokens e os truncamentos, além de gerar a maior deriva vetorial. Dentro de P4,
maior deriva também esteve significativamente associada à menor estabilidade do
Top-10 após correção de Holm.

Esses resultados são consistentes com a hipótese de que transformações lexicais
mais agressivas podem perturbar a representação esperada por um encoder
contextual pré-treinado sobre linguagem natural.

A evidência é mecanisticamente informativa, mas continua observacional dentro
do experimento. Não se afirma que a deriva seja, por si só, a causa exclusiva da
degradação do retrieval.


## 18.23 Encerramento definitivo da etapa experimental

Com a conclusão da RQ3, o trabalho passa a conter quatro camadas complementares
de evidência:

1. transformação linguística e tokenização;
2. alteração da representação vetorial;
3. recuperação e estabilidade do ranking;
4. propagação downstream para contexto RAG e resposta.

A cadeia experimental consolidada é:

`pré-processamento -> tokenização -> embedding -> ranking -> contexto RAG -> resposta`

A etapa experimental está encerrada.

Não estão previstas novas variantes, novos encoders, novas respostas RAG ou novas
avaliações com outro Juiz LLM apenas para alterar os resultados observados.

A próxima fase do projeto é a redação do artigo científico final no Overleaf e,
posteriormente, a preparação da apresentação.
