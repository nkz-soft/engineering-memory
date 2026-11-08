# Recall v1 live mission experiment

The 2026-11-08 run compared the canonical retain mission with a candidate that excludes operational lessons. The two Hindsight instances used separate database volumes, archives, and import state. Each imported all 14 synthetic conversations with zero skips or failures. Each report scores the same 35 questions across seven categories with the fixed project tag `project:recall-benchmark` and limit `10`.

| Category | Baseline | Candidate | Change (pp) |
| --- | ---: | ---: | ---: |
| Overall | 95.71% | 75.71% | -20.0000 |
| Architecture decisions | 100.00% | 100.00% | 0.0000 |
| Technology choices | 100.00% | 90.00% | -10.0000 |
| Debugging investigations | 100.00% | 50.00% | -50.0000 |
| Root causes | 100.00% | 90.00% | -10.0000 |
| Failed approaches | 80.00% | 70.00% | -10.0000 |
| Infrastructure | 90.00% | 90.00% | 0.0000 |
| Operational lessons | 100.00% | 40.00% | -60.0000 |

## Settings

- Both instances used Hindsight `1.2.0` at the repository image pin, with local embeddings and reranking. The bank was `engineering-global` in each instance. Bank configuration writes were enabled for provisioning. Automatic consolidation was disabled and the startup LLM probe was skipped on both engines. The successful retain operations exercised the extraction route. [Engine configuration](../../../deploy/hindsight/service.yaml)
- Both instances used the same LiteLLM `v1.108.0` proxy with OpenRouter model `openai/gpt-oss-20b`, recorded as `openai-gpt-oss-20b` in the profiles. The proxy used the OpenAI-compatible adapter and the operator's default OpenRouter routing. OpenRouter may select different providers or quantizations between requests, and a rerun may produce different extracted facts. [Model and provider details](https://openrouter.ai/openai/gpt-oss-20b) · [Routing settings](https://openrouter.ai/blog/insights/model-routing/)
- Provisioning read back both missions before import. The profiles hash the UTF-8 mission text applied by the provisioner. [Baseline mission](../../../src/engineering_memory/memory/hindsight/mission.txt) · [Candidate mission](candidate-mission.txt)

## Reproduce

Start two disposable instances with fresh volumes and the settings above. Enable `HINDSIGHT_API_ENABLE_BANK_CONFIG_API` and `HINDSIGHT_API_SKIP_LLM_VERIFICATION`, and set `HINDSIGHT_API_ENABLE_AUTO_CONSOLIDATION` to `false` for both. Configure the application with each run's engine, archive, and SQLite state, and set `ENGINEERING_MEMORY_PROJECT_RULES_PATH` to `evaluation/recall-v1/projects.toml`. Use the checked-in corpus and benchmark in both runs. [Validation guide](../../../specs/031-recall-evaluation/quickstart.md) · [Local Hindsight setup](../../../docs/development/local-hindsight.md)

Run provision with the canonical application for baseline. For the candidate, apply the same command in a disposable copy with its packaged `mission.txt` replaced by `candidate-mission.txt`. Run the canonical application for both imports and evaluations. Use a profile with the recorded engine and extractor identifiers and the digest of the mission applied to that run.

```text
uv run --locked engineering-memory provision --json
uv run --locked engineering-memory import --source chatgpt --export evaluation/recall-v1/conversations.json --json
uv run --locked engineering-memory evaluate recall --benchmark evaluation/recall-v1/benchmark.json --profile PROFILE --output REPORT
```

After both runs produce complete reports, compute the candidate-minus-baseline changes from the unrounded scores.

```text
uv run --locked engineering-memory evaluate compare --baseline BASELINE_REPORT --candidate CANDIDATE_REPORT --output COMPARISON_REPORT
```
