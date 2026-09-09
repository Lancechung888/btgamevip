"""Validate tenant-owned policy data without any tenant defaults."""

import re
from urllib.parse import urlsplit


def exact_keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'{label} must contain exactly {sorted(keys)}')
    return value


def strings(value, label, nonempty=False):
    if (not isinstance(value, list) or (nonempty and not value)
            or any(not isinstance(item, str) or not item.strip() for item in value)
            or len(value) != len(set(value))):
        raise ValueError(f'{label} must be a list of distinct nonempty strings')
    return value


def pattern(value, label, flags=0):
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise ValueError(f'{label} must be a nonempty regex of at most 4096 characters')
    compiled = re.compile(value, flags)
    if compiled.search(''):
        raise ValueError(f'{label} must not match empty input')
    return compiled


def hosts(values, label):
    for host in strings(values, label):
        parsed = urlsplit('https://' + host)
        if (parsed.hostname != host or parsed.netloc != host or parsed.path
                or parsed.query or parsed.fragment or not re.fullmatch(r'[a-z0-9.-]+', host)):
            raise ValueError(f'{label} must contain exact lowercase hostnames')
    return tuple(values)


def path_prefixes(values, label, absolute=False):
    for value in strings(values, label):
        if (value.startswith('/') != absolute or not value.endswith('/')
                or '\\' in value or any(c in value for c in '?#:')
                or any(part in ('.', '..') for part in value.split('/'))):
            raise ValueError(f'{label} must contain bounded directory prefixes')
    return tuple(values)


def marker_patterns(values):
    if not isinstance(values, list) or not values:
        raise ValueError('export_policy.internal_markers must be a nonempty list')
    result = []
    for item in values:
        exact_keys(item, {'pattern', 'label'}, 'internal marker')
        if not isinstance(item['label'], str) or not item['label'].strip():
            raise ValueError('internal marker label is required')
        result.append((pattern(item['pattern'], 'internal marker', re.I), item['label']))
    return result


def load_engine_policy(raw, expected_company):
    if (not isinstance(expected_company, str)
            or not re.fullmatch(r'[a-z0-9][a-z0-9-]*', expected_company)
            or raw.get('company_key') != expected_company):
        raise ValueError('company rule identity is missing or does not match the requested company')
    if raw.get('version') != '2.0':
        raise ValueError('company rule version must be 2.0; migrate legacy rules explicitly')
    policy = exact_keys(raw.get('engine_policy'), {
        'site_hosts', 'context_id_pattern', 'chrome_scan', 'official_citation', 'rendered_quality',
    }, 'engine_policy')
    chrome = exact_keys(policy['chrome_scan'], {'ignored_literals', 'patterns'}, 'chrome_scan')
    ignored = strings(chrome['ignored_literals'], 'chrome_scan.ignored_literals')
    if not isinstance(chrome['patterns'], list):
        raise ValueError('chrome_scan.patterns must be a list')
    chrome_patterns = []
    for item in chrome['patterns']:
        exact_keys(item, {'label', 'pattern'}, 'chrome pattern')
        if not isinstance(item['label'], str) or not item['label'].strip():
            raise ValueError('chrome pattern label is required')
        chrome_patterns.append((item['label'], pattern(item['pattern'], 'chrome pattern')))
    citation = exact_keys(policy['official_citation'], {
        'denied_pattern', 'prefix_pattern', 'allowed_zones', 'max_per_page',
    }, 'official_citation')
    zones = strings(citation['allowed_zones'], 'official_citation.allowed_zones')
    if not set(zones) <= {'body', 'heading', 'badge', 'alt', 'chrome'}:
        raise ValueError('official_citation.allowed_zones contains an unknown content zone')
    cap = citation['max_per_page']
    if not isinstance(cap, int) or isinstance(cap, bool) or cap < 1:
        raise ValueError('official_citation.max_per_page must be a positive integer')
    quality = exact_keys(policy['rendered_quality'], {
        'placeholder_pattern', 'download_negation_pattern', 'download_path_prefixes',
        'download_hosts', 'indexable_path_prefixes',
    }, 'rendered_quality')
    context = pattern(policy['context_id_pattern'], 'context_id_pattern')
    if context.groups != 1:
        raise ValueError('context_id_pattern must have exactly one capture group')
    return {
        'site_hosts': hosts(policy['site_hosts'], 'site_hosts'),
        'context_id_pattern': context,
        'chrome_ignored_literals': tuple(ignored),
        'chrome_patterns': tuple(chrome_patterns),
        'official_denied_pattern': pattern(citation['denied_pattern'], 'official denied pattern'),
        'official_prefix_pattern': pattern(citation['prefix_pattern'], 'official citation prefix', re.I),
        'official_allowed_zones': tuple(zones),
        'official_max_per_page': cap,
        'placeholder_pattern': pattern(quality['placeholder_pattern'], 'placeholder pattern', re.I),
        'download_negation_pattern': pattern(quality['download_negation_pattern'], 'download negation pattern', re.I),
        'download_path_prefixes': path_prefixes(quality['download_path_prefixes'], 'download_path_prefixes', True),
        'download_hosts': hosts(quality['download_hosts'], 'download_hosts'),
        'indexable_path_prefixes': path_prefixes(quality['indexable_path_prefixes'], 'indexable_path_prefixes'),
    }
