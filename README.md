# Impacto do Pré-processamento Linguístico na Recuperação Semântica de Documentos Científicos

Trabalho final da disciplina **INF 791 — Processamento de Linguagem Natural**, desenvolvido a partir do corpus, benchmark e sistema RAG do projeto **AmazoniaExpert.IA**.

## 1. Objetivo e questões de pesquisa

O projeto investiga como estratégias clássicas de pré-processamento linguístico afetam a recuperação semântica baseada em embeddings contextuais em um corpus científico sobre a Amazônia.

### RQ1 — questão principal

> **Como diferentes estratégias de pré-processamento linguístico afetam a recuperação semântica de capítulos de origem de perguntas científicas sobre a Amazônia?**

O experimento principal isola a etapa de *retrieval*. Corpus, chunks, IDs, metadados, encoder, banco vetorial, parâmetros de busca e conjunto de perguntas são mantidos controlados; a variável experimental é a transformação linguística aplicada ao texto.

### RQ2 — análise downstream exploratória

Como análise secundária, o trabalho examina 32 casos críticos para investigar se alterações no retrieval se propagam para a qualidade da resposta final do sistema RAG.

### RQ3 — extensão mecanística exploratória pós-resultados

Após o fechamento do experimento principal e da análise downstream, foi executada uma extensão mecanística, explicitamente identificada como **exploratória pós-resultados**:

> **Em que medida as estratégias de pré-processamento alteram a tokenização e a representação vetorial produzida pelo `all-mpnet-base-v2`, e essas alterações estão associadas à estabilidade do ranking e ao desempenho de recuperação?**

A extensão não modifica as variantes, os índices, os rankings, as respostas RAG ou os resultados principais. Seu objetivo é abrir a etapa intermediária:

```text
pré-processamento
        ↓
tokenização
        ↓
embedding
        ↓
ranking
        ↓
contexto RAG
        ↓
resposta
```

---

## 2. Base experimental

### Corpus

| Característica | Valor |
|---|---:|
| Documentos científicos | 38 |
| Páginas de origem | 1.337 |
| Chunks | 6.900 |
| IDs únicos de chunks | 6.900 |
| Documentos canônicos | 38 |
| Dimensionalidade dos embeddings | 768 |

O texto armazenado na baseline preserva a estrutura utilizada na vetorização original:

```text
Chapter + Section + Content
```

### Benchmark SPAmazon-QA

| Característica | Valor |
|---|---:|
| Perguntas | 130 |
| IDs únicos | 130 |
| Documentos-alvo canônicos | 38 |
| Direct | 53 |
| Indirect | 77 |
| Easy | 7 |
| Medium-Low | 28 |
| Medium-High | 16 |
| Hard | 79 |

O arquivo original `SPAmazon-QA.json` é preservado. Rankings, métricas, respostas e avaliações do novo experimento são armazenados separadamente.

---

## 3. Variantes de pré-processamento

| Variante | Transformação |
|---|---|
| **P0** | Texto original, sem novo pré-processamento |
| **P1** | Lowercase |
| **P2** | Lowercase + remoção controlada de stopwords |
| **P3** | Lowercase + lematização |
| **P4** | Lowercase + Porter stemming |

A mesma variante é aplicada aos chunks e às consultas **somente para retrieval**.

Em P2–P4 foi congelada, antes da inspeção dos resultados experimentais, uma lista de termos semanticamente críticos relacionados a temporalidade, negação, lógica, quantificação e comparação. Exemplos:

```text
since, before, after, between, from, to
not, no, without
and, or, but
all, same, every
more, less, greater, higher, lower, than
```

Implementação congelada:

```text
src/preprocess.py
```

SHA-256:

```text
050AEC627D8DA62FAC2F0B8E364FDC9D3102368F1464B17240187E964ACA6610
```

A suíte automatizada de validação terminou com:

```text
10 passed
```

---

## 4. Indexação vetorial controlada

Todos os índices utilizam:

```text
Encoder: sentence-transformers/all-mpnet-base-v2
Dimensionalidade: 768
Vector DB: ChromaDB
Índice aproximado: HNSW
Coleção: langchain
Chunks por índice: 6.900
```

Foram construídos cinco índices independentes:

```text
P0
P1
P2
P3
P4
```

Os cinco índices usam os mesmos IDs, a mesma ordem de inserção, os mesmos metadados e o mesmo encoder. A única diferença sistemática entre eles é a representação textual produzida pela estratégia de pré-processamento.

Os bancos vetoriais experimentais são armazenados fora do repositório por serem artefatos binários reconstruíveis.

---

## 5. Protocolo principal de recuperação

Cada uma das 130 perguntas é submetida às cinco condições:

```text
130 perguntas × 5 variantes = 650 consultas
```

Para cada consulta são armazenados os 10 chunks mais próximos:

```text
130 × 5 × Top-10 = 6.500 posições de ranking
```

Fluxo experimental:

```text
pergunta original
        |
        v
pré-processamento Pk
        |
        v
all-mpnet-base-v2
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

### Métricas

- Chapter Hit@1
- Chapter Hit@3
- Chapter Hit@5
- Chapter Hit@10
- First Relevant Rank
- MRR@10
- deltas em relação a P0

O capítulo de origem funciona como uma **proxy operacional de relocalização da fonte**. Um chunk de outro capítulo pode conter evidência cientificamente útil; portanto, Chapter Hit@k não deve ser interpretado como anotação absoluta de relevância por chunk.

---

## 6. Resultados globais de recuperação

| Variante | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 |
|---|---:|---:|---:|---:|---:|
| **P0** | **79,23%** | **90,00%** | **93,08%** | **95,38%** | **0,8507** |
| **P1** | **79,23%** | **90,00%** | **93,08%** | **95,38%** | **0,8507** |
| P2 | 70,77% | 80,77% | 83,08% | 89,23% | 0,7657 |
| P3 | 73,85% | 89,23% | 90,77% | 93,85% | 0,8152 |
| P4 | 60,77% | 73,08% | 80,77% | 85,38% | 0,6909 |

Diferenças em relação a P0:

| Variante | Δ Hit@1 | Δ Hit@3 | Δ Hit@5 | Δ Hit@10 | Δ MRR@10 |
|---|---:|---:|---:|---:|---:|
| P1 | 0,00 pp | 0,00 pp | 0,00 pp | 0,00 pp | 0,0000 |
| P2 | -8,46 pp | -9,23 pp | -10,00 pp | -6,15 pp | -0,0850 |
| P3 | -5,38 pp | -0,77 pp | -2,31 pp | -1,54 pp | -0,0356 |
| P4 | -18,46 pp | -16,92 pp | -12,31 pp | -10,00 pp | -0,1598 |

### Testes estatísticos

As comparações são pareadas, pois as mesmas 130 perguntas são avaliadas em todas as condições.

- Hit@k: teste exato de McNemar;
- MRR@10: Wilcoxon pareado;
- múltiplas comparações: correção de Holm-Bonferroni sobre 20 testes.

Sob `α = 0,05`:

- **P1** não difere de P0;
- **P2** apresenta diferença significativa em Hit@5 e MRR@10;
- **P3** não mantém diferenças significativas após a correção;
- **P4** apresenta diferenças significativas em todas as cinco métricas.

Resultados principais corrigidos:

```text
P2
Hit@5   p_Holm ≈ 0,0146
MRR@10  p_Holm ≈ 0,0153

P4
Hit@1   p_Holm < 0,001
Hit@3   p_Holm < 0,001
Hit@5   p_Holm ≈ 0,0064
Hit@10  p_Holm ≈ 0,0042
MRR@10  p_Holm < 0,001
```

### Interpretação

No corpus, encoder e protocolo avaliados:

- lowercase isolado foi neutro;
- remoção de stopwords degradou a recuperação em parte relevante das métricas;
- lematização foi a transformação adicional menos prejudicial e produziu ganhos localizados;
- Porter stemming apresentou a degradação global mais forte e consistente;
- nenhuma transformação adicional superou P0 globalmente.

Esses resultados são específicos ao `all-mpnet-base-v2`, ao SPAmazon-QA e ao protocolo adotado.

---

## 7. Extensão mecanística RQ3

A extensão foi definida **depois dos resultados principais**, mas seu protocolo, métricas e testes foram congelados antes de sua execução. Ela reutiliza os mesmos artefatos P0–P4 e não executa nova recuperação.

### 7.1 Preflight e ambiente

O preflight confirmou:

```text
6.900 chunks em cada P0-P4
IDs dos chunks idênticos
130 consultas em cada P0-P4
P0 idêntica às perguntas originais
650 combinações questão-variante
6.500 posições Top-10
Encoder = sentence-transformers/all-mpnet-base-v2
Dimensão = 768
Tokenizer = MPNetTokenizer
model.max_seq_length = 384
```

Ambiente da execução:

```text
Python: 3.13.3
sentence-transformers: 5.3.0
transformers: 5.4.0
torch: 2.11.0
numpy: 2.4.4
pandas: 3.0.2
scipy: 1.17.1
```

### 7.2 Unidades analisadas

```text
130 perguntas × 4 comparações com P0 = 520 observações de consultas

6.900 chunks × 4 comparações com P0 = 27.600 observações de corpus
```

A inferência estatística é concentrada nas 130 consultas pareadas. As 27.600 comparações de chunks são utilizadas principalmente de forma descritiva.

### 7.3 Tokenização

Foi utilizado o tokenizer real do MPNet.

#### Consultas

| Variante | Subwords P0 | Subwords Pk | Δ médio | Mudança relativa média | Sequência tokenizada alterada |
|---|---:|---:|---:|---:|---:|
| P1 | 21,469 | 21,469 | 0,000 | 0,00% | 0,0% |
| P2 | 21,469 | 15,238 | -6,231 | 29,24% | 100,0% |
| P3 | 21,469 | 21,500 | +0,031 | 0,75% | 99,2% |
| P4 | 21,469 | 25,915 | +4,446 | 21,61% | 100,0% |

#### Chunks

| Variante | Subwords P0 | Subwords Pk | Δ médio | Mudança relativa média | Sequência tokenizada alterada |
|---|---:|---:|---:|---:|---:|
| P1 | 177,581 | 177,581 | 0,000 | 0,00% | 0,0% |
| P2 | 177,581 | 152,824 | -24,756 | 14,36% | 99,29% |
| P3 | 177,581 | 177,105 | -0,476 | 0,76% | 99,81% |
| P4 | 177,581 | 204,007 | +26,427 | 16,03% | 100,0% |

A razão média `subwords/palavra` nos chunks passou de `1,554` em P0 para `1,786` em P4, evidenciando maior fragmentação subword após stemming.

O truncamento dos chunks também mudou:

```text
P0/P1: 21 chunks truncados
P2:    14
P3:    21
P4:    31
```

### 7.4 Deriva dos embeddings

A medida principal é:

```text
embedding_drift = 1 - cosine(P0, Pk)
```

#### Consultas

| Variante | Cosseno médio | Drift médio | Drift mediano |
|---|---:|---:|---:|
| P1 | 1,000000 | ≈0,000000 | 0,000000 |
| P2 | 0,930832 | 0,069168 | 0,064964 |
| P3 | 0,960339 | 0,039661 | 0,030069 |
| P4 | 0,812659 | **0,187341** | **0,160366** |

#### Chunks

| Variante | Cosseno médio | Drift médio | Drift mediano |
|---|---:|---:|---:|
| P1 | 1,000000 | ≈0,000000 | 0,000000 |
| P2 | 0,976116 | 0,023884 | 0,017332 |
| P3 | 0,984132 | 0,015868 | 0,011972 |
| P4 | 0,878721 | **0,121279** | **0,108292** |

A ordem descritiva da perturbação foi:

```text
P1 < P3 < P2 < P4
```

Essa mesma ordenação acompanha a tendência de degradação global da recuperação.

### 7.5 Testes estatísticos da deriva

Nas 130 consultas:

```text
Friedman χ² = 344,1963
p = 2,6935 × 10^-74
```

Como o teste global foi significativo, foram realizados Wilcoxon pareados entre as quatro variantes, com correção de Holm.

| Comparação | p ajustado por Holm |
|---|---:|
| P1 × P2 | 2,676 × 10^-22 |
| P1 × P3 | 2,676 × 10^-22 |
| P1 × P4 | 2,676 × 10^-22 |
| P2 × P3 | 6,448 × 10^-13 |
| P2 × P4 | 8,278 × 10^-20 |
| P3 × P4 | 2,676 × 10^-22 |

Todas as seis comparações permaneceram significativas sob `α = 0,05`.

### 7.6 Deriva do embedding × estabilidade do ranking

A estabilidade do Top-10 foi medida por overlap e índice de Jaccard entre o ranking P0 e o ranking Pk.

O principal resultado inferencial foi observado em P4:

```text
embedding drift × Jaccard Top-10
rho = -0,3375
p = 8,588 × 10^-5
p_Holm = 0,000344
```

Assim, dentro de P4, maior afastamento da representação em relação a P0 esteve significativamente associado à menor estabilidade do conjunto Top-10.

Em P3, a associação foi negativa no valor bruto, mas não permaneceu significativa após correção:

```text
rho = -0,1970
p = 0,0247
p_Holm = 0,0741
```

Na associação entre `embedding_drift` e `|ΔRR@10|`, P4 apresentou:

```text
rho = 0,2075
p = 0,0178
p_Holm = 0,0714
```

Portanto, esse segundo resultado é tratado apenas como tendência exploratória.

### 7.7 Interpretação mecanística

Os resultados permitem aprofundar a interpretação do experimento principal:

- **P1:** o lowercase externo não alterou nenhuma sequência tokenizada nas consultas ou chunks; os embeddings foram numericamente equivalentes a P0, o que explica a neutralidade do retrieval;
- **P3:** a lematização alterou quase todas as sequências tokenizadas, mas produziu pouca mudança no número de subwords e baixa deriva vetorial;
- **P2:** a remoção de stopwords reduziu substancialmente o número de tokens e produziu deriva intermediária;
- **P4:** o stemming aumentou a fragmentação subword, elevou o comprimento tokenizado, aumentou os casos de truncamento e apresentou a maior deriva vetorial.

Esses resultados são **consistentes com a hipótese** de que transformações lexicais mais disruptivas perturbem a representação esperada pelo encoder contextual e, consequentemente, a recuperação. A análise não estabelece causalidade e não deve ser generalizada para outros encoders ou corpora.

---

## 8. Caso sentinela — Questão 11

A Questão 11 contém a restrição temporal:

```text
since the 1970s
```

O documento-alvo é o Chapter 17.

Em P0, a recuperação foi dominada pelo:

```text
Chapter 11 — Economic Drivers in the Amazon from the 19th Century to the 1970s
```

O Chapter 17 não apareceu no Top-10. Nenhuma variante P0–P4 corrigiu essa falha.

O caso evidencia que:

```text
since the 1970s != to the 1970s
```

e funciona como exemplo qualitativo de uma limitação da recuperação densa em relações semânticas direcionais.

---

## 9. Análise downstream

### Seleção dos casos críticos

O subconjunto downstream foi congelado **antes da inspeção dos resultados P1–P4**, usando apenas informações históricas do TCC.

Regra:

```text
nota histórica do AmazoniaExpert.IA <= 3
OU
falha histórica de recuperação
```

Resultado:

```text
32 casos críticos únicos
```

IDs:

```text
9, 11, 15, 27, 34, 35, 36, 53, 58, 59, 63, 65, 67, 72, 77, 83,
90, 96, 97, 98, 99, 100, 102, 104, 105, 106, 110, 116, 117, 124, 125, 126
```

Esse subconjunto é utilizado para **análise exploratória de causa-raiz** e não representa a distribuição completa das 130 perguntas.

### Controle retrieval → geração

P1–P4 determinam apenas **quais chunks são recuperados**.

O ClimateChat recebe sempre:

- a pergunta original;
- o texto original P0 dos chunks selecionados;
- o mesmo prompt RAG do AmazoniaExpert.IA.

Fluxo:

```text
consulta processada Pk
        |
        v
Top-5 congelado
        |
        v
IDs dos chunks
        |
        v
texto original P0
        |
        v
prompt RAG
        |
        v
ClimateChat
        |
        v
resposta
```

Foram produzidas:

```text
32 perguntas × 5 variantes = 160 respostas RAG
```

### Gerador

```text
Modelo: ClimateChat.i1-Q4_K_M.gguf
temperature = 0.1
top_p = 0.9
top_k = 40
repeat_penalty = 1.15
max_tokens = 2048
n_ctx = 8192
n_gpu_layers = 0
seed = 42
```

A seed é reinicializada antes de cada completion:

```text
reset -> set_seed(42) -> create_completion(seed=42)
```

Protocolo:

```text
downstream-rag-fixed-seed-v2
```

---

## 10. Juiz LLM downstream

O protocolo reproduz literalmente a estrutura do prompt utilizada no TCC.

Modelo histórico:

```text
llama-3.3-70b-versatile
```

Como esse modelo não estava disponível na conta Groq utilizada na nova execução, o avaliador atual foi substituído por:

```text
openai/gpt-oss-120b
```

Configuração:

```text
temperature = 0.0
reasoning_effort = medium
entrada = pergunta + gabarito + resposta
saída = JSON {"nota": ..., "justificativa": "..."}
```

A avaliação é cega: o juiz não recebe variante, metadados de retrieval, indicação de resposta histórica ou informações sobre o pré-processamento.

Após deduplicação:

```text
192 registros finais
160 respostas P0-P4
32 respostas históricas reavaliadas
154 entradas únicas para o juiz
38 vereditos reutilizados
```

Protocolo:

```text
judge-tcc-prompt-gptoss120b-dedup-v3
```

---

## 11. Sensibilidade à substituição do Juiz LLM

As mesmas 32 respostas históricas foram avaliadas pelo juiz histórico e pelo juiz atual.

| Avaliação | Média | Mediana | DP |
|---|---:|---:|---:|
| Juiz histórico | 3,125 | 3 | 0,793 |
| GPT-OSS-120B | 1,969 | 2 | 0,695 |

Resultado:

```text
Δ médio = -1,156
29/32 respostas receberam nota menor
3/32 permaneceram iguais
0/32 receberam nota maior
Wilcoxon p ≈ 6,60 × 10^-7
```

Isso demonstra **sensibilidade à substituição do modelo avaliador**. As escalas absolutas produzidas pelos dois juízes não são tratadas como diretamente equivalentes.

A média histórica global do AmazoniaExpert.IA no TCC permanece **4,14/5 nas 130 questões sob o protocolo histórico**. As notas atuais dos 32 casos críticos não substituem, não recalculam e não reduzem retroativamente esse resultado.

---

## 12. Resultados downstream P0–P4

| Variante | N | Média | Mediana | DP |
|---|---:|---:|---:|---:|
| P0 | 32 | 2,188 | 2 | 0,896 |
| P1 | 32 | 2,156 | 2 | 0,884 |
| P2 | 32 | 2,250 | 2 | 0,984 |
| P3 | 32 | 2,000 | 2 | 0,622 |
| P4 | 32 | 2,406 | 2 | 0,979 |

Comparações pareadas com P0:

| Variante | Melhorou | Igual | Piorou | Δ médio | p bruto | p Holm |
|---|---:|---:|---:|---:|---:|---:|
| P1 | 0 | 31 | 1 | -0,031 | 0,317311 | 0,895243 |
| P2 | 6 | 19 | 7 | +0,062 | 0,743584 | 0,895243 |
| P3 | 5 | 18 | 9 | -0,188 | 0,237175 | 0,895243 |
| P4 | 10 | 15 | 7 | +0,219 | 0,223811 | 0,895243 |

Teste global de Friedman:

```text
χ²_F = 4,8500
p = 0,303038
```

Não foi detectada diferença global estatisticamente significativa entre P0–P4 nas 32 perguntas críticas.

### Retrieval × qualidade da resposta

Nos 160 registros controlados:

```text
capítulo-alvo ausente do Top-5:
n = 45
nota média = 2,178

capítulo-alvo presente no Top-5:
n = 115
nota média = 2,209
```

Correlação entre RR@10 e nota:

```text
Spearman rho = 0,0908
p = 0,253312
```

Nesse subconjunto crítico, a posição do capítulo-alvo isoladamente não explica a qualidade final da resposta.

A conclusão downstream é:

> **mudanças no retrieval podem se propagar para a geração, mas essa propagação não é determinística.**

---

## 13. Casos qualitativos principais

- **Q11** — falha temporal persistente; nenhuma variante recuperou o Chapter 17 no Top-5;
- **Q65** — P3/P4 levam o documento-alvo ao Top-5, mas a melhora de retrieval não produz melhora automática da nota;
- **Q83** — maior presença do capítulo-alvo em P4 acompanha melhora de nota de 2 para 3;
- **Q124** — P2 introduz o Chapter 15 no Top-5, mas a nota cai de 3 para 2.

Na extensão mecanística, também foi acompanhado:

- **Q58** — P0/P1 mantêm o mesmo primeiro rank relevante, mas diferem na composição completa do Top-5.

---

## 14. Figuras finais

Os artefatos visuais oficiais estão em:

```text
results/figures_final/
├── fig01_downstream_likert.png
├── fig01_downstream_likert.pdf
├── fig02_downstream_delta.png
├── fig02_downstream_delta.pdf
├── fig03_judge_sensitivity.png
├── fig03_judge_sensitivity.pdf
├── fig04_hit5_vs_score.png
├── fig04_hit5_vs_score.pdf
├── fig05_retrieval_global.png
├── fig05_retrieval_global.pdf
├── fig06_query_embedding_drift.png
├── fig06_query_embedding_drift.pdf
├── fig07_ranking_stability.png
├── fig07_ranking_stability.pdf
├── fig08_representation_mechanism_combined.png
└── fig08_representation_mechanism_combined.pdf
```

Scripts:

```text
scripts/generate_final_figures.py
scripts/generate_mechanistic_combined_figure.py
```

### Figuras principais selecionadas para o artigo

```text
fig05_retrieval_global
fig08_representation_mechanism_combined
fig02_downstream_delta
```

Função de cada figura:

- **fig05** — desempenho global de recuperação, respondendo diretamente à RQ1;
- **fig08** — relação entre alteração da representação e estabilidade do ranking, sustentando a RQ3;
- **fig02** — comportamento downstream das variantes em relação a P0, relacionado à RQ2.

As figuras `fig01`, `fig03`, `fig04`, `fig06` e `fig07` permanecem como resultados complementares e material para apresentação.

---

## 15. Principais artefatos

```text
data/reference/
├── p0_chunks.jsonl
└── downstream_critical_cases.jsonl

results/raw/
├── controlled_rankings.csv
├── downstream_responses_rag.csv
├── downstream_responses_rag.jsonl
├── downstream_judge_evaluations.csv
├── representation_shift_queries.csv
└── representation_shift_chunks.csv

results/metrics/
├── controlled_question_metrics.csv
├── controlled_summary.csv
├── controlled_deltas_vs_p0.csv
├── downstream_summary.csv
├── downstream_pairwise_vs_p0.csv
├── downstream_global_tests.csv
├── judge_sensitivity_summary.csv
├── judge_sensitivity_per_question.csv
├── retrieval_answer_relationship.csv
├── retrieval_change_answer_change.csv
├── retrieval_change_answer_change_per_question.csv
├── retrieval_delta_answer_delta_correlations.csv
├── representation_shift_summary.csv
├── representation_tokenization_summary.csv
├── representation_ranking_stability.csv
├── representation_retrieval_correlations.csv
└── representation_statistical_tests.csv

results/tables/
├── controlled_statistical_tests_vs_p0.csv
├── downstream_critical_cases.csv
├── downstream_score_distribution.csv
├── downstream_key_cases.csv
└── representation_key_cases.csv

results/runs/
├── controlled_retrieval_run.json
├── controlled_analysis_summary.txt
├── downstream_generation_run.json
├── downstream_judge_run.json
├── downstream_analysis_summary.txt
├── downstream_analysis_run.json
├── representation_shift_summary.txt
└── representation_shift_run.json

results/figures_final/
└── figuras finais em PNG e PDF
```

---

## 16. Reprodutibilidade

### Testes de pré-processamento

```powershell
pytest .\tests\test_preprocessing.py -v
```

### Análise dos resultados controlados de retrieval

```powershell
& "C:\TCCII\UNSTRUCTURED\.venv\Scripts\python.exe" `
".\scripts\analyze_controlled_results.py"
```

### Análise downstream

```powershell
& "C:\TCCII\UNSTRUCTURED\.venv\Scripts\python.exe" `
".\scripts\analyze_downstream_results.py"
```

### Extensão mecanística RQ3 — preflight

```powershell
& "C:\TCCII\UNSTRUCTURED\.venv\Scripts\python.exe" `
".\scripts\analyze_representation_shift.py" `
--validate-only
```

### Extensão mecanística RQ3 — análise completa

```powershell
& "C:\TCCII\UNSTRUCTURED\.venv\Scripts\python.exe" `
".\scripts\analyze_representation_shift.py"
```

### Figuras P0–P4/downstream

```powershell
& "C:\TCCII\UNSTRUCTURED\.venv\Scripts\python.exe" `
".\scripts\generate_final_figures.py"
```

### Figura mecanística combinada

```powershell
& "C:\TCCII\UNSTRUCTURED\.venv\Scripts\python.exe" `
".\scripts\generate_mechanistic_combined_figure.py"
```

As decisões metodológicas, divergências de reprodução, hashes, auditorias e resultados intermediários são documentados em:

```text
docs/registro_experimental.md
```

---

## 17. Estrutura do repositório

```text
PLN-TRABALHO-FINAL/
├── data/
│   ├── reference/
│   └── processed/
├── docs/
│   └── registro_experimental.md
├── results/
│   ├── cases/
│   ├── figures_final/
│   ├── metrics/
│   ├── raw/
│   ├── runs/
│   └── tables/
├── scripts/
├── src/
├── tests/
├── SPAmazon-QA.json
├── Roteiro_Trabalho_Final_PLN.pdf
└── README.md
```

---

## 18. Status atual

### Concluído

- auditoria do corpus P0;
- canonicalização dos 38 documentos;
- validação das 130 perguntas;
- reprodução da baseline histórica;
- definição e congelamento de P0–P4;
- validação manual e automatizada do pré-processamento;
- geração dos corpora derivados;
- construção dos cinco índices vetoriais controlados;
- execução das 650 consultas;
- análise de 6.500 posições de ranking;
- cálculo de Hit@k e MRR@10;
- testes estatísticos pareados com correção de Holm;
- seleção prévia dos 32 casos críticos;
- geração de 160 respostas RAG controladas;
- avaliação downstream com 192 registros finais;
- análise da sensibilidade à substituição do Juiz LLM;
- análise integrada retrieval → contexto → geração → nota;
- definição e congelamento da extensão mecanística RQ3;
- preflight completo da extensão;
- análise de tokenização das 130 consultas e dos 6.900 chunks;
- 520 comparações de representação entre consultas P0 e P1–P4;
- 27.600 comparações de representação entre chunks P0 e P1–P4;
- análise de deriva dos embeddings;
- análise de estabilidade Top-10;
- testes Friedman, Wilcoxon e Spearman com correção de Holm;
- geração de `fig06`, `fig07` e `fig08`;
- consolidação do registro experimental.

### Fase atual

**Etapa experimental encerrada. Próxima fase: redação do artigo científico final no Overleaf e preparação posterior da apresentação.**

Não estão previstas novas variantes, novos encoders ou novas avaliações com outro Juiz LLM apenas para modificar os resultados observados.

---

## Autoria

**Ana Clara Guerra**

Projeto desenvolvido no contexto da disciplina **INF 791 — Processamento de Linguagem Natural**.
