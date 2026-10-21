# Análise da P5 — Query rewriting orientado pelo domínio SPA

**Experimento:** P5-domain-aware-spa-v3-fallback-auditado-v1  
**Data do registro:** 21/10/2026 (UTC conforme manifesto)  
**Fonte dos cálculos:** `summary.csv`, `paired_metrics(1).csv`, `rankings(1).csv`, `auditoria_detalhada.csv`, `manifest.json`.  
**Estágio:** recuperação finalizada; discussão e relato acadêmico pendentes de revisão editorial.

## 1. Protocolo efetivamente avaliado

- **Conjunto:** 130 consultas do SPAmazon-QA.
- **Modelo reformulador:** Qwen2.5 3B, via Ollama local, `temperature=0`, `seed=42`, `num_predict=256`, `num_ctx=2048`.
- **Prompt:** `domain-aware-spa-v3`, contexto geral dos relatórios Science Panel for the Amazon, sem resposta esperada ou capítulo-alvo.
- **Auditoria pré-recuperação:** 75 paráfrases equivalentes aprovadas; 12 saídas idênticas ao original; 28 saídas rejeitadas; 15 com revisão pendente.
- **Política:** consultas equivalentes → paráfrase; casos idênticos, rejeitados e pendentes → pergunta original (fallback), com todas as questões mantidas.
- **Indexação:** mesma coleção `langchain` P0 do ChromaDB controlado, com 6.900 chunks; **sem reindexação**.
- **Encoder:** `sentence-transformers/all-mpnet-base-v2` (768 dimensões); Top-10.
- **Paridade com a P0 histórica:** `true`, conforme `manifest.json`.
- **Q11:** usada durante o desenvolvimento do prompt; apresentada separadamente de 129 questões não utilizadas na escolha do prompt.

## 2. Métricas globais: P0 vs P5 (130 questões)

| Métrica | P0 | P5 | Diferença P5−P0 |
|---|---:|---:|---:|
| Hit@1 | 79,23% (103/130) | 78,46% (102/130) | −0,77 p.p. |
| Hit@3 | 90,00% (117/130) | 88,46% (115/130) | −1,54 p.p. |
| Hit@5 | 93,08% (121/130) | 91,54% (119/130) | −1,54 p.p. |
| Hit@10 | 95,38% (124/130) | 94,62% (123/130) | −0,77 p.p. |
| MRR@10 | 0,850714 | 0,841218 | −0,009496 |

**Conclusão descritiva:** não houve melhora agregada em nenhuma das cinco métricas. A estratégia P5 perdeu uma consulta com Hit@10, sem recuperar novos casos previamente malsucedidos.

## 3. Sensibilidade ao desenvolvimento do prompt (129 questões sem Q11)

| Métrica | P0 | P5 | Diferença |
|---|---:|---:|---:|
| Hit@1 | 79,84% | 79,07% | −0,78 p.p. |
| Hit@3 | 90,70% | 89,15% | −1,55 p.p. |
| Hit@5 | 93,80% | 92,25% | −1,55 p.p. |
| Hit@10 | 96,12% | 95,35% | −0,78 p.p. |
| MRR@10 | 0,857309 | 0,847739 | −0,009570 |

A exclusão da Q11 não muda a direção do efeito. Esse conjunto de 129 consultas deve ser denominado **não utilizado no desenvolvimento do prompt**. O termo “confirmatório” somente é apropriado com declaração clara do congelamento prévio do protocolo e da natureza exploratória do estudo.

## 4. Análise restrita às 75 reformulações efetivas

| Métrica | P0 nas 75 | P5 nas 75 | Diferença |
|---|---:|---:|---:|
| Hit@1 | 78,67% | 77,33% | −1,33 p.p. |
| Hit@3 | 88,00% | 85,33% | −2,67 p.p. |
| Hit@5 | 93,33% | 90,67% | −2,67 p.p. |
| Hit@10 | 94,67% | 93,33% | −1,33 p.p. |
| MRR@10 | 0,843460 | 0,827000 | −0,016460 |

As 55 consultas sem reformulação aplicada (43 fallback + 12 idênticas) são idênticas à P0 por definição, e não fornecem evidência de efeito da reescrita. O recorte das 75 questões é **descritivo**, condicionado a uma auditoria de equivalência; não é uma amostra aleatória independente.

## 5. Casos com alterações de MRR@10

| Questão | Primeiro rank relevante P0 | Primeiro rank relevante P5 | ΔRR@10 | Leitura |
|---|---:|---:|---:|---|
| Q63 | 7 | 6 | +0,023810 | pequena melhora |
| Q74 | 3 | 8 | −0,208333 | degradação no Top-5 |
| Q75 | 3 | 4 | −0,083333 | degradação no Top-3 |
| Q101 | 4 | fora do Top-10 | −0,250000 | único caso que perdeu Hit@10 |
| Q121 | 4 | 3 | +0,083333 | melhora no Top-3 |
| Q125 | 1 | 5 | −0,800000 | maior degradação de MRR |

**Importante:** a comparação de relevância se baseia no capítulo-alvo, não na avaliação manual de cada chunk quanto à resposta. Posições referem-se ao primeiro chunk do capítulo-alvo.

## 6. Estabilidade dos rankings

- Nas **75** questões com paráfrase efetiva, **73** tiveram pelo menos alguma alteração na lista ordenada dos dez chunks.
- A média de interseção entre os conjuntos Top-10 de P0 e P5 foi **8,43 chunks em dez** nessas 75 questões (84,27% de sobreposição simples).
- Em **15/75** a composição dos dez chunks permaneceu idêntica, embora pudesse haver reordenação; em apenas **2/75** a ordem inteira permaneceu idêntica.
- O chunk em primeiro lugar mudou em **14/75** questões.
- Portanto, mudanças de ranking podem ocorrer mesmo quando a posição do primeiro capítulo relevante e as métricas Hit@k permanecem iguais.

## 7. Testes pareados exploratórios

- **McNemar exato bicaudal** sobre indicadores binários por questão:
  - Hit@1: 0 ganhos vs. 1 perda, `p=1,000`.
  - Hit@3: 1 ganho vs. 3 perdas, `p=0,625`.
  - Hit@5: 0 ganhos vs. 2 perdas, `p=0,500`.
  - Hit@10: 0 ganhos vs. 1 perda, `p=1,000`.
- **MRR@10:** teste exato de inversão de sinais pareados dos seis deltas não nulos, bicaudal, `p=0,1875`.
- **IC percentil bootstrap pareado de 95%** para a diferença média MRR@10, 20.000 reamostragens, semente 20261021: aproximadamente **[−0,0251; +0,0002]**. O intervalo inclui zero.

Esses testes não indicam diferença estatisticamente significativa nos níveis convencionais. A quantidade de pares discordantes é pequena; não afirmar equivalência estatística ou ausência de qualquer efeito apenas porque `p>0,05`.

## 8. Limitações e interpretação

1. **Efeito da política de fallback:** 42,31% das consultas permaneceram idênticas à P0, diminuindo a magnitude da diferença global; relatar também o recorte das 75 reformulações.
2. **Auditoria semântica:** classificações são julgamento interpretativo e podem merecer segunda revisão independente ou adjudicação; preservar o CSV e os motivos.
3. **Q11:** participou do ajuste do prompt e não deve ser tratada como validação inteiramente independente.
4. **Proxy de relevância:** Hit@k e MRR@10 dependem da correspondência ao capítulo-alvo, não de uma anotação manual da utilidade do chunk para responder.
5. **Especificidade do tratamento:** o resultado descreve Qwen2.5 3B + prompt v3 + auditoria/fallback + all-mpnet-base-v2 + corpus SPA; não demonstra que outras técnicas de query rewriting sempre falhem.
6. **Foco em recuperação:** os resultados não avaliam respostas de um gerador RAG sob P5.
7. **Diferença para P1–P4:** P5 altera consultas e preserva o índice P0; P1–P4 modificaram representações em consulta/corpus. Comparações são informativas, mas as intervenções têm mecanismos diferentes.

## 9. Redação acadêmica sugerida

> Como análise complementar, avaliou-se uma estratégia de reformulação de consultas orientada por domínio, implementada com Qwen2.5 3B executado localmente. As 130 perguntas do SPAmazon-QA foram processadas com prompt fixo e auditadas quanto à preservação semântica, resultando em 75 reformulações aceitas, 12 saídas inalteradas e 43 casos tratados por retorno à consulta original. A recuperação foi realizada sobre o mesmo índice e encoder empregados em P0. Em relação à baseline, a estratégia apresentou Hit@10 de 94,62% versus 95,38% e MRR@10 de 0,8412 versus 0,8507, sem melhoria global. Entre as 75 reformulações efetivas, 73 modificaram a ordenação dos dez primeiros chunks, porém apenas seis alteraram a posição do primeiro capítulo relevante, com duas melhorias e quatro degradações. Os resultados indicam que a reformulação pode afetar a composição dos rankings sem produzir ganhos correspondentes nas métricas de recuperação por capítulo, nas condições investigadas.

**Próxima decisão recomendada:** manter o experimento P5 congelado; incorporar como análise complementar e destacar Q101/Q125, juntamente com um exemplo de melhora (Q121 ou Q63), sem refazer as paráfrases ou selecionar casos a posteriori para otimizar os resultados.
