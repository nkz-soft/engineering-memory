# Tasks: Rename to Engineering Memory

## Phase 1 - Setup
- [x] T001 Confirm approval, baseline and absence of conflicting PRs in specs/011-rename-engineering-memory/plan.md.

## Phase 2 - Foundation
- [x] T002 Review the completed requirements checklist and existing .gitignore / .dockerignore.

## Phase 3 - US1: Isolated configuration
Independent test: dedicated-prefix settings load while consumer settings are ignored.
- [x] T003 [US1] Add failing prefix-isolation cases in tests/unit/test_settings_namespace.py.
- [x] T004 [US1] Change src/engineering_memory/settings.py prefix, tests/unit/conftest.py isolation and configuration tests / .env.example.

## Phase 4 - US2: Consistent identity
Independent test: installed command, imports, version and image use Engineering Memory.
- [x] T005 [US2] Observe failing identity assertions in tests/unit/test_cli.py and tests/structure/test_packaging.py before implementation.
- [x] T006 [US2] Rename src package and imports; update pyproject.toml, uv.lock, observability, Dockerfile and .github/workflows/ci.yml.

## Phase 5 - US3: Discovery and guidance
Independent test: contextual identifier audit and repository URL verification.
- [x] T007 [US3] Update README.md, ARCHITECTURE.md ADR-008, CLAUDE.md, constitution, docs/, specs/, projects.example.toml and issue-template links.
- [x] T008 [US3] Rename GitHub repository and update origin; verify old URL redirects to the canonical repository.

## Final Phase - Verification and delivery
- [ ] T009 Run full tests, Ruff, wheel / clean-install CLI checks and Docker checks; record results in specs/011-rename-engineering-memory/verification.md.
- [ ] T010 Review final diff, fix findings and create PR using .github/pull_request_template.md; move issue to in-review.

## Dependencies and implementation strategy
T001 -> T002 -> T003 -> T004 -> T005 -> T006 -> T007 -> T009 -> T008 -> T010.
US1 is the first independently testable slice. US2 follows its tests; US3 follows the completed rename. Execute sequentially because identifier edits overlap files. Parallel review examples: configuration behavior versus documentation audit; container packaging versus domain-data invariant review. No implementation tests use private data.
