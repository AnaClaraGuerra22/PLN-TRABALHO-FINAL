# P5 — Inserção compacta no artigo (INF 791)

> Texto sugerido. Ajustar nomes e numeração das subseções ao manuscrito; acrescentar referências ao modelo e ao corpus usando a bibliografia do próprio artigo. O título/escopo principal do projeto P0–P4 não precisa ser alterado.

## Metodologia complementar

Adicionalmente às variantes clássicas P0–P4, investigou-se uma condição exploratória de reformulação de consultas por LLM (P5). O modelo Qwen2.5 3B, executado localmente no Ollama (temperatura 0; semente 42), recebeu um prompt fixo com contexto científico geral do *Science Panel for the Amazon* (SPA), instruído a preservar conceitos técnicos, restrições e significado. O prompt não recebeu respostas de referência, chunks ou capítulos-alvo. As 130 perguntas do SPAmazon-QA passaram por auditoria de equivalência semântica anterior à recuperação: 75 reformulações foram aceitas, 12 saídas permaneceram idênticas e 43 foram substituídas pela pergunta original (*fallback*: 28 rejeitadas e 15 pendentes). Diferentemente de P1–P4, P5 modificou apenas a consulta, reutilizando o índice ChromaDB P0, seus 6.900 chunks, o encoder `all-mpnet-base-v2` e o Top-10. O ranking P0 reexecutado coincidiu com o registro congelado.

## Resultados e discussão

| Variante | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 |
|---|---:|---:|---:|---:|---:|
| P0 — Original | 79,23% | 90,00% | 93,08% | 95,38% | 0,8507 |
| P1 — Lowercase | 79,23% | 90,00% | 93,08% | 95,38% | 0,8507 |
| P2 — Stopwords | 70,77% | 80,77% | 83,08% | 89,23% | 0,7657 |
| P3 — Lematização | 73,85% | 89,23% | 90,77% | 93,85% | 0,8152 |
| P4 — Stemming | 60,77% | 73,08% | 80,77% | 85,38% | 0,6909 |
| P5 — LLM + fallback | 78,46% | 88,46% | 91,54% | 94,62% | 0,8412 |

*P1–P4 transformam corpus e consulta; P5 transforma somente a consulta e preserva o índice P0.*

A P5 não superou a baseline: Hit@5 caiu 1,54 ponto percentual e MRR@10 diminuiu 0,0095. Nas 75 consultas efetivamente reformuladas, 73 apresentaram mudanças no ranking ordenado do Top-10, mas apenas seis alteraram a posição do primeiro capítulo relevante (duas melhorias e quatro pioras). A Q101 perdeu o acerto no Top-10, enquanto a Q125 apresentou a maior degradação de MRR@10 (−0,8000). Os testes pareados exploratórios não identificaram diferença global significativa (McNemar exato para Hit@10: p=1,000; inversão de sinais para MRR@10: p=0,1875), sem que isso implique equivalência estatística. A exclusão da Q11, empregada no desenvolvimento do prompt, não mudou a direção dos resultados. O resultado sugere que mudanças linguísticas podem alterar a vizinhança vetorial sem ganho correspondente na relocalização do capítulo-fonte.

## Considerações éticas e limitações — frase sugerida

O LLM foi utilizado exclusivamente para reformular consultas, sem geração de respostas finais. A auditoria semântica e a política de fallback limitaram desvios de significado, mas 55 das 130 consultas permaneceram iguais à baseline, e a relevância foi operacionalizada por capítulo-alvo, não pela utilidade de cada chunk; portanto, a conclusão é restrita ao protocolo, modelo e corpus avaliados.
