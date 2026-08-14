---
name: allwell-s2t-qa
description: Scan AllWell website drafts, rendered HTML, metadata, JSON-LD, and social copy for residual Simplified Chinese with OpenCC, then report each hit with a Taiwan Traditional Chinese suggestion and FIX or REVIEW severity. Use before publication, during content refreshes, after template changes, or whenever a zh-TW artifact may contain Simplified Chinese. The skill is advisory and never edits or publishes content.
---

# AllWell 簡轉繁 QA

Detect residual Simplified Chinese before public delivery. Report evidence only; never rewrite files automatically.

## Run

Use Python 3 and the bundled scanner:

```powershell
python scripts/scan_simplified.py path\to\draft.md --pretty
python scripts/scan_simplified.py _site --ext .html,.json --json
Get-Content draft.txt -Raw | python scripts/scan_simplified.py --stdin --pretty
```

The scanner requires an existing `opencc` Python package. If it is unavailable, return `setup_required` and exit 2. Do not install a package, request a credential, or change the target file as part of a scan.

## Interpret results

- `FIX`: OpenCC identifies a Simplified Chinese form with an unambiguous Traditional Chinese replacement. Correct it before publication.
- `REVIEW`: The character can be valid in both writing systems or depends on context. Read the full phrase and decide manually.
- Exit 0: no `FIX` hits. `REVIEW` findings may remain and must be resolved by a human.
- Exit 1: at least one `FIX` hit, or at least one finding when `--fail-on any` is used.
- Exit 2: invalid input, missing dependency, unreadable file, or invalid bundled wordbank.

Treat every public location as in scope, including title, H1, visible copy, meta description, Open Graph/Twitter tags, feed text, JSON-LD, alt text, and social copy. Do not preserve Simplified Chinese merely as an SEO variant. The current company policy snapshot and the site redline gate remain authoritative if they are stricter.

## Workflow

1. Read the current company policy snapshot before scanning AllWell work.
2. Scan the source artifact and, when available, the rendered HTML.
3. Record file, line, column, source term, suggested Traditional Chinese term, severity, and context.
4. Give the findings to the content owner. Do not auto-apply replacements.
5. Re-scan the revised artifact. It may proceed only when `FIX=0` and every `REVIEW` item has a recorded disposition.

Use `references/wordbank.json` for deterministic phrase overrides and ambiguity handling. Keep the public wordbank limited to match terms and severity behavior; never add issue identifiers, private provenance, credentials, commercial figures, or internal paths.

See [references/verification-example.md](references/verification-example.md) for the bundled positive and negative validation.

## Boundaries

- Do not publish, deploy, submit indexing, follow short links, log in, or alter account state.
- Do not infer that a clean text scan proves full policy compliance; run the separate redline and content-value gates.
- Do not use OpenCC output as evidence that a proper noun, game title, or factual claim is correct.
- Do not scan images. Route image-text QA to the Art owner.
