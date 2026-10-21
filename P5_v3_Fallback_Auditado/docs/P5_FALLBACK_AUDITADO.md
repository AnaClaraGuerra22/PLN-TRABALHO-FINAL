# P5 v3: reformulação de consultas orientada ao domínio SPA, com auditoria e fallback

## O que este pacote faz

**Não altera P0–P4, o prompt v3, os embeddings, o corpus ou o banco ChromaDB.** A extensão modifica apenas a política de avaliação: uma saída de reformulação semanticamente rejeitada ou pendente de revisão não substitui a pergunta original. A escolha é feita **antes** da recuperação, independentemente do ranking e das métricas.

O script verifica que cada entrada de `review_auditada.csv` é exatamente a mesma que a paráfrase registrada em `results/p5/paraphrases.jsonl`, que todas as decisões têm correspondência na auditoria e que P0 reproduz os IDs congelados nas dez posições.

## Classes da auditoria e política fixa

| Status | Quantidade | `approved` | Consulta P5 utilizada |
|---|---:|---:|---|
| `EQUIVALENTE` | 75 | 1 | paráfrase produzida pelo Qwen |
| `SEM_ALTERACAO` | 12 | 1 | pergunta original, porque o Qwen não a modificou |
| `REJEITAR` | 28 | 0 | pergunta original (`fallback`) |
| `REVISAR` | 15 | 0 | pergunta original (`fallback` conservador, não é aprovação) |
| **Total** | **130** | **87 aprovadas** | 130 perguntas recuperadas |

Esses números se referem à auditoria *assistida* existente, que deve ser revisada por uma pessoa se for utilizada como anotação semântica científica no artigo. A Q11 foi usada para elaborar o prompt: analisar também os 129 casos fora do desenvolvimento.

## Instalação no Windows

Extraia o ZIP em `TRAB FINAL`, deixando a pasta `P5_v3_Fallback_Auditado` disponível dentro da raiz. Com a `.venv` ativada, copie os arquivos:

```powershell
Copy-Item '.\P5_v3_Fallback_Auditado\scripts\run_p5_query_rewriting.py' '.\scripts\' -Force
Copy-Item '.\P5_v3_Fallback_Auditado\tests\test_p5_query_rewriting.py' '.\tests\' -Force
Copy-Item '.\P5_v3_Fallback_Auditado\files\review_auditada.csv' '.\results\p5\review_auditada.csv'
Copy-Item '.\P5_v3_Fallback_Auditado\files\auditoria_detalhada.csv' '.\results\p5\auditoria_detalhada.csv'
```

A cópia de `review_auditada.csv` usa um nome NOVO. Não substitua `results/p5/review.csv`, nem `results/p5/paraphrases.jsonl`. Os exemplos pressupõem que o ZIP foi extraído com exatamente uma pasta superior; se houver uma pasta adicional, ajuste o caminho.

### Testes

```powershell
python -m unittest discover -s tests -p 'test_p5_query_rewriting.py' -v
```

### Execução completa (somente após revisar a política de auditoria)

```powershell
python .\scripts\run_p5_query_rewriting.py evaluate --ids all --review .\results\p5\review_auditada.csv --audit-file .\results\p5\auditoria_detalhada.csv --fallback-rejected --output .\results\p5\full_130_v3_fallback
```

A pasta de destino deve estar vazia ou não existir. O programa recusa sobrescrever dados anteriores. **Não execute `generate` ou `review` para obter a planilha auditada:** a geração original já está congelada, e a função `review` sobrescreveria/reconstruiria o CSV a partir de um arquivo de revisão escolhido.

## Saídas

- `rankings.csv`: 2 rankings por pergunta (P0 e política P5, Top-10); colunas `audit_status`, `query_source`, `effective_paraphrase`.
- `paired_metrics.csv`: métricas pareadas P0/P5 e deltas por pergunta com motivo da seleção da consulta.
- `summary.csv`: resultados nas 130 questões; resultado confirmatório excluindo Q11 (129 questões); descrição secundária das questões efetivamente reformuladas.
- `manifest.json`: hashes dos dados, auditoria, modelo de embeddings, prompt e política experimental.

## Interpretação metodológica essencial

O resultado principal mede uma **política assistida de reformulação com revisão semântica e fallback**, não o uso puro do LLM em todas as 130 perguntas. No subconjunto de 43 perguntas com fallback, P0 e P5 devem retornar o mesmo ranking, por construção. Isso pode atenuar degradações e precisa ser explicitamente divulgado. A análise restrita às 75 reformulações equivalentes é **descritiva e sujeita à seleção**, não substituindo a comparação pareada global. O caso Q11 foi utilizado no desenvolvimento e deve ser separado na análise confirmatória.

A revisão das 15 questões `REVISAR` não é obrigatória antes desta avaliação conservadora: elas permanecem **não aprovadas** e utilizam a pergunta original. Qualquer mudança posterior nessa política exige documentar uma nova versão de avaliação e manter os resultados anteriores preservados. Não selecione paráfrases com base no ranking ou gabarito.
