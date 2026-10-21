"""P5: paráfrase de consulta comparada à P0 em índice CONTROLADO e congelado.

Execução na raiz do PLN-TRABALHO-FINAL. Nenhuma mudança em P0-P4.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.chapters import canonicalize_chunk, canonicalize_target

QUESTIONS = ROOT / 'data/processed/p0_questions.jsonl'
HISTORY = ROOT / 'results/raw/controlled_rankings.csv'
DB = Path(r'C:\PLN_EXPERIMENTOS\VECTOR_DB_CONTROLLED\P0')
OUT = ROOT / 'results/p5'
MODEL = 'sentence-transformers/all-mpnet-base-v2'
COLLECTION = 'langchain'
OLLAMA_URL = 'http://127.0.0.1:11434/api/chat'  # exclusivamente local
GENERATION_OPTIONS = {'temperature': 0, 'seed': 42, 'num_predict': 256, 'num_ctx': 2048}
K = (1, 3, 5, 10)
# v3: piloto de contexto geral do domínio SPA; congelar antes do experimento de 130 questões.
PROMPT_VERSION = 'domain-aware-spa-v3'
PROMPT = (
    'You are a scientific question-paraphrasing assistant. '
    'DOMAIN BACKGROUND (terminology interpretation only): The questions come from a '
    'scientific question-answering dataset derived from Science Panel for the Amazon '
    '(SPA) reports. They cover the Amazon region, ecosystems, forests, natural '
    'resources, land use, environmental processes, climate, economic activities, '
    'societies, public policy, and sustainable development. '
    'This background is NOT evidence, and you must not add any of it to the question. '
    'TASK: Produce exactly ONE standalone paraphrase in English of the user question. '
    'Keep EXACTLY the same information need, meaning, answer type, scientific '
    'categories, specificity, geographic and temporal scope, and level of certainty. '
    'Preserve quantities, the distinction between examples versus an exhaustive set, '
    'entities, dates, negation, comparisons, direction of time, and technical noun '
    'phrases. Do not replace a scientific or economic technical concept by a '
    'broader, narrower, or merely related concept. When a term cannot safely be '
    'replaced with a fully equivalent one, KEEP THAT TERM UNCHANGED and vary only '
    'grammar or surrounding everyday wording. '
    'Never answer the question; never add examples, inferred facts, hints, or '
    'interpretations. Never add any reference to SPA, reports, chapter titles, '
    'documents, or the Amazon unless those already appear in the original question. '
    'Return only the rewritten English question with a question mark, without '
    'preface, quotes, explanation, or alternative versions.'
)


def validate_cache_protocol(item):
    """Verifica que nenhuma paráfrase antiga foi misturada ao novo protocolo."""
    return (
        item.get('prompt_version') == PROMPT_VERSION
        and item.get('prompt') == PROMPT
        and item.get('options') == GENERATION_OPTIONS
        and item.get('llm_provider') == 'ollama_local'
    )


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def questions(path=QUESTIONS):
    rows = {}
    with open(path, encoding='utf-8-sig') as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            qid = int(item['id_questao'])
            if qid in rows or not item['query'].strip():
                raise ValueError(f'Pergunta duplicada/vazia: {qid}')
            canonicalize_target(item['capitulo_alvo'])
            rows[qid] = item
    if len(rows) != 130:
        raise ValueError(f'Esperadas 130 perguntas; encontradas {len(rows)}')
    return rows


def select_ids(spec, rows):
    ids = sorted(rows) if spec.lower() == 'all' else [int(x) for x in spec.split(',')]
    if len(ids) != len(set(ids)) or any(i not in rows for i in ids):
        raise ValueError('IDs inválidos ou duplicados')
    return ids


def cached(path):
    rows = {}
    if path.exists():
        with open(path, encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                qid = int(item['id_questao'])
                if qid in rows:
                    raise ValueError(f'Paráfrase duplicada: {qid}')
                rows[qid] = item
    return rows


def rewrite_flags(original, rewritten):
    import re
    flags = []
    if not rewritten.strip() or original.casefold().strip() == rewritten.casefold().strip():
        flags.append('VAZIA_OU_IDENTICA')
    nums = lambda text: Counter(re.findall(r'\b\d+(?:[.,]\d+)?s?\b', text.lower()))
    if nums(original) != nums(rewritten):
        flags.append('NUMEROS_DIFERENTES')
    negs = lambda text: Counter(re.findall(r'\b(?:no|not|never|without|nor|neither)\b', text.lower()))
    if negs(original) != negs(rewritten):
        flags.append('NEGACOES_DIFERENTES')
    return flags


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def local_rewrite(question, model, *, endpoint=OLLAMA_URL):
    """Gera uma paráfrase via Ollama local, sem API externa nem custos de uso.

    O servidor deve estar em 127.0.0.1; o endpoint padrão não sai do computador.
    """
    payload = {
        'model': model,
        'stream': False,
        'messages': [
            {'role': 'system', 'content': PROMPT},
            {'role': 'user', 'content': question},
        ],
        'options': GENERATION_OPTIONS,
    }
    request = Request(
        endpoint,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urlopen(request, timeout=300) as response:
            data = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(
            f'Ollama local respondeu HTTP {exc.code}: {detail}. '
            f'Confirme a instalação do modelo: ollama pull {model}'
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(
            'Ollama não está respondendo em 127.0.0.1:11434. '
            'Instale/inicie o Ollama e execute: '
            f'ollama pull {model}'
        ) from exc
    content = (data.get('message') or {}).get('content')
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(f'Ollama retornou resposta vazia/inválida: {data!r}')
    return content.strip().strip('"“”')


def generate(args):
    q = questions()
    ids = select_ids(args.ids, q)
    cache = cached(args.paraphrases)
    fingerprint = sha256(QUESTIONS)
    args.paraphrases.parent.mkdir(parents=True, exist_ok=True)
    print(f'Geração 100% local usando Ollama: {args.llm}')
    with args.paraphrases.open('a', encoding='utf-8') as f:
        for qid in ids:
            original = q[qid]['query']
            if qid in cache:
                previous = cache[qid]
                if (previous['original'] != original or previous['qa_hash'] != fingerprint
                        or previous['llm'] != args.llm or previous['prompt'] != PROMPT
                        or not validate_cache_protocol(previous)):
                    raise ValueError(f'Cache incompatível: questão {qid}')
                print(f'Q{qid}: já gerada, preservada sem seleção posterior')
                continue
            paraphrase = local_rewrite(original, args.llm)
            if not paraphrase:
                raise ValueError(f'LLM retornou texto vazio para Q{qid}')
            item = {'id_questao': qid, 'original': original, 'paraphrase': paraphrase,
                    'llm': args.llm, 'llm_provider': 'ollama_local', 'prompt_version': PROMPT_VERSION, 'options': GENERATION_OPTIONS,
                    'temperature': 0, 'prompt': PROMPT,
                    'qa_hash': fingerprint, 'utc': datetime.now(timezone.utc).isoformat(),
                    'flags': rewrite_flags(original, paraphrase)}
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            f.flush()
            print(f'Q{qid}: paráfrase salva; revisar antes de recuperar')


def review(args):
    q = questions()
    cache = cached(args.paraphrases)
    old = {}
    if args.review.exists():
        with args.review.open(encoding='utf-8-sig', newline='') as f:
            old = {int(r['id_questao']): r for r in csv.DictReader(f)}
    rows = []
    for qid, item in sorted(cache.items()):
        if (qid not in q or item['qa_hash'] != sha256(QUESTIONS)
                or item['original'] != q[qid]['query'] or not validate_cache_protocol(item)):
            raise ValueError(f'Paráfrase não pertence à base atual: {qid}')
        before = old.get(qid, {})
        matched = before.get('paraphrase') == item['paraphrase']
        rows.append({'id_questao': qid, 'original': item['original'], 'paraphrase': item['paraphrase'],
                     'flags': '|'.join(rewrite_flags(item['original'], item['paraphrase'])),
                     'approved': before.get('approved', '0') if matched else '0',
                     'notes': before.get('notes', '') if matched else ''})
    write_csv(args.review, rows, ['id_questao', 'original', 'paraphrase', 'flags', 'approved', 'notes'])
    print(f'{len(rows)} paráfrases para revisão em {args.review}; edite approved para 1 após validar o sentido.')


def metric(chapters, target):
    first = next((i for i, c in enumerate(chapters, 1) if c == target), None)
    d = {'first_rank': first if first else '', 'mrr10': 1 / first if first else 0.0}
    d.update({f'hit{k}': int(first is not None and first <= k) for k in K})
    return d


def historical_p0(path, ids):
    if not path.is_file():
        raise FileNotFoundError(f'Ranking P0 histórico não localizado: {path}')
    expected = {}
    with path.open(encoding='utf-8-sig', newline='') as f:
        sniff = f.readline()
        f.seek(0)
        reader = csv.DictReader(f, delimiter=';' if sniff.count(';') > sniff.count(',') else ',')
        for r in reader:
            qid = int(r['id_questao'])
            if r['variant'] == 'P0' and qid in ids:
                key = (qid, int(r['rank']))
                if key in expected:
                    raise ValueError(f'Ranking P0 duplicado: {key}')
                expected[key] = r['chunk_id']
    for qid in ids:
        if any((qid, rank) not in expected for rank in range(1, 11)):
            raise ValueError(f'Ranking histórico P0 incompleto: {qid}')
    return expected


def evaluate(args):
    import chromadb
    from langchain_huggingface import HuggingFaceEmbeddings
    q = questions()
    ids = select_ids(args.ids, q)
    cache = cached(args.paraphrases)
    with args.review.open(encoding='utf-8-sig', newline='') as f:
        approvals = {int(r['id_questao']): r for r in csv.DictReader(f)}
    for qid in ids:
        item = cache.get(qid, {})
        a = approvals.get(qid, {})
        if (not item or item.get('qa_hash') != sha256(QUESTIONS)
                or item.get('original') != q[qid]['query'] or not validate_cache_protocol(item)):
            raise ValueError(f'Cache inválido/ausente para Q{qid}')
        if (a.get('approved', '').strip() != '1' or a.get('original') != item['original']
                or a.get('paraphrase') != item['paraphrase']):
            raise ValueError(f'Q{qid}: paráfrase não aprovada ou modificada após revisão')
    if len({cache[qid]['llm'] for qid in ids}) != 1:
        raise ValueError('Modelos LLM diferentes no mesmo experimento P5')
    if not args.db.is_dir():
        raise FileNotFoundError(f'Índice Chroma P0 local não encontrado: {args.db}')
    client = chromadb.PersistentClient(path=str(args.db))
    col = client.get_collection(name=COLLECTION, embedding_function=None)
    if col.count() != 6900:
        raise ValueError(f'P0 inválido: {col.count()} chunks (esperado 6900)')
    encoder = HuggingFaceEmbeddings(model_name=MODEL)
    if len(encoder.embed_query('Amazon')) != 768:
        raise ValueError('Embedding não tem 768 dimensões')
    expected = historical_p0(args.history, ids)
    rank_rows, pair_rows = [], []
    for qid in ids:
        target = canonicalize_target(q[qid]['capitulo_alvo'])
        measures = {}
        for variant, query in (('P0', q[qid]['query']), ('P5', cache[qid]['paraphrase'])):
            result = col.query(query_embeddings=[encoder.embed_query(query)], n_results=10,
                               include=['metadatas', 'distances'])
            if len(result['ids'][0]) != 10:
                raise ValueError(f'Q{qid} {variant}: retorno incompleto')
            chapter_ids = []
            for rank, (cid, metadata, distance) in enumerate(zip(result['ids'][0], result['metadatas'][0], result['distances'][0]), 1):
                if variant == 'P0' and expected[(qid, rank)] != cid:
                    raise RuntimeError(f'Q{qid} posição {rank}: P0 não reproduziu ranking congelado; interrompido')
                chapter = canonicalize_chunk(metadata)  # source distingue Cross Chapter e capítulo regular
                chapter_ids.append(chapter)
                rank_rows.append({'id_questao': qid, 'variant': variant, 'rank': rank, 'chunk_id': cid,
                                  'chapter_id': chapter, 'target': target, 'hit': int(chapter == target),
                                  'distance': float(distance), 'source': metadata.get('source', '')})
            measures[variant] = metric(chapter_ids, target)
        row = {'id_questao': qid, 'tipo': q[qid]['tipo'], 'dificuldade': q[qid]['dificuldade'], 'target': target}
        for var in ('P0', 'P5'):
            row.update({f'{var}_{k}': v for k, v in measures[var].items()})
        for k in K:
            row[f'delta_hit{k}'] = measures['P5'][f'hit{k}'] - measures['P0'][f'hit{k}']
        row['delta_mrr10'] = measures['P5']['mrr10'] - measures['P0']['mrr10']
        pair_rows.append(row)
        print(f"Q{qid}: P0 Hit@10={measures['P0']['hit10']}; P5 Hit@10={measures['P5']['hit10']}; ΔMRR={row['delta_mrr10']:+.4f}")
    dest = args.output
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f'Destino já preenchido: {dest}; escolha nova pasta, não sobrescreva resultados')
    dest.mkdir(parents=True, exist_ok=True)
    write_csv(dest / 'rankings.csv', rank_rows, list(rank_rows[0]))
    write_csv(dest / 'paired_metrics.csv', pair_rows, list(pair_rows[0]))
    summary = []
    for var in ('P0', 'P5'):
        subset = [r for r in pair_rows]
        row = {'variant': var, 'n': len(subset)}
        for k in K:
            row[f'hit{k}'] = sum(r[f'{var}_hit{k}'] for r in subset) / len(subset)
        row['mrr10'] = sum(r[f'{var}_mrr10'] for r in subset) / len(subset)
        summary.append(row)
    write_csv(dest / 'summary.csv', summary, list(summary[0]))
    manifest = {'protocol': 'P5-query-rewriting-paired-v1', 'ids': ids,
                'questions_sha256': sha256(QUESTIONS), 'paraphrases_sha256': sha256(args.paraphrases),
                'review_sha256': sha256(args.review), 'history_sha256': sha256(args.history),
                'database_path': str(args.db), 'collection': COLLECTION, 'n_chunks': col.count(),
                'prompt_version': PROMPT_VERSION, 'prompt_sha256': hashlib.sha256(PROMPT.encode('utf-8')).hexdigest(),
                'ollama_model_tag': cache[ids[0]]['llm'], 'ollama_options': GENERATION_OPTIONS,
                'encoder': MODEL, 'top_k': 10, 'historical_p0_parity': True,
                'timestamp_utc': datetime.now(timezone.utc).isoformat()}
    (dest / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Resultados salvos em', dest)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    s = p.add_subparsers(dest='command', required=True)
    for command, handler in [('generate', generate), ('review', review), ('evaluate', evaluate)]:
        sub = s.add_parser(command)
        sub.set_defaults(func=handler)
        sub.add_argument('--paraphrases', type=Path, default=OUT / 'paraphrases.jsonl')
        if command in ('generate', 'evaluate'):
            sub.add_argument('--ids', default='11')
        if command == 'generate':
            sub.add_argument('--llm', default='qwen2.5:3b',
                             help='Tag de um modelo previamente baixado no Ollama local')
        if command in ('review', 'evaluate'):
            sub.add_argument('--review', type=Path, default=OUT / 'review.csv')
        if command == 'evaluate':
            sub.add_argument('--db', type=Path, default=DB)
            sub.add_argument('--history', type=Path, default=HISTORY)
            sub.add_argument('--output', type=Path, default=OUT / 'pilot11')
    args = p.parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
