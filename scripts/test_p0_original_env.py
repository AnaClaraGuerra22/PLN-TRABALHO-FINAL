import chromadb

DB_PATH = r"C:\PLN_EXPERIMENTOS\VECTOR_DB_P0_FRESH"

print("=" * 70)
print("TESTE DA BASELINE P0 COM O AMBIENTE ORIGINAL DO TCC")
print("=" * 70)

print(f"\nBanco:\n{DB_PATH}")

client = chromadb.PersistentClient(path=DB_PATH)

colecoes = client.list_collections()

print("\nColeções encontradas:")
for c in colecoes:
    nome = c if isinstance(c, str) else c.name
    print("-", nome)

collection = client.get_collection(name="langchain")

print("\nTentando contar os chunks...")

total = collection.count()

print(f"\nTotal de chunks: {total}")

print("\nObtendo 3 exemplos...")

dados = collection.get(
    limit=3,
    include=["documents", "metadatas"]
)

for i, chunk_id in enumerate(dados["ids"]):

    print("\n" + "-" * 60)

    print("ID:")
    print(chunk_id)

    print("\nMETADATA:")
    print(dados["metadatas"][i])

    print("\nDOCUMENTO:")
    documento = dados["documents"][i]

    if documento:
        print(documento[:800])
    else:
        print("SEM DOCUMENTO")

print("\nTESTE CONCLUÍDO.")