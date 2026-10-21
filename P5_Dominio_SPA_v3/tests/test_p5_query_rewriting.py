"""Testes sem API e sem banco: executar python -m unittest discover -s tests -v."""
import csv
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / 'src/chapters.py').exists():
    # Fallback para executar os testes também no pacote avulso (sem clonar GitHub).
    stub = types.ModuleType('src.chapters')
    stub.canonicalize_target = lambda t: 'chapter_17' if t == 'Capítulo 17' else 'chapter_01'
    stub.canonicalize_chunk = lambda m: 'chapter_17' if 'Cap_17_' in m['source'] else 'chapter_11'
    sys.modules['src'] = types.ModuleType('src')
    sys.modules['src.chapters'] = stub
spec = importlib.util.spec_from_file_location('run_p5_query_rewriting', ROOT / 'scripts/run_p5_query_rewriting.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class P5Tests(unittest.TestCase):
    def test_rewrite_number_and_negation_flags(self):
        self.assertEqual(mod.rewrite_flags('Name three activities since the 1970s.', 'List three activities since the 1970s.'), [])
        self.assertIn('NUMEROS_DIFERENTES', mod.rewrite_flags('Since the 1970s', 'Since 1980'))
        self.assertIn('NEGACOES_DIFERENTES', mod.rewrite_flags('What is not useful?', 'What is useful?'))

    def test_ollama_local_request_mock(self):
        """Verifica o payload sem abrir conexão de rede nem baixar modelo."""
        from io import BytesIO
        fake = BytesIO(json.dumps({'message': {'content': 'Which three activities expanded since the 1970s?'}}).encode('utf-8'))
        class Response:
            def __enter__(self): return fake
            def __exit__(self, *args): return False
        with patch.object(mod, 'urlopen', return_value=Response()) as mocked:
            text = mod.local_rewrite('Name three activities since the 1970s.', 'qwen2.5:3b')
            self.assertTrue(text.startswith('Which'))
            request = mocked.call_args.args[0]
            self.assertEqual(request.full_url, 'http://127.0.0.1:11434/api/chat')
            payload = json.loads(request.data.decode('utf-8'))
            self.assertEqual(payload['model'], 'qwen2.5:3b')
            self.assertEqual(payload['options']['temperature'], 0)
            self.assertTrue(payload['stream'] is False)
            self.assertEqual(payload['messages'][1]['content'], 'Name three activities since the 1970s.')

    def test_domain_aware_prompt_version(self):
        self.assertEqual(mod.PROMPT_VERSION, 'domain-aware-spa-v3')
        self.assertIn('Science Panel for the Amazon', mod.PROMPT)
        self.assertIn('terminology interpretation only', mod.PROMPT)
        self.assertIn('technical noun', mod.PROMPT)
        self.assertIn('KEEP THAT TERM UNCHANGED', mod.PROMPT)
        self.assertIn('Never answer the question', mod.PROMPT)
        self.assertIn('never add examples', mod.PROMPT)

    def test_domain_protocol_cache_guard(self):
        good = {
            'prompt_version': mod.PROMPT_VERSION,
            'prompt': mod.PROMPT,
            'options': mod.GENERATION_OPTIONS,
            'llm_provider': 'ollama_local',
        }
        self.assertTrue(mod.validate_cache_protocol(good))
        self.assertFalse(mod.validate_cache_protocol({**good, 'prompt_version': 'conservative-v2'}))
        self.assertFalse(mod.validate_cache_protocol({**good, 'llm_provider': 'openai_api'}))

    def test_metrics(self):
        self.assertEqual(mod.metric(['chapter_11'] * 10, 'chapter_17')['hit10'], 0)
        self.assertEqual(mod.metric(['chapter_17'] + ['chapter_11']*9, 'chapter_17')['mrr10'], 1)
        self.assertEqual(mod.metric(['chapter_11']*4 + ['chapter_17'] + ['chapter_11']*5, 'chapter_17')['hit5'], 1)

    def test_historical_p0_completeness(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'rank.csv'
            with p.open('w', encoding='utf-8-sig', newline='') as f:
                w = csv.DictWriter(f, fieldnames=['variant', 'id_questao', 'rank', 'chunk_id'])
                w.writeheader()
                for k in range(1, 11):
                    w.writerow({'variant':'P0','id_questao':11,'rank':k,'chunk_id':f'x{k}'})
            self.assertEqual(mod.historical_p0(p, [11])[(11, 10)], 'x10')
            with self.assertRaises(ValueError):
                mod.historical_p0(p, [11, 12])

    def test_cache_and_selection(self):
        with tempfile.TemporaryDirectory() as t:
            file = Path(t)/'para.jsonl'
            file.write_text(json.dumps({'id_questao':11,'paraphrase':'Which three activities?'})+'\n', encoding='utf-8')
            self.assertEqual(mod.cached(file)[11]['paraphrase'], 'Which three activities?')
        self.assertEqual(mod.select_ids('11',{11:{}}),[11])
        with self.assertRaises(ValueError):
            mod.select_ids('11,11',{11:{}})

if __name__ == '__main__':
    unittest.main()
