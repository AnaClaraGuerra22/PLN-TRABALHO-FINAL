# P5 v3 — Reformulação de consultas com contexto de domínio SPA (Ollama local)

## Objetivo e restrições

Extensão **exploratória** da comparação original P0–P4. O P5 altera **apenas o texto das consultas** usando uma paráfrase produzida localmente por `qwen2.5:3b`, mantendo o índice controlado P0 (ChromaDB), o corpus com 6.900 chunks, os IDs, o encoder `sentence-transformers/all-mpnet-base-v2` e o Top-10. Não usa API paga, não reindexa e não gera respostas científicas.

## O que mudou na v3?

O prompt (constante `PROMPT` em `scripts/run_p5_query_rewriting.py`) oferece **contexto amplo e fixo do domínio**: perguntas derivadas dos relatórios do Science Panel for the Amazon (SPA), abrangendo biomas, ecossistemas, recursos naturais, uso da terra, clima, economia, sociedades, políticas públicas e desenvolvimento sustentável. Informa que esse contexto serve **somente para desambiguar termos**, sem trazer novos fatos à consulta. O prompt exige preservar conceitos técnicos, quantificadores, tipo de resposta, período, negações, escopo e especificidade. Quando não existir sinônimo estritamente equivalente, manda **manter o termo técnico original e apenas mudar a sintaxe**.

O gerador vê **somente a pergunta original**. Não recebe `resposta_esperada`, `capitulo_alvo`, chunks, fontes ou resultados P0. A versão, o prompt e as opções do Ollama ficam registrados em cada item gerado. O script agora bloqueia cache de prompts/provedores diferentes na revisão ou avaliação e registra hash do prompt no manifesto de execução.

## Protocolo de piloto, histórico e congelamento

- **v1**: Q11 rejeitada por substituir `commodity` por `commerce`; registrada em `results/p5/pilot_prompt_v1/`.
- **v2**: Q11 rejeitada por substituir `commodity activities` por `commercial endeavors`; **arquive antes de instalar a v3** como descrito abaixo.
- **v3**: teste **sem recuperar o Top-10 antes de revisar**. Gere uma saída por pergunta. Não ajuste o prompt para perseguir melhoria no resultado de Q11. Depois de revisão metodológica, congele modelo+prompt+parâmetros para o conjunto de 130 perguntas. Caso a nova saída também altere o sentido, documente a rejeição e defina uma política uniforme para as questões inválidas, evitando busca seletiva por uma saída favorável.

A revisão manual deve ocorrer **antes de consultar o ChromaDB**, sem olhar os rankings para decidir aprovação. A ausência de flags automáticas **não** prova equivalência semântica. O piloto e seus ajustes devem ser apresentados como elaboração exploratória da metodologia, e não resultado confirmatório.

## Passo 1 — Salvar a saída v2 antes de substituir os arquivos

Na raiz `TRAB FINAL` (PowerShell):

```powershell
$arquivoV2 = '.\results\p5\paraphrases.jsonl'
$revisaoV2 = '.\results\p5\review.csv'
$destino = '.\results\p5\pilot_prompt_v2'
if ((Test-Path $destino) -and (Get-ChildItem $destino -Force | Select-Object -First 1)) { throw 'Arquivo v2 já preservado. Confira manualmente para evitar sobrescrita.' }
New-Item -ItemType Directory -Force $destino | Out-Null
Move-Item -LiteralPath $arquivoV2 -Destination (Join-Path $destino 'paraphrases.jsonl') -ErrorAction Stop
Move-Item -LiteralPath $revisaoV2 -Destination (Join-Path $destino 'review.csv') -ErrorAction Stop
```

## Passo 2 — Atualizar os três arquivos do código

Baixe e extraia `P5_Dominio_SPA_v3.zip` **dentro de TRAB FINAL**. O conteúdo será criado sob uma pasta com o mesmo nome. Procure recursivamente, caso o descompactador tenha criado uma pasta extra:

```powershell
$pacote = '.\P5_Dominio_SPA_v3'
$arquivos = @{
  'run_p5_query_rewriting.py' = '.\scripts\'
  'test_p5_query_rewriting.py' = '.\tests\'
  'P5_QUERY_REWRITING.md' = '.\docs\'
}
foreach ($nome in $arquivos.Keys) {
  $matches = @(Get-ChildItem -Path $pacote -Recurse -File -Filter $nome)
  if ($matches.Count -ne 1) { throw "Esperado 1 arquivo $nome; encontrados $($matches.Count)" }
  Copy-Item -LiteralPath $matches[0].FullName -Destination $arquivos[$nome] -Force
  Write-Host "Atualizado: $nome"
}
```

## Passo 3 — Testar e gerar Q11

No terminal com `.venv` ativado e Ollama instalado:

```powershell
python -m unittest discover -s tests -p "test_p5_query_rewriting.py" -v
# Resultado esperado: Ran 7 tests ... OK
python .\scripts\run_p5_query_rewriting.py generate --ids 11 --llm qwen2.5:3b
python .\scripts\run_p5_query_rewriting.py review
```

Abra `results/p5/review.csv`. Não aprove automaticamente: examine equivalência. Para decidir junto no ChatGPT, envie o CSV ou copie apenas `original` e `paraphrase`. **Ainda não execute `evaluate`**.

## Próxima etapa, somente se a paráfrase tiver sido aprovada

Altere `approved` de `0` para `1` no CSV mantendo as outras colunas inalteradas. Avalie a questão piloto no índice **P0 controlado original**:

```powershell
python .\scripts\run_p5_query_rewriting.py evaluate --ids 11 --output results/p5/pilot11_v3
```

O banco local padrão é `C:\PLN_EXPERIMENTOS\VECTOR_DB_CONTROLLED\P0`, coleção `langchain`. Antes do P5, a rotina exige reproduzir o ranking P0 armazenado em `results/raw/controlled_rankings.csv` exatamente, chunk por chunk. Se falhar, interrompe a avaliação.

Saídas: `rankings.csv`, `paired_metrics.csv`, `summary.csv`, `manifest.json`. Comparação P0 x P5 por Hit@1/3/5/10 e MRR@10; resultado pode piorar ou melhorar.

## Experimento final das 130 perguntas (não executar ainda)

Somente após congelar o prompt, a tag/digest do modelo (`ollama show qwen2.5:3b`) e a política de revisão/rejeição:

```powershell
python .\scripts\run_p5_query_rewriting.py generate --ids all --llm qwen2.5:3b
python .\scripts\run_p5_query_rewriting.py review
# Revisar antes de avaliar. Escolher e documentar de antemão como tratar saídas inválidas.
python .\scripts\run_p5_query_rewriting.py evaluate --ids all --output results/p5/full130_v3
```

**Atenção:** O comando `evaluate --ids all` exige aprovação das 130 paráfrases; não execute se alguma continuar inválida. Nesse caso, é necessário estabelecer e implementar uma política pré-definida para casos rejeitados antes da comparação global.

Versão do Ollama local e recursos disponíveis não garantem bit-a-bit o mesmo texto apesar de `temperature=0` e `seed=42`; use cache e registre tags, versão e digest do modelo.
