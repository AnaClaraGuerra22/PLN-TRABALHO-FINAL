# Impacto do Pré-processamento Linguístico na Recuperação Semântica de Documentos Científicos

Trabalho Final da disciplina **INF 791 - Processamento de Linguagem Natural**, desenvolvido a partir do corpus e do benchmark construídos no projeto **AmazoniaExpert.IA**.

## 1. Visão geral

Este projeto investiga como diferentes estratégias clássicas de pré-processamento linguístico afetam a recuperação semântica de documentos científicos sobre a Amazônia.

Pergunta principal:

> **Como diferentes estratégias de pré-processamento linguístico afetam a recuperação semântica de capítulos de origem de perguntas científicas sobre a Amazônia?**

O experimento principal isola a etapa de retrieval. Corpus, chunks, IDs, metadados, encoder, banco vetorial, parâmetros de busca e conjunto de perguntas permanecem controlados; a variável experimental é a preparação linguística aplicada ao texto.

Além da análise principal de recuperação, o projeto inclui uma **análise secundária downstream em casos críticos**, para verificar se mudanças no contexto recuperado também se traduzem em melhora ou piora da resposta final do RAG.

---

## 2. Corpus

O corpus foi exportado da base vetorial utilizada no AmazoniaExpert.IA e auditado antes dos novos experimentos.

| Característica | Valor |
|---|---:|
| Documentos científicos | 38 |
| Chunks | 6.900 |
| IDs únicos de chunks | 6.900 |
| Capítulos regulares | 34 |
| Cross Chapters | 2 |
| Anexos | 2 |
| Dimensionalidade dos embeddings | 768 |

O texto armazenado na baseline preserva a estrutura utilizada na vetorização original:

```text
Chapter + Section + Content
```

---

## 3. Benchmark SPAmazon-QA

A avaliação utiliza o **SPAmazon-QA**, conjunto curado de perguntas e respostas científicas sobre a Amazônia.

| Característica | Valor |
|---|---:|
| Perguntas | 130 |
| IDs únicos | 130 |
| Documentos-alvo canônicos | 38 |
| Direct | 53 |
| Indirect | 77 |

### Distribuição por dificuldade

| Dificuldade | Perguntas |
|---|---:|
| Easy | 7 |
| Medium-Low | 28 |
| Medium-High | 16 |
| Hard | 79 |

O arquivo original `SPAmazon-QA.json` não é sobrescrito. Rankings, métricas e novos resultados são salvos separadamente.

---

## 4. Canonicalização dos documentos

O campo `capitulo_alvo` possui 39 grafias distintas, normalizadas para 38 origens canônicas.

Exemplo:

```text
Capítulo CC2
Capítulo Cross Chapter 2
cc2
cross_chapter_2
```

são tratados como:

```text
cross_chapter_2
```

Durante a auditoria também foi identificada uma ambiguidade herdada dos metadados históricos:

```text
Chapter 1       -> chapter_number = 1
Cross Chapter 1 -> chapter_number = 1

Chapter 2       -> chapter_number = 2
Cross Chapter 2 -> chapter_number = 2
```

Como o campo `source` distingue corretamente esses documentos, o identificador canônico atual é derivado prioritariamente de `source`, preservando os metadados originais para auditoria.

| Documento | Chunks |
|---|---:|
| Chapter 1 | 243 |
| Cross Chapter 1 | 61 |
| Chapter 2 | 229 |
| Cross Chapter 2 | 18 |

A distribuição completa está em:

```text
results/tables/chunks_por_documento.csv
```

---

## 5. Variantes de pré-processamento

| Variante | Transformação |
|---|---|
| **P0** | Texto original, sem novo pré-processamento |
| **P1** | Lowercase |
| **P2** | Lowercase + remoção controlada de stopwords |
| **P3** | Lowercase + lematização |
| **P4** | Lowercase + Porter stemming |

A mesma variante é aplicada aos chunks e às consultas.

### Termos semanticamente protegidos

Para evitar a remoção ou deformação deliberada de operadores críticos, foi congelada antes dos resultados uma lista de termos protegidos, incluindo palavras relacionadas a:

- temporalidade;
- negação;
- lógica;
- quantificação;
- comparação e direção.

Exemplos:

```text
since, before, after, between, from, to
not, no, without
and, or, but
all, same, every
more, less, greater, higher, lower, than
```

Essa política não será alterada depois da observação dos rankings P0-P4.

---

## 6. Validação do pré-processamento

As transformações foram inspecionadas manualmente com exemplos de:

- temporalidade;
- temporalidade oposta;
- negação;
- comparação;
- quantidades, siglas e intervalos numéricos.

A inspeção completa está em:

```text
results/runs/preprocessing_validation_final.txt
```

Também foi criada uma suíte automatizada de testes:

```text
10 passed
```

Arquivo:

```text
tests/test_preprocessing.py
```

Hash SHA-256 da implementação congelada em `src/preprocess.py`:

```text
050AEC627D8DA62FAC2F0B8E364FDC9D3102368F1464B17240187E964ACA6610
```

---

## 7. Corpora derivados

P1-P4 foram construídos a partir exatamente dos mesmos 6.900 registros de P0.

Todas as variantes preservaram:

```text
6.900 chunks
6.900 IDs únicos
38 documentos
0 textos vazios
0 alterações nos metadados
```

| Variante | Redução de caracteres | SHA-256 |
|---|---:|---|
| P0 | - | `1fce41571ca46ccca48c9aaf2fc07013aa7fe6bd215305350365eb451a73fae8` |
| P1 | 0,00% | `0e1efcd0f921f08956529d89eb0ff267d221fbf494458c655e5e7e6eff1c3c6a` |
| P2 | 11,28% | `48dc79cf004d56c5f25905532564fc8a0f4018f6c15fdbe241c2e6b2f8103447` |
| P3 | 2,98% | `ae8b5ad596327372a3b5b6cf8e92a422db99ac45daae7e8f288e86e325302e99` |
| P4 | 11,06% | `70fd5435015ba57aea468b8148190c1cc619e69796b8b33c6871cbb55ca62ded` |

---

## 8. Indexação vetorial controlada

Modelo fixo:

```text
sentence-transformers/all-mpnet-base-v2
```

Configuração:

```text
Dimensionalidade: 768
Banco vetorial: ChromaDB
Índice aproximado: HNSW
Coleção: langchain
```

Para reduzir diferenças causadas pela construção histórica do HNSW, o experimento principal reconstrói cinco índices sob as mesmas condições:

```text
P0_CONTROLLED
P1
P2
P3
P4
```

Todos utilizam os mesmos IDs, a mesma ordem de inserção, os mesmos metadados, o mesmo encoder e o mesmo batch size.

Os bancos experimentais são mantidos fora do OneDrive e não são versionados no Git por serem artefatos binários reconstruíveis.

---

## 9. Protocolo principal de recuperação

Cada uma das 130 perguntas é submetida às cinco condições:

```text
130 perguntas x 5 variantes = 650 consultas
```

Para cada consulta são armazenados os 10 chunks mais próximos:

```text
130 perguntas x 5 variantes x Top-10
= 6.500 posições de ranking
```

Fluxo:

```text
query original
    |
    v
preprocessamento Pk
    |
    v
embedding all-mpnet-base-v2
    |
    v
índice Pk
    |
    v
Top-10
    |
    v
canonicalização do documento
    |
    v
métricas
```

---

## 10. Métricas

Métricas principais:

- **Chapter Hit@1**
- **Chapter Hit@3**
- **Chapter Hit@5**
- **Chapter Hit@10**
- **First Relevant Rank**
- **MRR@10**
- **Delta vs P0_CONTROLLED**

O capítulo de origem funciona como uma **proxy operacional de relocalização da fonte**. Um chunk de outro capítulo pode conter evidência cientificamente válida; portanto, Chapter Hit@k não deve ser interpretado como julgamento absoluto de relevância por chunk.

---

## 11. Reprodução da baseline histórica

A reprodução do banco P0 preservado produziu:

| Métrica | Resultado |
|---|---:|
| Hit@1 | 103/130 - 79,23% |
| Hit@3 | 117/130 - 90,00% |
| Hit@5 | 121/130 - 93,08% |
| Hit@10 | 124/130 - 95,38% |
| MRR@10 | 0,8507 |

No TCC histórico, o indicador operacional equivalente ao Hit@5 havia registrado 118/130, ou 90,8%.

A reprodução atual concordou com o histórico em:

```text
127/130 consultas
97,69%
```

As três divergências foram os IDs 96, 97 e 98, todos do Annex II. A diferença foi registrada como divergência de reprodução, sem atribuição causal não comprovada.

---

## 12. Caso sentinela - relações temporais

A Questão 11 é acompanhada como caso sentinela para temporalidade.

A pergunta exige atividades que se expandiram:

```text
since the 1970s
```

A baseline P0 recuperou predominantemente:

```text
Chapter 11
Economic Drivers in the Amazon from the 19th Century to the 1970s
```

O Chapter 17, documento-alvo, não apareceu no Top-10.

O caso evidencia que alta proximidade temática não garante preservação da relação temporal:

```text
since the 1970s != to the 1970s
```

---

# 13. Análise secundária downstream dos casos críticos

Além do experimento principal de retrieval, será executada uma análise de causa-raiz em um subconjunto fixado **antes de observar os resultados P1-P4**.

## Regra de seleção

Um caso entra no subconjunto quando:

```text
nota histórica do AmazoniaExpert.IA <= 3
OU
capitulo_recuperado histórico == False
```

No SPAmazon-QA isso produz:

- 23 casos com nota histórica 1, 2 ou 3;
- 12 casos históricos com falha de recuperação;
- 3 casos pertencentes aos dois grupos: 11, 102 e 124;
- **32 casos críticos únicos**.

Distribuição das notas baixas:

| Nota | Casos |
|---|---:|
| 1 | 1 |
| 2 | 4 |
| 3 | 18 |

IDs selecionados:

```text
9, 11, 15, 27, 34, 35, 36, 53, 58, 59, 63, 65, 67, 72, 77, 83,
90, 96, 97, 98, 99, 100, 102, 104, 105, 106, 110, 116, 117, 124, 125, 126
```

Essa seleção prévia evita escolher apenas casos que posteriormente favoreçam alguma variante.

---

## 14. Pipeline downstream: retrieval separado da geração

O texto processado de P1-P4 é usado para recuperar, mas **não será entregue diretamente ao gerador**.

Para cada variante:

```text
pergunta
   |
   v
preprocessamento Pk
   |
   v
índice Pk
   |
   v
Top-5 chunk IDs
   |
   v
lookup dos mesmos IDs em p0_chunks.jsonl
   |
   v
texto ORIGINAL dos 5 chunks
   |
   v
ClimateChat
   |
   v
resposta Pk
   |
   v
Juiz LLM
```

Essa decisão isola o efeito do pré-processamento na **seleção do contexto**, sem confundir retrieval com possíveis danos de legibilidade causados por stemming, lematização ou remoção de stopwords.

O experimento principal continua usando Top-10 para métricas. A geração downstream usa Top-5 para manter proximidade com a arquitetura original do AmazoniaExpert.IA.

---

## 15. Geração ClimateChat nos casos críticos

Configuração a ser reproduzida do TCC:

```text
temperature = 0.1
top_p = 0.9
repeat_penalty = 1.15
max_tokens = 2048
n_ctx = 8192
```

Será utilizado o mesmo modelo local ClimateChat em GGUF e o mesmo prompt final do AmazoniaExpert.IA, com restrição para responder a partir do contexto recuperado.

Para cada um dos 32 casos serão geradas respostas com:

```text
P0_CONTROLLED
P1
P2
P3
P4
```

Total:

```text
32 casos x 5 condições = 160 novas respostas
```

---

## 16. Juiz LLM na análise downstream

O protocolo de avaliação seguirá o desenho utilizado no TCC:

```text
Modelo: llama-3.3-70b-versatile
Infraestrutura: Groq
Temperature: 0.0
Persona: Professor Doutor especialista na Amazônia
Entrada: pergunta + gabarito + resposta
Saída: JSON com nota 1-5 + justificativa
```

Escala:

| Nota | Interpretação |
|---|---|
| 1 | Incorreta / irrelevante |
| 2 | Insuficiente, com erros graves ou omissões centrais |
| 3 | Parcial, correta em parte, mas incompleta ou superficial |
| 4 | Boa, majoritariamente correta, com falhas mínimas |
| 5 | Excelente, completa e cientificamente aderente |

### Controle de possível drift do juiz

As notas históricas do TCC serão preservadas, mas não serão a única base de comparação.

As 32 respostas históricas do AmazoniaExpert.IA também serão submetidas novamente ao juiz atual, na mesma rodada das novas respostas.

Assim, o conjunto de avaliação atual terá:

```text
32 respostas históricas reavaliadas
+ 32 P0_CONTROLLED
+ 32 P1
+ 32 P2
+ 32 P3
+ 32 P4
= 192 avaliações atuais do Juiz LLM
```

Se o modelo original do juiz não estiver mais disponível, qualquer substituição deverá ser registrada e as notas novas não serão tratadas como diretamente equivalentes às históricas.

---

## 17. Análise dos 32 casos críticos

Para cada pergunta serão comparados:

- nota histórica;
- nota atual da resposta histórica;
- rank do primeiro documento correto em P0-P4;
- capítulos presentes no Top-5;
- resposta P0_CONTROLLED;
- respostas P1-P4;
- notas e justificativas atuais do juiz.

Principais deltas:

```text
DeltaJudge(P1) = Nota(P1) - Nota(P0_CONTROLLED)
DeltaJudge(P2) = Nota(P2) - Nota(P0_CONTROLLED)
DeltaJudge(P3) = Nota(P3) - Nota(P0_CONTROLLED)
DeltaJudge(P4) = Nota(P4) - Nota(P0_CONTROLLED)
```

Serão contabilizados:

- casos que melhoraram;
- empates;
- casos que pioraram;
- média e mediana das notas;
- transições de nota, por exemplo `3 -> 4`;
- retrieval melhorou + resposta melhorou;
- retrieval melhorou + resposta não melhorou;
- retrieval piorou + resposta piorou;
- resposta mudou sem mudança relevante no rank.

Como o subconjunto foi selecionado por falha ou baixa nota histórica, essa etapa é tratada como **análise exploratória de causa-raiz**, não como estimativa global das 130 perguntas.

---

## 18. Arquivos planejados para a etapa downstream

```text
data/reference/downstream_critical_cases.jsonl
results/tables/downstream_critical_cases.csv
results/raw/downstream_retrieval_top5.csv
results/raw/downstream_generated_answers.csv
results/raw/downstream_judge_scores.csv
results/metrics/downstream_summary.csv
results/cases/downstream_case_reports/
```

---

## 19. Estrutura do repositório

```text
PLN-TRABALHO-FINAL/
|
+-- data/
|   +-- reference/
|   +-- processed/
|
+-- docs/
|   +-- registro_experimental.md
|
+-- results/
|   +-- cases/
|   +-- metrics/
|   +-- raw/
|   +-- runs/
|   +-- tables/
|
+-- scripts/
+-- src/
+-- tests/
|
+-- SPAmazon-QA.json
+-- Roteiro_Trabalho_Final_PLN.pdf
+-- README.md
```

---

## 20. Principais comandos já utilizados

### Validar corpus

```powershell
python .\scripts\validate_p0_chapters.py
```

### Validar SPAmazon-QA

```powershell
python .\scripts\validate_spamazon_qa.py
```

### Inspecionar pré-processamento

```powershell
python .\scripts\inspect_preprocessing.py
```

### Executar testes automatizados

```powershell
pytest .\tests\test_preprocessing.py -v
```

### Gerar corpora P1-P4

```powershell
python .\scripts\build_preprocessed_corpora.py
```

### Construir os índices controlados

```powershell
& "C:\TCCII\UNSTRUCTURED\.venv\Scripts\python.exe" `
".\scripts\build_controlled_vector_dbs.py"
```

---

## 21. Status atual

### Concluído

- auditoria do corpus P0;
- exportação dos 6.900 chunks;
- identificação dos 38 documentos canônicos;
- validação das 130 perguntas;
- reprodução da baseline histórica;
- definição e congelamento de P0-P4;
- validação manual do pré-processamento;
- 10 testes automatizados aprovados;
- geração e auditoria dos corpora P1-P4;
- hashes para reprodutibilidade;
- documentação experimental e README.

### Em execução

- construção controlada dos índices P0-P4.

### Próximos passos

1. validar os cinco índices;
2. executar 650 consultas e salvar 6.500 posições de ranking;
3. calcular Hit@k e MRR@10;
4. comparar P1-P4 com P0_CONTROLLED;
5. analisar por tipo e dificuldade;
6. materializar os 32 casos críticos;
7. executar geração ClimateChat nesses casos;
8. realizar 192 avaliações atuais com Juiz LLM;
9. produzir análise de causa-raiz, tabelas e figuras finais.

---

## 22. Registro experimental

Decisões metodológicas, auditorias, divergências e resultados intermediários são registrados em:

```text
docs/registro_experimental.md
```

---

## Autoria

**Ana Clara Guerra**

Projeto desenvolvido no contexto da disciplina **INF 791 - Processamento de Linguagem Natural**.
