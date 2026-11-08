# Research Decisions

## R1 — Use the consumer path for both operations

ARCHITECTURE.md §16.1 names `reflect` and `search_memory` on the existing MCP surface. Issue #32's `evaluation/recall-v1/` and `evaluation/runner.py` provide an established stdio client and a separate synthetic baseline. A live run for #31 uses the accumulated bank without writing to it. Record whether #30 project models are available and keep their state fixed during the run.

## R2 — Confirm the engine wire contract on the pinned service

The [upstream reflect reference](https://hindsight.vectorize.io/developer/api/reflect) describes a text answer, strict tag scoping, and optional supporting evidence. Treat it as a design reference. The pinned version in `deploy/hindsight/service.yaml` and its running contract determine the exact request and response fields, evidence metadata, and optional usage counters. Verify these before mapping them. Prefer archive-backed references from concrete memories. A model mention by itself supplies no conversation provenance.

## R3 — Review coverage and synthesis separately

Freeze private expectations before seeing outputs. Count a point as covered by recall only when a returned item and its sanitized source support it. Count a point in reflect only when the answer states it and the validated evidence supports it. Review relationships, chronology and unsupported claims separately. Use the lookup controls to show the cost of synthesis on simple questions.
