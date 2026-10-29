"""Local Compose lifecycle. Run from a checkout, outside the product's domain boundaries.

Exit 77 means live E2E was skipped, never passed. Output is deliberately limited to
stage names: subprocess output can contain credentials or conversation payloads.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values

HERE = Path(__file__).resolve().parent
DEV_PROJECT = "engineering-memory-product-dev"


class DeploymentError(RuntimeError):
    """A safe diagnostic, containing no operator values or subprocess output."""


@dataclass(frozen=True)
class Limits:
    startup: float = 600
    total: float = 1800
    cleanup: float = 60

    def __post_init__(self):
        if any(not math.isfinite(v) or v <= 0 for v in (self.startup, self.total, self.cleanup)):
            raise DeploymentError("Deadlines must be positive finite seconds")


@dataclass(frozen=True)
class RunIdentity:
    project: str

    @classmethod
    def create(cls):
        return cls("em-e2e-" + uuid.uuid4().hex)

    @property
    def bank(self):
        return self.project

    def cleanup_project(self, project):
        if project != self.project or not project.startswith("em-e2e-") or len(project) != 39:
            raise DeploymentError("Refusing cleanup of an unowned project")
        try:
            uuid.UUID(hex=project[7:])
        except ValueError:
            raise DeploymentError("Refusing cleanup of an invalid identity") from None
        return project


@dataclass(frozen=True)
class Report:
    code: int
    message: str


def validate_environment(env, *, external):
    required = ["PRODUCT_PROXY_KEY"]
    required += (
        ["PRODUCT_PROXY_URL"]
        if external
        else ["PRODUCT_PROVIDER_MODEL", "PRODUCT_PROVIDER_API_BASE", "PRODUCT_PROVIDER_API_KEY"]
    )
    for name in required:
        if not env.get(name, "").strip():
            raise DeploymentError("Missing required variable: " + name)
    if (
        not external
        and env.get("PRODUCT_MODEL_ALIAS", "engineering-extraction") != "engineering-extraction"
    ):
        raise DeploymentError(
            "PRODUCT_MODEL_ALIAS must match the internal engineering-extraction route"
        )
    name = "PRODUCT_PROXY_URL" if external else "PRODUCT_PROVIDER_API_BASE"
    try:
        url = urlsplit(env[name])
        valid = (
            url.scheme in ("http", "https")
            and url.hostname
            and not url.username
            and not url.password
        )
        if external and url.hostname in ("localhost", "127.0.0.1", "::1"):
            valid = False
    except ValueError:
        valid = False
    if not valid:
        raise DeploymentError("Invalid container-reachable URL: " + name)


def execute(args, *, env, timeout):
    try:
        result = subprocess.run(
            args,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise DeploymentError("Command deadline exceeded") from None
    except OSError:
        raise DeploymentError(
            "Cannot execute Docker Compose; check installation and daemon"
        ) from None
    if result.returncode:
        raise DeploymentError(
            "Compose command failed; check configuration, images and service readiness"
        )


def compose(project, *, e2e=False, external=False):
    # The runner loads its explicit env file into env; suppress implicit checkout .env loading.
    args = [
        "docker",
        "compose",
        "--env-file",
        os.devnull,
        "-p",
        project,
        "-f",
        str(HERE / "compose.yaml"),
        "-f",
        str(HERE / ("compose.e2e.yaml" if e2e else "compose.dev.yaml")),
    ]
    if external:
        args += ["-f", str(HERE / "compose.external.yaml")]
    return [*args, "--profile", "tools", "--profile", "external" if external else "internal"]


def dependencies(external):
    return ["hindsight"] if external else ["litellm", "hindsight"]


def run_e2e(env, *, execute=execute, ready=False, external=False, limits=None):
    limits = limits or Limits()
    if not ready:
        return Report(77, "SKIPPED: product prerequisites #16/#17/#19/#21/#23/#24 are unavailable")
    if not any(env.get(k, "").strip() for k in ("PRODUCT_PROXY_KEY", "PRODUCT_PROVIDER_API_KEY")):
        return Report(77, "SKIPPED: model credentials are unavailable")
    validate_environment(env, external=external)
    identity = RunIdentity.create()
    base = compose(identity.project, e2e=True, external=external)
    # Do not let caller environment redirect Compose to a development project/bank.
    env = {**env, "COMPOSE_PROJECT_NAME": identity.project}
    deadline = time.monotonic() + limits.total
    stage = "startup"
    code, message = 0, "PASS"

    def run(arguments, budget):
        remaining = min(budget, deadline - time.monotonic())
        if remaining <= 0:
            raise DeploymentError("Total deadline exceeded")
        execute([*base, *arguments], env=env, timeout=remaining)

    try:
        run(
            [
                "up",
                "-d",
                "--wait",
                "--wait-timeout",
                str(math.ceil(limits.startup)),
                *dependencies(external),
            ],
            limits.startup,
        )
        stage = "provision"
        run(["run", "--build", "--rm", "--no-deps", "-T", "provision"], limits.startup)
        stage = "scenario"
        run(["run", "--rm", "--no-deps", "-T", "e2e"], limits.total)
    except (DeploymentError, subprocess.TimeoutExpired, OSError):
        code, message = 1, "FAIL: " + stage
    except KeyboardInterrupt:
        code, message = 130, "FAIL: interrupted during " + stage
    finally:
        identity.cleanup_project(identity.project)
        try:
            execute(
                [*base, "down", "--volumes", "--remove-orphans", "--timeout", "10"],
                env=env,
                timeout=limits.cleanup,
            )
        except (DeploymentError, subprocess.TimeoutExpired, OSError, KeyboardInterrupt):
            code = code or 1
            message += "; cleanup failed; recover owned project " + identity.project
    return Report(code, message + "; project=" + identity.project)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["config", "dependencies", "start", "stop", "reset", "e2e"]
    )
    parser.add_argument("--env-file", type=Path, default=HERE / ".env")
    parser.add_argument("--external", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--startup-timeout", type=float, default=600)
    parser.add_argument("--total-timeout", type=float, default=1800)
    parser.add_argument("--cleanup-timeout", type=float, default=60)
    parser.add_argument("--destroy-development-data", action="store_true")
    args = parser.parse_args(argv)
    if args.action == "e2e" and not args.live:
        print("SKIPPED: live E2E requires --live")
        return 77
    try:
        limits = Limits(args.startup_timeout, args.total_timeout, args.cleanup_timeout)
        ready = (
            json.loads((HERE / "capabilities.json").read_text(encoding="utf-8"))["ready"] is True
        )
        # Missing prerequisites short-circuit before credentials, Docker or any live mutation.
        if args.action == "e2e" and not ready:
            print("SKIPPED: product prerequisites #16/#17/#19/#21/#23/#24 are unavailable")
            return 77
        if args.action == "start" and not ready:
            raise DeploymentError(
                "Product initialization is unavailable; use dependencies for infrastructure only"
            )
        env = {
            **{k: v for k, v in dotenv_values(args.env_file).items() if v is not None},
            **os.environ,
        }
        env["COMPOSE_PROJECT_NAME"] = DEV_PROJECT
        if args.action in ("stop", "reset", "config"):
            # Down/config must work without credentials. Values are interpolation sentinels only.
            for key, value in {
                "PRODUCT_PROXY_KEY": "offline-placeholder",
                "PRODUCT_PROXY_URL": "http://proxy.invalid:4000/v1",
            }.items():
                if not env.get(key, "").strip():
                    env[key] = value
        elif args.action != "e2e":
            validate_environment(env, external=args.external)
        if args.action == "e2e":
            report = run_e2e(env, ready=ready, external=args.external, limits=limits)
            print(report.message)
            return report.code
        base = compose(DEV_PROJECT, external=args.external)
        if args.action == "reset" and not args.destroy_development_data:
            raise DeploymentError("Reset requires --destroy-development-data")
        if args.action in ("stop", "reset"):
            tail = ["down", "--timeout", "10"]
            if args.action == "reset":
                tail += ["--volumes"]
            execute([*base, *tail], env=env, timeout=limits.cleanup)
        elif args.action == "config":
            execute([*base, "config", "--quiet"], env=env, timeout=limits.startup)
        else:
            execute(
                [
                    *base,
                    "up",
                    "-d",
                    "--wait",
                    "--wait-timeout",
                    str(math.ceil(limits.startup)),
                    *dependencies(args.external),
                ],
                env=env,
                timeout=limits.startup,
            )
            if args.action == "start":
                execute(
                    [*base, "run", "--build", "--rm", "--no-deps", "-T", "provision"],
                    env=env,
                    timeout=limits.startup,
                )
        print(
            "OK: "
            + args.action
            + (" (infrastructure only)" if args.action == "dependencies" else "")
        )
        return 0
    except DeploymentError as error:
        print("FAIL: " + str(error), file=sys.stderr)
        return 1
    except (OSError, ValueError):
        # Never render unexpected parser/file errors that may quote credential values.
        print(
            "FAIL: configuration or lifecycle operation; "
            "verify variable names, Docker readiness and deadlines",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print("FAIL: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":

    def interrupted(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
