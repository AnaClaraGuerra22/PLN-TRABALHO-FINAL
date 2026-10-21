# P5 — Trechos para integrar ao artigo INF 791

**Destinação:** inserir como análise complementar no artigo *Impacto do Pré-processamento Linguístico na Recuperação Semântica de Documentos Científicos*. Texto baseado no experimento final P5, não substitui a análise P0–P4. Recomenda-se adaptar a numeração das seções ao manuscrito atual.

## Metodologia — Análise complementar de reformulação de consultas (P5)

Além das condições de pré-processamento clássico (P0–P4), investigou-se, em caráter complementar e exploratório, uma estratégia de reformulação semântica de consultas por modelo de linguagem (P5). Utilizou-se o Qwen2.5 3B, executado localmente via Ollama, com temperatura 0, semente 42, limite de 256 tokens de saída e janela de contexto de 2.048 tokens. O prompt fixo, orientado pelo domínio, informava apenas que as perguntas eram provenientes de relatórios científicos do *Science Panel for the Amazon* (SPA) e exigia preservação de conceitos, quantificadores, restrições temporais e escopo semântico. Não foram fornecidos ao reformulador os capítulos-alvo, as respostas de referência ou os chunks do corpus.

As 130 perguntas do SPAmazon-QA foram reformuladas uma vez e submetidas a uma auditoria de equivalência semântica antes da avaliação de recuperação. Foram aceitas 75 reformulações, 12 saídas permaneceram idênticas à pergunta original e 43 não foram adotadas (28 rejeitadas e 15 pendentes de revisão), sendo aplicada nestes casos a consulta original como *fallback*. Assim, as 130 consultas foram mantidas na comparação, mas apenas 75 sofreram alteração efetiva. Diferentemente de P1–P4, a condição P5 modifica somente a consulta: tanto P0 quanto P5 usam o mesmo índice P0 congelado (6.900 chunks; ChromaDB, coleção `langchain`), o mesmo encoder `sentence-transformers/all-mpnet-base-v2` e busca Top-10. A paridade dos rankings P0 reexecutados com o histórico foi verificada antes do cálculo das métricas.

A questão 11 foi empregada no desenvolvimento do prompt, anterior à execução global; seus resultados são identificados como piloto e também é apresentada uma análise de sensibilidade excluindo essa questão (n=129). A relevância operacional permanece definida pelo capítulo de origem da pergunta, e não por uma avaliação independente da utilidade de cada chunk.

## Resultados — Recuperação com P5

| Condição | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 |
|:--|--:|--:|--:|--:|--:|
| **P0 — Original** | **79,23%** | **90,00%** | **93,08%** | **95,38%** | **0,8507** |
| P1 — Lowercase | 79,23% | 90,00% | 93,08% | 95,38% | 0,8507 |
| P2 — Stopwords | 70,77% | 80,77% | 83,08% | 89,23% | 0,7657 |
| P3 — Lematização | 73,85% | 89,23% | 90,77% | 93,85% | 0,8152 |
| P4 — Stemming | 60,77% | 73,08% | 80,77% | 85,38% | 0,6909 |
| **P5 — LLM + auditoria/fallback** | **78,46%** | **88,46%** | **91,54%** | **94,62%** | **0,8412** |

*Nota para a tabela: P1–P4 transformam consultas e corpus e utilizam seus próprios índices controlados; P5 reformula apenas consultas e reutiliza o índice P0. Portanto, as linhas são comparáveis em métricas, mas representam intervenções distintas.*

A estratégia P5 não apresentou ganho agregado sobre P0: o Hit@5 diminuiu de 93,08% para 91,54% (−1,54 ponto percentual), o Hit@10 de 95,38% para 94,62% (−0,77 ponto percentual) e o MRR@10 de 0,8507 para 0,8412 (Δ=−0,0095). Entre as 130 perguntas, seis apresentaram alteração do primeiro *rank* relevante: duas melhoras (Q63 e Q121) e quatro pioras (Q74, Q75, Q101 e Q125). A Q101 perdeu seu acerto no Top-10, ao passo que nenhuma falha anterior foi recuperada. Na Q11, usada como piloto, o capítulo-alvo 17 continuou ausente do Top-10 nas duas condições.

No subconjunto das 75 reformulações efetivas, 73 apresentaram mudanças na lista ordenada dos dez primeiros chunks, embora os conjuntos Top-10 compartilhassem, em média, 8,43 chunks. O MRR@10 nesse subconjunto caiu de 0,8435 (P0) para 0,8270 (P5), sugerindo que a reescrita modificou os rankings sem gerar benefícios sistemáticos de relocalização do capítulo-alvo. Excluída a Q11, o MRR@10 foi 0,8573 em P0 e 0,8477 em P5, preservando a direção descritiva do resultado. Como análises exploratórias, o teste exato de McNemar para Hit@10 resultou em p=1,000 e um teste exato de inversão de sinais pareados para MRR@10 em p=0,1875. Não se observou evidência estatística suficiente de diferença global; isso não prova equivalência.

## Discussão, limitações e considerações éticas

Os resultados complementam a análise de P0–P4: a modificação da superfície linguística de uma consulta, mesmo por um LLM com instruções de preservação semântica e contexto geral do domínio, pode alterar a vizinhança vetorial e a ordenação dos chunks sem aumentar a recuperação do capítulo de origem. A política conservadora de auditoria evitou utilizar reformulações com mudanças indevidas de significado, mas fez com que 55/130 consultas permanecessem idênticas à baseline, atenuando diferenças globais. Por isso, os resultados nas 75 reformulações efetivas são apresentados separadamente e de modo descritivo.

A auditoria de equivalência semântica depende de julgamento interpretativo, e a própria definição de relevância por capítulo não assegura que cada chunk desse capítulo contenha a resposta. Ademais, a P5 não foi avaliada quanto à qualidade das respostas geradas pelo RAG, limitando-se à recuperação. Em termos de transparência sobre modelos generativos, o Qwen2.5 3B foi empregado exclusivamente na reformulação textual das consultas, não como fonte de respostas ou avaliador de relevância. Os resultados descrevem esta configuração específica e não permitem generalizar a ausência de ganho para todo método de *query rewriting*. A questão 11 deve ser explicitada como piloto utilizado no ajuste anterior do prompt.

## Conclusão — Acréscimo conciso sugerido

Em uma análise complementar, a reformulação orientada por domínio com Qwen2.5 3B alterou os rankings, mas não superou o desempenho global da consulta original. Em conjunto, os resultados reforçam que transformações linguísticas, clássicas ou generativas, devem ser avaliadas empiricamente quando aplicadas à recuperação densa, em vez de presumidas como benéficas.

## Registro de transparência e reproducibilidade

- Protocolo: `P5-domain-aware-spa-v3-fallback-auditado-v1`.
- Modelo: `qwen2.5:3b` via Ollama; prompt `domain-aware-spa-v3`; temperatura 0; semente 42.
- Conjunto: 130 perguntas; 75 reformulações aceitas; 12 sem alteração; 43 fallback.
- Índice reutilizado: P0, 6.900 chunks, ChromaDB `langchain`.
- Artefatos: `scripts/run_p5_query_rewriting.py`, `tests/test_p5_query_rewriting.py`, `results/p5/full_130_v3_fallback/{summary.csv,paired_metrics.csv,rankings.csv,manifest.json}`.
- Para o artigo, citar o repositório e acrescentar as referências bibliográficas apropriadas a Qwen2.5, Ollama, MPNet e SPA segundo a bibliografia já usada. Não inventar entradas bibliográficas.
- Limite da disciplina INF 791: artigo científico de no máximo 10 páginas; selecionar apenas a tabela consolidada e um parágrafo de casos para não deslocar a análise principal.
