"""Company isolation and fail-closed configuration regression tests."""

import ast
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

import company_rule_policy as policy
import export_redline_rules as exporter
import redline_lint_site as lint


HERE = Path(__file__).resolve().parent
ALLWELL = json.loads((HERE / 'redline_rules.json').read_text(encoding='utf-8'))


def other_company():
    raw = copy.deepcopy(ALLWELL)
    raw['company_key'] = 'sample-bakery'
    for key in ('by_name', 'frozen', 'by_gid', 'wording', 'context_gates', 'jargon', 'official_names'):
        raw[key] = []
    raw['wording'] = [{'id': 'bakery-word', 'pattern': 'COBALT_ONLY', 'severity': 'error'}]
    raw['density'] = None
    raw['site_identity']['canonical_site_name'] = 'Sample Bakery'
    raw['handwritten_chrome']['pages'] = []
    raw['engine_policy'] = {
        'site_hosts': ['bakery.example'],
        'context_id_pattern': r'sku=(\d+)',
        'chrome_scan': {'ignored_literals': ['ALLOWED_COBALT_ONLY'], 'patterns': [
            {'label': 'Bakery claim', 'pattern': 'COBALT_ONLY'},
        ]},
        'official_citation': {'denied_pattern': 'PRIVILEGED', 'prefix_pattern': r'Bakery says\s*',
                              'allowed_zones': ['body', 'heading'], 'max_per_page': 2},
        'rendered_quality': {
            'placeholder_pattern': 'UNFINISHED_BAKERY',
            'download_negation_pattern': 'UNAVAILABLE_BAKERY',
            'download_path_prefixes': ['/catalog/'],
            'download_hosts': ['assets.bakery.example'],
            'indexable_path_prefixes': ['products/'],
        },
    }
    return raw


class CompanyPolicyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='company-policy-test-')
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def file(self, name, value):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value,
                          encoding='utf-8')
        return target

    def load(self, raw, company=None):
        return lint.load_rules(str(self.file('rules.json', raw)), company or raw['company_key'])

    def cli(self, raw, company, mode='text', text='Plain content'):
        rules = self.file('rules.json', raw)
        config = self.file('config.yml', f'company_key: "{company}"\ntitle: "{text}"\ndescription: "Plain"\n')
        args = [sys.executable, str(HERE / 'redline_lint_site.py'), '--rules', str(rules), '--config', str(config)]
        if mode == 'text':
            args += ['--text', str(self.file('input.txt', text))]
        elif mode == 'build':
            self.file('build/index.html', f'<html><body><p>{text}</p></body></html>')
            args += ['--build-root', str(self.root / 'build')]
        elif mode == 'config':
            args += ['--config-only']
        elif mode == 'site':
            self.file('build/index.html', '<html><title>Plain</title><body>Plain</body></html>')
            args += ['--site-root', str(self.root / 'build')]
        result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8',
                                env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        return result.returncode, result.stdout + result.stderr

    def test_each_cli_mode_rejects_another_company(self):
        for mode in ('text', 'build', 'config', 'site'):
            with self.subTest(mode=mode):
                code, output = self.cli(ALLWELL, 'sample-bakery', mode)
                self.assertEqual(code, 2, output)
                self.assertIn('company rule identity', output)

    def test_no_silent_company_default(self):
        for expected in (None, '', 'ALLWELL', 'other-tenant'):
            with self.subTest(expected=expected), self.assertRaises(ValueError):
                policy.load_engine_policy(ALLWELL, expected)

    def test_allwell_and_other_rules_are_independent_in_one_process(self):
        first = self.load(ALLWELL)
        second = self.load(other_company())
        text = '本服立即開玩，u2 返現、首儲禮包'
        self.assertTrue(lint.scan_text_doc(text, first)[0])
        self.assertEqual(lint.scan_text_doc(text, second)[0], [])
        self.assertTrue(lint.scan_text_doc('COBALT_ONLY', second)[0])
        self.assertEqual(lint.scan_text_doc('COBALT_ONLY', first)[0], [])
        self.assertTrue(lint.scan_text_doc(text, first)[0])

    def test_other_company_works_in_text_and_build_without_game_rules(self):
        for mode in ('text', 'build'):
            with self.subTest(mode=mode):
                code, output = self.cli(other_company(), 'sample-bakery', mode, '本服 u2 返現 首儲禮包')
                self.assertEqual(code, 0, output)
                code, output = self.cli(other_company(), 'sample-bakery', mode, 'COBALT_ONLY')
                self.assertEqual(code, 1, output)

    def test_legacy_config_and_site_use_selected_policy(self):
        for mode in ('config', 'site'):
            with self.subTest(mode=mode):
                code, output = self.cli(other_company(), 'sample-bakery', mode, '返現 首儲禮包')
                self.assertEqual(code, 0, output)
                code, output = self.cli(other_company(), 'sample-bakery', mode, 'COBALT_ONLY')
                self.assertEqual(code, 1, output)
        code, output = self.cli(ALLWELL, 'allwell-next', 'config', '返現')
        self.assertEqual(code, 1, output)

    def test_ignore_literals_are_tenant_owned(self):
        selected = self.load(other_company())['policy']
        self.assertEqual(lint.hits('ALLOWED_COBALT_ONLY', selected), [])
        self.assertTrue(lint.hits('COBALT_ONLY', selected))

    def test_site_links_use_exact_company_hosts(self):
        selected = self.load(other_company())['policy']
        self.assertEqual(lint.url_to_relpath('https://bakery.example/products/a/', '', selected), 'products/a/index.html')
        self.assertEqual(lint.url_to_relpath('//bakery.example/products/a/', '', selected), 'products/a/index.html')
        for url in ('https://btgamevip.com/products/a/', '//btgamevip.com/products/a/',
                    'https://bakery.example.evil.test/x/', 'https://bakery.example@evil.test/x/',
                    'https://evil.test/?next=bakery.example', 'https://bakery.example/%2e%2e/x/'):
            with self.subTest(url=url):
                self.assertIsNone(lint.url_to_relpath(url, '', selected))

    def test_download_routes_do_not_match_company_names_in_queries(self):
        selected = self.load(other_company())['policy']
        tail = '<div data-faq>UNAVAILABLE_BAKERY</div>'
        for href in ('/catalog/a', 'https://assets.bakery.example/a', '//assets.bakery.example/a'):
            self.assertTrue(lint.check_rendered_quality(f'<a href="{href}">Open</a>{tail}', selected))
        for href in ('/go/a', 'https://go.btgamevip.com/a', 'https://qd.u2game99.com/a',
                     'https://evil.test/?next=assets.bakery.example/a', 'https://assets.bakery.example.evil.test/a'):
            self.assertEqual(lint.check_rendered_quality(f'<a href="{href}">Open</a>{tail}', selected), [])

    def test_quality_patterns_and_index_scope_are_tenant_owned(self):
        selected = self.load(other_company())['policy']
        self.assertEqual(lint.check_rendered_quality('<p>unknown TBD null</p>', selected), [])
        self.assertTrue(lint.check_rendered_quality('<p>UNFINISHED_BAKERY</p>', selected))
        html = '<meta name="robots" content="noindex">'
        self.assertTrue(lint.check_game_robots(html, 'products/a/index.html', selected))
        self.assertEqual(lint.check_game_robots(html, 'games/a/index.html', selected), [])
        self.assertEqual(selected['context_id_pattern'].findall('gid=2367 sku=400'), ['400'])

    def test_citation_grammar_is_tenant_owned(self):
        raw = other_company()
        raw['jargon'] = [{'id': 'flower', 'pattern': 'FLOWER', 'severity': 'error'}]
        raw['official_names'] = [{'id': 'quote', 'slug': 'sample', 'exact': '「Blue FLOWER」',
                                  'allow_zones': ['body'], 'max_per_page': 1}]
        selected = self.load(raw)
        self.assertTrue(lint.official_spans('Bakery says 「Blue FLOWER」', 'body', 'sample.html', set(), selected, {}))
        self.assertEqual(lint.official_spans('u2 官方玩法名為「Blue FLOWER」', 'body', 'sample.html', set(), selected, {}), [])
        raw['engine_policy']['official_citation']['denied_pattern'] = 'FLOWER'
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.load(raw)

    def test_citation_scope_and_limit_are_tenant_owned(self):
        raw = other_company()
        raw['jargon'] = [{'id': 'flower', 'pattern': 'FLOWER', 'severity': 'error'}]
        raw['official_names'] = [{'id': 'quote', 'slug': 'sample', 'exact': '「Blue FLOWER」',
                                  'allow_zones': ['heading'], 'max_per_page': 2}]
        selected = self.load(raw)
        state = {}
        for expected in (True, True, False):
            spans = lint.official_spans('Bakery says 「Blue FLOWER」', 'heading', 'sample.html', set(), selected, state)
            self.assertEqual(bool(spans), expected)
        self.assertEqual(lint.official_spans('Bakery says 「Blue FLOWER」', 'body', 'sample.html', set(), selected, {}), [])
        raw['engine_policy']['official_citation']['max_per_page'] = 1
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.load(raw)

    def test_policy_missing_invalid_unknown_fields_fail_closed(self):
        cases = []
        for key in ('version', 'company_key', 'engine_policy'):
            item = copy.deepcopy(ALLWELL)
            del item[key]
            cases.append(item)
        item = copy.deepcopy(ALLWELL)
        item['version'] = '1.1'
        cases.append(item)
        for key in ALLWELL['engine_policy']:
            item = copy.deepcopy(ALLWELL)
            del item['engine_policy'][key]
            cases.append(item)
        item = copy.deepcopy(ALLWELL)
        item['engine_policy']['token'] = 'DO_NOT_EXPORT'
        cases.append(item)
        for regex in ('[', '', '.*', '(unclosed'):
            item = copy.deepcopy(ALLWELL)
            item['engine_policy']['rendered_quality']['placeholder_pattern'] = regex
            cases.append(item)
        for item in cases:
            with self.subTest(item=item.get('version')), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.load(item, 'allwell-next')

    def test_malformed_hosts_paths_and_context_pattern_rejected(self):
        for key, value in [('site_hosts', ['https://example.test']), ('site_hosts', ['EXAMPLE.test']),
                           ('context_id_pattern', 'sku=([0-9]+)(extra)')]:
            raw = other_company()
            raw['engine_policy'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                policy.load_engine_policy(raw, 'sample-bakery')
        for value in ('../', '/wrong-root/', 'products', 'products/../'):
            raw = other_company()
            raw['engine_policy']['rendered_quality']['indexable_path_prefixes'] = [value]
            with self.subTest(value=value), self.assertRaises(ValueError):
                policy.load_engine_policy(raw, 'sample-bakery')

    def test_exporter_uses_private_tenant_markers_without_publishing_them(self):
        raw = other_company()
        raw.pop('_generated_by', None)
        raw['export_policy'] = {'internal_markers': [{'pattern': 'PRIVATE_BAKERY_[0-9]+', 'label': 'Private reference'}]}
        # Public descriptions must enter through explicitly public input fields.
        raw['site_identity'] = {'canonical_site_name': 'Sample Bakery', 'severity': 'error', 'public_message': 'Name mismatch'}
        raw['handwritten_chrome'].pop('message', None)
        raw['handwritten_chrome'].pop('suggestion', None)
        raw.pop('density', None)
        with redirect_stdout(io.StringIO()):
            result = exporter.build_public(raw, 'sample-bakery')
        self.assertNotIn('export_policy', result)
        exporter.scan_output('ALL-123 u2', raw['export_policy'])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            exporter.scan_output('PRIVATE_BAKERY_42', raw['export_policy'])
        with self.assertRaises(ValueError):
            exporter.build_public(raw, 'allwell-next')
        raw['engine_policy']['private_notes'] = 'SECRET'
        with self.assertRaises(ValueError):
            exporter.build_public(raw, 'sample-bakery')

    def test_exporter_missing_markers_cannot_silently_disable_guard(self):
        for value in ({}, {'internal_markers': []}, {'internal_markers': [{'pattern': 'x', 'label': 'x', 'secret': 'x'}]}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                exporter.scan_output('anything', value)

    def test_shared_implementation_contains_no_company_identity_literals(self):
        for name in ('redline_lint_site.py', 'company_rule_policy.py', 'export_redline_rules.py'):
            tree = ast.parse((HERE / name).read_text(encoding='utf-8'))
            literals = '\n'.join(n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str))
            for token in ('btgamevip.com', 'u2game99.com', 'allwell-next', 'sample-bakery', 'u2\\s', 'ALL-\\d'):
                with self.subTest(file=name, token=token):
                    self.assertNotIn(token, literals)


if __name__ == '__main__':
    unittest.main()
