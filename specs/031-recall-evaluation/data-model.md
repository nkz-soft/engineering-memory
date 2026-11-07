# Data model — Recall evaluation

## Benchmark

A strict versioned JSON object with `schema_version` (1), `project_tag` (`project:recall-benchmark` for v1), `limit` (10 for v1), `corpus_sha256` (the exact sibling export bytes), `project_rules_sha256` (the exact sibling project rule bytes), and ordered `questions`. Derive the benchmark SHA-256 from the exact manifest bytes. Check both sibling files before recall.

Each question has an ASCII kebab-case `id`, a `category`, nonblank `query`, and one or more `topics`. Category keys are `architecture-decisions`, `technology-choices`, `debugging-investigations`, `root-causes`, `failed-approaches`, `infrastructure`, and `operational-lessons`. Require at least 30 questions, unique IDs and normalized queries, and at least one question in each category.

Each topic has a stable `id` unique within its question, a nonempty list of `aliases`, and a nonempty list of `document_ids`. IDs must resolve to the fixed synthetic export under the current ChatGPT source-ID scheme. Validate that every topic has at least one alias present in its declared supporting source text. Reject blank or tokenless aliases and duplicate normalized aliases within a topic.

## Scoring

Normalize evidence and aliases with Unicode NFKC and case folding. Tokenize into Unicode alphanumeric runs (underscore separates tokens), then match contiguous whole-token sequences. Match each topic at most once, using any alias in any of the first ten results whose `document_id` is listed for that topic. Count matched topics divided by total topics per question, then average the question ratios within each category and overall. Compute deltas from the unrounded means and round displayed scores and percentage-point deltas to four decimal places.

## Report

A completed report contains schema and scoring versions, the benchmark, corpus and rules digests, project tag and limit, and a run profile from a checked JSON file. The profile fields are `run_id`, `engine_version`, `extractor_id`, and `mission_sha256`. Use short public identifier values for the first three and lowercase hex for the mission hash. For the published pair, record the actual engine version and public extractor model identifier with the exact mission digest. The benchmark operator supplies and verifies the profile.

Each report contains one entry per question with ID, category, all expected topic IDs and the matched subset. Include the resulting category and overall fractions. Validate scores against the question outcomes on comparison. Check that the question IDs, categories, and expected topic IDs agree between reports. Do not serialize returned matches, source excerpts, or environment details. Comparison contains the two validated profiles, both summaries, and candidate minus baseline in percentage points.
