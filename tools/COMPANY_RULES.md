# Company-Owned Publication Rules

The Python checker is shared implementation. Tenant identity and publication
policy are data, not Python constants or fallback defaults.

## Source and Binding

`data/game_redlines.json` is the private, tenant-owned source. It remains ignored
by Git and excluded from the built site. `tools/export_redline_rules.py` validates
and exports only public fields to `tools/redline_rules.json`. Do not hand-edit the
generated public file or upload the private source.

The site declares `company_key` in `_config.yml`. Every checker mode loads the
same version 2.0 rule file and checks its `company_key` against that declaration.
An explicit `--company` can supply the expected identity for an external caller;
the caller must obtain it from its trusted company configuration, not from the
untrusted article. A missing or mismatched identity fails with exit code 2.

`--games` is rejected. The legacy config/chrome scanner now uses `by_name` from
the same rule file instead of a separate game list.

## Tenant Policy

`engine_policy` contains these required, validated sections:

- `site_hosts` and `context_id_pattern`: internal-link and subject-ID matching.
- `chrome_scan`: configured claim patterns and literal exclusions.
- `official_citation`: citation-prefix grammar, non-exempt patterns, allowed
  content zones and the maximum per-page citation count. Each named exception
  must stay within this policy and match its bound page identity.
- `rendered_quality`: visible-placeholder and download-negation patterns,
  exact download hosts, local path prefixes and required-indexing path scopes.

Existing rule arrays, site identity and named handwritten-page requirements
remain in the same tenant rule file. A tenant with no named handwritten pages
or no jargon rules supplies an explicit empty list, not another tenant's defaults.
There must still be at least one executable content rule.

`export_policy.internal_markers` is private-only tenant data. Its patterns prevent
private references from being copied into public descriptions. The exporter
requires it, validates its structure, and never includes it in the public output.
Shared structural allowlists still reject unknown fields; policy data cannot add
arbitrary exporter fields or disable validation by omitting a section.

## Update Contract for Assistants

Update only the intended tenant's private rule source and, when necessary, its
site identity binding. Run the exporter, its `--check` mode, the acceptance tests,
the tenant-isolation tests and a full site build. Rule changes alone do not require
editing the checker. Changing a platform rule is not permission to suppress a
failing check, rewrite an approval, replay a publish action or copy another tenant's
configuration.

This is a file-backed company-rule interface, not a new Company Studio form.
It does not change human approval or publication authority.

## Verification

Run `python tools/redline_lint_accept.py` and
`python -m unittest discover -s tools -p 'test_company_rule_policy.py'`.
The latter exercises two independent company policies in one process and through
text, build, config-only and legacy site CLI entry points. It covers mismatched
identity, missing/corrupt settings, company-owned citation scopes and limits,
exact-host URL matching, private export markers and absence of tenant identity
literals in shared implementation.
