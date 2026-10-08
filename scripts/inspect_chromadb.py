from pathlib import Path
from collections import Counter
import chromadb


BASE_DIR = Path(__file__).resolve().parents[1]
VECTOR_DB = BASE_DIR / "VECTOR_DB"


def main():

    print("=" * 70)
    print("INSPEÇÃO DO CHROMADB ORIGINAL DO AMAZONIAEXPERT.IA")
    print("=" * 70)

    if not VECTOR_DB.exists():
        raise FileNotFoundError(
            f"VECTOR_DB não encontrado em:\n{VECTOR_DB}"
        )

    print(f"\nBanco encontrado em:\n{VECTOR_DB}")

    client = chromadb.PersistentClient(
        path=str(VECTOR_DB)
    )


    collections = client.list_collections()

    print("\n" + "=" * 70)
    print("COLEÇÕES")
    print("=" * 70)

    print(f"Quantidade de coleções: {len(collections)}")

    if not collections:
        raise RuntimeError(
            "Nenhuma coleção foi encontrada no ChromaDB."
        )

    for collection_info in collections:

        if isinstance(collection_info, str):
            collection_name = collection_info
        else:
            collection_name = collection_info.name

        print("\n" + "-" * 70)
        print(f"COLEÇÃO: {collection_name}")
        print("-" * 70)

        collection = client.get_collection(
            name=collection_name
        )

        total = collection.count()

        print(f"\nTotal de chunks: {total}")



        sample = collection.get(
            limit=5,
            include=["documents", "metadatas"]
        )

        print("\nAMOSTRA DE 5 CHUNKS")

        for i, chunk_id in enumerate(sample["ids"]):

            document = sample["documents"][i]
            metadata = sample["metadatas"][i]

            print("\n" + "." * 60)

            print(f"ID:")
            print(chunk_id)

            print("\nMETADADOS:")
            print(metadata)

            print("\nTEXTO:")
            print(document[:600] if document else "SEM TEXTO")



        dados = collection.get(
            include=["metadatas"]
        )

        metadatas = dados["metadatas"] or []

        campos = sorted(
            {
                chave
                for metadata in metadatas
                if metadata
                for chave in metadata.keys()
            }
        )

        print("\n" + "=" * 70)
        print("CAMPOS DE METADADOS")
        print("=" * 70)

        for campo in campos:
            print(f"- {campo}")


        capitulos = Counter()

        for metadata in metadatas:

            if not metadata:
                capitulos["SEM_METADATA"] += 1
                continue

            chapter = metadata.get(
                "chapter_number",
                "SEM_CHAPTER_NUMBER"
            )

            capitulos[str(chapter)] += 1

        print("\n" + "=" * 70)
        print("DISTRIBUIÇÃO DE chapter_number")
        print("=" * 70)

        for chapter, quantidade in sorted(
            capitulos.items(),
            key=lambda x: x[0]
        ):
            print(
                f"{chapter:<30} -> {quantidade} chunks"
            )

        print("\n" + "=" * 70)
        print("RESUMO")
        print("=" * 70)

        print(f"Coleção: {collection_name}")
        print(f"Chunks: {total}")
        print(f"Metadados: {len(metadatas)}")
        print(f"Valores distintos de chapter_number: {len(capitulos)}")


if __name__ == "__main__":
    main()