"""Run an isolated, bounded, credential-free real-engine contract gate."""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = {
    "test_default_replace_preserves_stable_identity",
    "test_async_retry_does_not_extract_twice",
    "test_original_timestamps_drive_temporal_retrieval",
    "test_never_written_bank_read_is_404",
} | {
    f"test_tag_membership[{mode}-expected{i}]"
    for i, mode in enumerate(["any", "all", "any_strict", "all_strict", "exact"])
}


def verify_report(root):
    cases = list(root.iter("testcase"))
    names = [case.attrib["name"] for case in cases]
    if len(names) != len(REQUIRED) or set(names) != REQUIRED:
        raise ValueError("§6/9/10 incomplete live contract selection")
    if any(
        case.find(outcome) is not None
        for case in cases
        for outcome in ("skipped", "failure", "error")
    ):
        raise ValueError("§6/9/10 live contract did not pass without skips")


def main():
    project = "contract-" + uuid4().hex[:12]
    compose = [
        "docker",
        "compose",
        "-p",
        project,
        "-f",
        str(ROOT / "deploy/hindsight/compose.contract.yaml"),
    ]
    env = {**os.environ, "COMPOSE_PROJECT_NAME": project, "ENGINEERING_MEMORY_LIVE_CONTRACT": "1"}
    # Fixed loopback defaults may be overridden for concurrent local runs.
    env["ENGINEERING_MEMORY_LIVE_STORE_URL"] = "http://127.0.0.1:" + env.get(
        "CONTRACT_ENGINE_PORT", "8889"
    )
    env["CONTRACT_FIXTURE_URL"] = "http://127.0.0.1:" + env.get("CONTRACT_FIXTURE_PORT", "8890")
    try:
        subprocess.run(
            [*compose, "up", "-d", "--wait", "--wait-timeout", "600"],
            env=env,
            check=True,
            timeout=660,
        )
        with tempfile.TemporaryDirectory(prefix="live-contract-") as directory:
            report = Path(directory) / "results.xml"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/integration/test_live_hindsight_contract.py",
                    "-q",
                    "--tb=short",
                    f"--junitxml={report}",
                ],
                cwd=ROOT,
                env=env,
                check=True,
                timeout=420,
            )
            verify_report(ET.parse(report).getroot())
    finally:
        subprocess.run(
            [*compose, "down", "--volumes", "--remove-orphans"], env=env, check=True, timeout=90
        )


if __name__ == "__main__":
    main()
