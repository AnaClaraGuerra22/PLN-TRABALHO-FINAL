# P5 – Reformulação semântica de consultas com LLM local (Ollama)

**Sem API paga.** A P5 é uma análise exploratória de *query rewriting*: altera somente a pergunta. A configuração P0–P4, o corpus, o encoder (`sentence-transformers/all-mpnet-base-v2`) e o índice ChromaDB **P0 controlado** permanecem intactos.

## Dependências

- Windows e o `.venv` já usado no trabalho de PLN;
- **Ollama** instalado gratuitamente: https://ollama.com/download/windows;
- Modelo local `qwen2.5:3b`, baixado uma única vez (~2 GB; o tamanho real pode variar). Para máquinas com pouca RAM, pode-se usar `qwen2.5:1.5b`, mas escolha **antes** de coletar resultados e utilize **o mesmo modelo em todas as 130 perguntas**;
- Nenhuma chave, crédito nem assinatura de API necessários. O pacote Python `openai` previamente instalado pode permanecer no ambiente, mas **não é usado** pela P5.

## Instalar modelo local

No PowerShell (Ollama instalado e em execução):

```powershell
ollama pull qwen2.5:3b
ollama list
```

Se `ollama` não for reconhecido, feche e reabra o terminal após a instalação. Se a conexão local falhar, confira se o aplicativo Ollama está aberto; quando necessário, `ollama serve` em um terminal separado.

## Atualização do projeto

Copie `scripts/run_p5_query_rewriting.py`, `tests/test_p5_query_rewriting.py` e `docs/P5_QUERY_REWRITING.md` desta versão para as **mesmas pastas** do seu projeto. Substitua os dois arquivos P5 anteriores; não altere arquivos P0–P4.

## Revisão conservadora do prompt — piloto v2

Na primeira tentativa de Q11 (prompt v1), a paráfrase substituiu "commodity" por "commerce", alterando parcialmente o conceito. **Rejeitar** a saída; a ausência de flags automáticas não garante equivalência semântica. Não houve avaliação no ChromaDB dessa tentativa. O prompt foi reforçado de modo **geral, antes da recuperação**, para preservar terminologia técnica, categorias e nível de especificidade. A v2 será usada de forma uniforme nas 130 questões.

Antes de executar novamente a geração, **arquive o piloto v1** para rastreabilidade (na raiz do projeto, PowerShell):

```powershell
New-Item -ItemType Directory -Force .\results\p5\pilot_prompt_v1 | Out-Null
Move-Item .\results\p5\paraphrases.jsonl .\results\p5\pilot_prompt_v1\paraphrases.jsonl
Move-Item .\results\p5\review.csv .\results\p5\pilot_prompt_v1\review.csv
```

Guarde a saída v1 original, com `approved=0`, e inclua no registro experimental a justificativa da rejeição. Ao executar novamente, o script cria um novo cache independente. **Não altere manualmente as paráfrases no JSONL** e não escolha outputs com base no desempenho do ranking. Esta revisão de prompt é parte do piloto de engenharia, não um resultado comparativo P5.

## Piloto técnico: questão 11

Abra um terminal no diretório `TRAB FINAL` e ative seu `.venv`:

```powershell
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -p "test_p5_query_rewriting.py" -v
python .\scripts\run_p5_query_rewriting.py generate --ids 11 --llm qwen2.5:3b
python .\scripts\run_p5_query_rewriting.py review
```

Abra `results/p5/review.csv`, confira a pergunta parafraseada, e altere `approved` para `1` **somente se mantiver o significado**. Não deve acrescentar as respostas esperadas, ampliar ou estreitar escopo, nem alterar o período histórico, a negação ou o número de atividades solicitado. As flags automáticas são apenas um alerta: revisão humana é obrigatória **antes** da recuperação.

**Apenas após aprovação:**

```powershell
python .\scripts\run_p5_query_rewriting.py evaluate --ids 11 --output results/p5/pilot11
```

O índice utilizado é `C:\PLN_EXPERIMENTOS\VECTOR_DB_CONTROLLED\P0`, coleção `langchain` (6900 chunks); o caminho e a contagem são validados. O script reexecuta a consulta P0 com o mesmo `HuggingFaceEmbeddings.embed_query` usado no experimento controlado e compara, posição a posição, com `results/raw/controlled_rankings.csv`. Se houver divergência de ranking, interrompe a execução antes de produzir uma comparação inválida.

Outputs: `rankings.csv`, `paired_metrics.csv`, `summary.csv` e `manifest.json` em `results/p5/pilot11`.

## Experimento total, somente após piloto

```powershell
python .\scripts\run_p5_query_rewriting.py generate --ids all --llm qwen2.5:3b
python .\scripts\run_p5_query_rewriting.py review
# Revise e aprove, sem testar várias paráfrases para escolher a melhor.
python .\scripts\run_p5_query_rewriting.py evaluate --ids all --output results/p5/full130
```

Não execute `all` antes da decisão final de modelo, prompt e método de revisão. O cache mantém uma única saída por pergunta. Em caso de paráfrase semanticamente inválida, documente a ocorrência em vez de selecionar um texto otimizado pelos resultados.

## Nota metodológica

- `P5` não é operação simétrica aplicada aos chunks; é reformulação apenas das consultas.
- Preservar registro da tag exata e digest do modelo local: `ollama list` e `ollama show qwen2.5:3b`.
- Temperatura 0 e seed 42 são solicitados ao Ollama, mas não garantem identidade perfeita em todo hardware/software. Registrar versão e modelo.
- O LLM vê apenas a pergunta, **nunca** `resposta_esperada`, `capitulo_alvo`, chunks ou rankings.
- Resultados negativos são tão informativos quanto ganhos; relatar natureza pós-hoc/exploratória e taxas de aprovação das paráfrases.
- Não confundir Chapter Hit@k operacional com relevância real no nível de chunk ou qualidade de resposta gerada.
