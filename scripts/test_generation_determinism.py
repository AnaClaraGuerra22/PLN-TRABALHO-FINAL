import json
import hashlib
from pathlib import Path

import pandas as pd
from langchain_community.llms import LlamaCpp
from langchain_core.prompts import PromptTemplate


BASE_DIR = Path(__file__).resolve().parents[1]

CAMINHO_MODELO = Path(
    r"C:\TCCII\MODELO\ClimateChat.i1-Q4_K_M.gguf"
)

P0_CORPUS = (
    BASE_DIR
    / "data"
    / "reference"
    / "p0_chunks.jsonl"
)

CASES_FILE = (
    BASE_DIR
    / "data"
    / "reference"
    / "downstream_critical_cases.jsonl"
)

RETRIEVAL_FILE = (
    BASE_DIR
    / "results"
    / "cases"
    / "downstream_retrieval_top5.csv"
)


PROMPT_RAG = PromptTemplate(
    template="""<s>[INST] You are a highly qualified scientific assistant specializing in the sustainable development of the Amazon. 
Your task is to answer the question primarily based on the provided context from the Science Panel for the Amazon (SPA) reports. 

Strict Rules you MUST follow:
1. Direct Answer: Answer exactly what is asked. You may use your internal scientific expertise to complement the information, but do not contradict the context.
2. Conciseness: Keep your answer between 1 to 3 short paragraphs. 
3. No Filler Words: DO NOT use conversational fillers like "Based on the provided text...", "According to the context...", or "In conclusion...". State the facts directly.

Context extracted from SPA reports:
{context}

Question: {question}
Scientific Answer: [/INST]""",
    input_variables=["context", "question"],
)


def sha256_text(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def load_p0():
    lookup = {}

    with P0_CORPUS.open(
        "r",
        encoding="utf-8"
    ) as f:
        for line in f:
            rec = json.loads(line)

            lookup[str(rec["chunk_id"])] = {
                "document": rec["document"],
                "metadata": rec["metadata"],
            }

    return lookup


def load_question(qid):
    with CASES_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:
        for line in f:
            rec = json.loads(line)

            if int(rec["id_questao"]) == qid:
                return rec["pergunta"]

    raise RuntimeError(
        f"Questão {qid} não encontrada."
    )


def build_context(df, variant, qid, p0_lookup):
    sub = df[
        (df["variant"] == variant)
        & (df["id_questao"] == qid)
    ].sort_values("rank")

    if len(sub) != 5:
        raise RuntimeError(
            f"{variant}/Q{qid}: "
            f"esperados 5 chunks; encontrados {len(sub)}."
        )

    textos = []
    ids = []

    for _, row in sub.iterrows():
        rank = int(row["rank"])
        chunk_id = str(row["chunk_id"])

        ids.append(chunk_id)

        textos.append(
            f"[Trecho {rank}]: "
            f"{p0_lookup[chunk_id]['document']}"
        )

    return "\n\n".join(textos), ids


print("=" * 72)
print("TESTE DE DETERMINISMO — Q9 P0 × P1")
print("=" * 72)

p0_lookup = load_p0()
pergunta = load_question(9)

retrieval = pd.read_csv(
    RETRIEVAL_FILE,
    encoding="utf-8-sig"
)

retrieval["id_questao"] = (
    retrieval["id_questao"].astype(int)
)

retrieval["chunk_id"] = (
    retrieval["chunk_id"].astype(str)
)

contexto_p0, ids_p0 = build_context(
    retrieval,
    "P0",
    9,
    p0_lookup,
)

contexto_p1, ids_p1 = build_context(
    retrieval,
    "P1",
    9,
    p0_lookup,
)

prompt_p0 = PROMPT_RAG.format(
    context=contexto_p0,
    question=pergunta,
)

prompt_p1 = PROMPT_RAG.format(
    context=contexto_p1,
    question=pergunta,
)


print("\nChunk IDs P0:")
print(ids_p0)

print("\nChunk IDs P1:")
print(ids_p1)

print(
    "\nChunks idênticos:",
    ids_p0 == ids_p1,
)

print(
    "Contextos idênticos:",
    contexto_p0 == contexto_p1,
)

print(
    "Prompts idênticos:",
    prompt_p0 == prompt_p1,
)

print(
    "\nSHA prompt P0:",
    sha256_text(prompt_p0),
)

print(
    "SHA prompt P1:",
    sha256_text(prompt_p1),
)


if prompt_p0 != prompt_p1:
    raise RuntimeError(
        "P0 e P1 não possuem prompts idênticos. "
        "Não executar teste de geração."
    )


print("\n" + "=" * 72)
print("CARREGANDO CLIMATECHAT")
print("=" * 72)

llm = LlamaCpp(
    model_path=str(CAMINHO_MODELO),
    temperature=0.1,
    max_tokens=2048,
    n_ctx=8192,
    n_gpu_layers=0,
    repeat_penalty=1.15,
    top_p=0.9,
    seed=42,
    stop=[
        "</s>",
        "Question:",
        "[INST]",
    ],
    verbose=False,
)


print("\nGerando Q9 / P0...")

resposta_p0 = (
    llm.invoke(prompt_p0)
    .strip()
)

print("Gerando Q9 / P1...")

resposta_p1 = (
    llm.invoke(prompt_p1)
    .strip()
)


hash_p0 = sha256_text(resposta_p0)
hash_p1 = sha256_text(resposta_p1)


print("\n" + "=" * 72)
print("RESULTADO")
print("=" * 72)

print(
    "Respostas idênticas:",
    resposta_p0 == resposta_p1,
)

print(
    "SHA resposta P0:",
    hash_p0,
)

print(
    "SHA resposta P1:",
    hash_p1,
)


print("\n--- RESPOSTA P0 ---")
print(resposta_p0)

print("\n--- RESPOSTA P1 ---")
print(resposta_p1)


if resposta_p0 == resposta_p1:
    print("\n" + "=" * 72)
    print("TESTE PASSOU")
    print("=" * 72)
    print(
        "Prompt idêntico + seed fixa "
        "produziram resposta idêntica."
    )
else:
    print("\n" + "=" * 72)
    print("ATENÇÃO: TESTE NÃO PASSOU")
    print("=" * 72)
    print(
        "Prompts idênticos produziram "
        "respostas diferentes."
    )