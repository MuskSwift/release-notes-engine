# Changelog

## Unreleased

- ENG-019: model `grok-4.7-build-fast` + `--effort xhigh`.

- ENG-018: grok CLI `--effort xhigh` (model `grok-4.7`).

## Unreleased

- ENG-017: default model `grok-4.7` (effort unchanged).

## 0.1.0 — 2026-10-01

- Initial public CLI release: turns change notes (plus an optional taboo list) into a five-heading Chinese changelog for end users, via xAI (`XAI_API_KEY`) or an authenticated grok CLI.
- Schema-fidelity: when materials cite third-party headings such as `## 问题陈述`, keep the original text; do not project this engine’s five H2 into those descriptions.
