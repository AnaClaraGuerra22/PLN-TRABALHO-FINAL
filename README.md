# Impacto do Pré-processamento Linguístico na Recuperação Semântica de Documentos Científicos

Trabalho Final da disciplina **INF 791 — Processamento de Linguagem Natural**, desenvolvido a partir do corpus e do benchmark construídos no projeto **AmazoniaExpert.IA**.

---

## 1. Visão geral

Este projeto investiga o efeito de diferentes estratégias clássicas de pré-processamento linguístico sobre a recuperação semântica de documentos científicos utilizando embeddings densos.

A questão central do experimento é:

> **Como diferentes estratégias de pré-processamento linguístico afetam a recuperação semântica de capítulos de origem de perguntas científicas sobre a Amazônia?**

O experimento utiliza documentos científicos produzidos pelo **Science Panel for the Amazon (SPA)** e perguntas pertencentes ao benchmark **SPAmazon-QA**.

A arquitetura avaliada utiliza:

- embeddings densos;
- `sentence-transformers/all-mpnet-base-v2`;
- ChromaDB;
- índice HNSW;
- recuperação Top-k;
- avaliação baseada no capítulo de origem da pergunta.

O objetivo não é avaliar geração de respostas por LLM, mas isolar especificamente o comportamento da etapa de **recuperação semântica**.

---

## 2. Corpus

O corpus utilizado neste experimento é derivado da base documental do AmazoniaExpert.IA.

Após auditoria, foram identificados:

| Característica | Valor |
|---|---:|
| Documentos científicos | 38 |
| Chunks | 6.900 |
| Capítulos regulares | 34 |
| Cross Chapters | 2 |
| Anexos | 2 |
| Dimensionalidade dos embeddings | 768 |

Os 38 documentos correspondem a 34 capítulos regulares, dois Cross Chapters e dois anexos.

Cada chunk mantém os metadados de origem, incluindo documento, capítulo, seção e página.

---

## 3. Benchmark SPAmazon-QA

A avaliação utiliza o **SPAmazon-QA**, conjunto curado de perguntas e respostas científicas sobre a Amazônia.

| Característica | Valor |
|---|---:|
| Perguntas | 130 |
| IDs únicos | 130 |
| Documentos-alvo canônicos | 38 |
| Perguntas Direct | 53 |
| Perguntas Indirect | 77 |

### Distribuição por dificuldade

| Dificuldade | Perguntas |
|---|---:|
| Easy | 7 |
| Medium-Low | 28 |
| Medium-High | 16 |
| Hard | 79 |

O campo `capitulo_alvo` apresentou originalmente 39 grafias diferentes, normalizadas para 38 identificadores canônicos.

Exemplo:

```text
Capítulo CC2
Capítulo Cross Chapter 2
cross_chapter_2
```

são tratados como:

```text
cross_chapter_2
```

---

## 4. Auditoria dos metadados

Durante a preparação do experimento foi identificada uma ambiguidade nos metadados históricos do corpus.

No banco original:

```text
Chapter 1       -> chapter_number = 1
Cross Chapter 1 -> chapter_number = 1

Chapter 2       -> chapter_number = 2
Cross Chapter 2 -> chapter_number = 2
```

Entretanto, o campo `source` distingue corretamente esses documentos.

Por esse motivo, a avaliação atual deriva o identificador canônico do documento prioritariamente a partir de `source`, preservando os metadados originais sem modificá-los.

| Documento | Chunks |
|---|---:|
| Chapter 1 | 243 |
| Cross Chapter 1 | 61 |
| Chapter 2 | 229 |
| Cross Chapter 2 | 18 |

A distribuição completa está disponível em:

```text
results/tables/chunks_por_documento.csv
```

---

## 5. Variantes de pré-processamento

Foram definidas cinco condições experimentais.

| Variante | Transformação |
|---|---|
| **P0** | Texto original, sem novo pré-processamento |
| **P1** | Lowercase |
| **P2** | Lowercase + remoção controlada de stopwords |
| **P3** | Lowercase + lematização |
| **P4** | Lowercase + Porter stemming |

As mesmas transformações são aplicadas tanto aos chunks quanto às consultas.

---

## 6. Preservação de relações semanticamente críticas

A remoção indiscriminada de stopwords pode eliminar palavras pequenas que carregam relações fundamentais para uma consulta científica.

Por esse motivo, foi definida previamente uma lista de operadores protegidos relacionados a temporalidade, negação, comparação, quantificação e relações lógicas.

Exemplos:

```text
since
before
after
between
from
to

not
no
without

greater
higher
lower
more
less
than

all
same
each
every

and
or
but
```

Essa lista foi definida **antes da comparação dos resultados de recuperação**, evitando ajustes pós-hoc das variantes.

---

## 7. Validação do pré-processamento

Antes da criação dos índices experimentais, as transformações foram inspecionadas manualmente em consultas representativas de temporalidade, negação, comparação, quantidade, siglas e intervalos numéricos.

Exemplo temporal:

```text
P0:
Name three major commodity or extractive activities that expanded
in the Amazon since the 1970s.

P1:
name three major commodity or extractive activities that expanded
in the amazon since the 1970s.

P2:
name three major commodity or extractive activities expanded
amazon since 1970s.

P3:
name three major commodity or extractive activity that expand
in the amazon since the 1970s.

P4:
name three major commod or extract activ that expand
in the amazon since the 1970s.
```

A saída completa está em:

```text
results/runs/preprocessing_validation_final.txt
```

Também foi criada uma suíte automatizada com `pytest`.

Resultado:

```text
10 passed
```

Arquivo:

```text
tests/test_preprocessing.py
```

---

## 8. Corpora derivados

Os quatro corpora derivados foram construídos a partir exatamente dos mesmos 6.900 registros da baseline.

Todas as variantes preservaram:

```text
6.900 chunks
6.900 IDs únicos
38 documentos
0 chunks vazios
0 alterações nos metadados
```

### Alteração no tamanho textual

| Variante | Redução de caracteres |
|---|---:|
| P1 | 0,00% |
| P2 | 11,28% |
| P3 | 2,98% |
| P4 | 11,06% |

P1 altera a caixa dos caracteres, mas não o comprimento dos textos.

---

## 9. Reprodutibilidade dos corpora

Hashes SHA-256:

```text
P0
1fce41571ca46ccca48c9aaf2fc07013aa7fe6bd215305350365eb451a73fae8

P1
0e1efcd0f921f08956529d89eb0ff267d221fbf494458c655e5e7e6eff1c3c6a

P2
48dc79cf004d56c5f25905532564fc8a0f4018f6c15fdbe241c2e6b2f8103447

P3
ae8b5ad596327372a3b5b6cf8e92a422db99ac45daae7e8f288e86e325302e99

P4
70fd5435015ba57aea468b8148190c1cc619e69796b8b33c6871cbb55ca62ded
```

SHA-256 de `src/preprocess.py`:

```text
050AEC627D8DA62FAC2F0B8E364FDC9D3102368F1464B17240187E964ACA6610
```

Também disponível em:

```text
results/runs/preprocess_hash.txt
```

---

## 10. Indexação vetorial

O modelo utilizado em todas as condições é:

```text
sentence-transformers/all-mpnet-base-v2
```

Características:

```text
Dimensionalidade: 768
Banco vetorial: ChromaDB
Índice aproximado: HNSW
Coleção: langchain
```

Para garantir um experimento controlado, os cinco índices experimentais são reconstruídos sob as mesmas condições:

```text
P0
P1
P2
P3
P4
```

Todos utilizam os mesmos 6.900 IDs, a mesma ordem de inserção, os mesmos metadados, o mesmo encoder, a mesma dimensionalidade, o mesmo tamanho de lote e a mesma configuração do banco vetorial.

Assim, a principal variável experimental é a representação textual fornecida ao modelo de embeddings.

Os bancos vetoriais não são armazenados no GitHub por serem artefatos binários reconstruíveis.

---

## 11. Protocolo de recuperação

Cada uma das 130 perguntas é submetida separadamente às cinco condições:

```text
130 perguntas x 5 variantes = 650 consultas
```

Para cada consulta são armazenados os **10 chunks mais próximos**:

```text
130 perguntas x 5 variantes x Top-10
= 6.500 posições de ranking
```

A avaliação considera o primeiro chunk pertencente ao documento de origem da pergunta.

---

## 12. Métricas

São utilizadas:

- **Hit@1**
- **Hit@3**
- **Hit@5**
- **Hit@10**
- **First Relevant Rank**
- **MRR@10**

Hit@k indica se pelo menos um chunk do documento de origem foi recuperado entre os primeiros `k` resultados.

MRR@10 considera o inverso da posição do primeiro resultado correto até a posição 10:

```text
MRR@10 = média(1 / rank do primeiro resultado correto)
```

As métricas representam a capacidade de **localizar o documento de origem** da pergunta e não devem ser interpretadas diretamente como avaliação da qualidade final de uma resposta gerada.

---

## 13. Reprodução da baseline histórica

Antes dos experimentos P1–P4 foi realizada uma reprodução da recuperação original do AmazoniaExpert.IA.

| Métrica | Resultado |
|---|---:|
| Hit@1 | 79,23% |
| Hit@3 | 90,00% |
| Hit@5 | 93,08% |
| Hit@10 | 95,38% |
| MRR@10 | 0,8507 |

No experimento histórico do TCC, o indicador equivalente ao Hit@5 havia registrado:

```text
118/130
90,8%
```

A reprodução atual apresentou concordância em:

```text
127/130 consultas
97,69%
```

As únicas divergências foram os IDs 96, 97 e 98, todos pertencentes ao **Annex II**.

Na base atualmente preservada, o Annex II foi recuperado na primeira posição para essas três consultas.

Essa diferença é registrada como uma divergência de reprodução. Os artefatos disponíveis não permitem determinar com segurança se ela decorre de reconstrução anterior do índice, alteração do estado do banco ou outra diferença histórica.

---

## 14. Caso sentinela: relações temporais

A Questão 11 do SPAmazon-QA foi selecionada como caso sentinela para relações temporais.

A pergunta solicita atividades que se expandiram:

```text
since the 1970s
```

Entretanto, a baseline P0 recuperou predominantemente:

```text
Chapter 11
Economic Drivers in the Amazon from the 19th Century to the 1970s
```

Ranking P0:

```text
1  -> Chapter 11
2  -> Chapter 11
3  -> Chapter 11
4  -> Chapter 11
5  -> Chapter 11
6  -> Chapter 11
7  -> Chapter 14
8  -> Chapter 11
9  -> Chapter 11
10 -> Chapter 11
```

O documento-alvo, **Chapter 17**, não apareceu no Top-10.

O caso evidencia a distinção entre:

```text
since the 1970s
```

e:

```text
to the 1970s
```

Apesar da alta proximidade temática, as duas expressões possuem relações temporais diferentes.

Esse caso será acompanhado individualmente nas variantes P1–P4.

---

## 15. Estrutura do repositório

```text
PLN-TRABALHO-FINAL/
│
├── data/
│   ├── reference/
│   │   ├── p0_chunks.jsonl
│   │   └── spamazon_qa_questions.jsonl
│   └── processed/
│       ├── p1_chunks.jsonl
│       ├── p2_chunks.jsonl
│       ├── p3_chunks.jsonl
│       └── p4_chunks.jsonl
│
├── docs/
│   └── registro_experimental.md
│
├── results/
│   ├── cases/
│   ├── metrics/
│   ├── raw/
│   ├── runs/
│   └── tables/
│
├── scripts/
├── src/
├── tests/
│
├── SPAmazon-QA.json
├── Roteiro_Trabalho_Final_PLN.pdf
└── README.md
```

---

## 16. Principais comandos

### Validar documentos do corpus

```powershell
python .\scripts\validate_p0_chapters.py
```

### Validar SPAmazon-QA

```powershell
python .\scripts\validate_spamazon_qa.py
```

### Inspecionar transformações linguísticas

```powershell
python .\scripts\inspect_preprocessing.py
```

### Executar testes automatizados

```powershell
pytest .\tests\test_preprocessing.py -v
```

### Construir corpora P1–P4

```powershell
python .\scripts\build_preprocessed_corpora.py
```

### Construir índices controlados P0–P4

```powershell
python .\scripts\build_controlled_vector_dbs.py
```

---

## 17. Registro experimental

Decisões metodológicas, auditorias, divergências de reprodução e resultados intermediários são registrados continuamente em:

```text
docs/registro_experimental.md
```

---

## 18. Status atual

Concluído:

- auditoria do corpus P0;
- identificação dos 38 documentos canônicos;
- separação correta dos Cross Chapters;
- validação das 130 perguntas do SPAmazon-QA;
- reprodução da baseline histórica;
- definição das variantes P0–P4;
- validação manual do pré-processamento;
- testes automatizados;
- congelamento das regras de pré-processamento;
- geração e auditoria dos corpora derivados;
- geração de hashes para reprodutibilidade.

Em execução / próximo estágio:

- construção controlada dos índices P0–P4;
- execução das 650 consultas;
- cálculo das métricas comparativas;
- análise por tipo e dificuldade;
- análise dos casos linguisticamente críticos;
- geração das tabelas e figuras finais.

---

## 19. Observação metodológica

O capítulo de origem é utilizado como referência operacional para avaliar a localização da fonte documental.

Entretanto, um chunk pertencente a outro capítulo pode conter evidência cientificamente relevante devido à redundância temática e à natureza interdisciplinar dos relatórios do Science Panel for the Amazon.

Assim, as métricas de recuperação deste trabalho avaliam principalmente a **capacidade de relocalização do documento de origem**, e não constituem, isoladamente, uma medida de relevância semântica absoluta ou da qualidade de uma resposta final produzida por um sistema RAG.

---

## Autoria

**Ana Clara Guerra**

Projeto desenvolvido no contexto da disciplina de **Processamento de Linguagem Natural — INF 791**.
