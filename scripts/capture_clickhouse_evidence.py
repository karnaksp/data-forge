#!/usr/bin/env python3
"""Capture live ClickHouse ingestion evidence from a short local Docker run."""

from __future__ import annotations

import argparse
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "docs" / "assets"
COMPOSE = [
    "docker",
    "compose",
    "--env-file",
    ".env.example",
    "-f",
    "docker-compose.yml",
    "-f",
    "docker-compose.evidence.yml",
]
CORE_SERVICES = ["postgres", "kafka", "schema-registry", "clickhouse"]
DATAGEN_SERVICE = "data-generator"
COUNT_QUERIES = {
    "clickhouse-orders-count.txt": "SELECT count() AS orders FROM analytics.orders",
    "clickhouse-payments-count.txt": "SELECT count() AS payments FROM analytics.payments",
    "clickhouse-inventory-count.txt": (
        "SELECT count() AS inventory_changes FROM analytics.inventory_changes"
    ),
}


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def shell_command(parts: list[str]) -> str:
    return " ".join(parts)


def run(args: list[str], timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        command = " ".join(args)
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: {command}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def compose(args: list[str], timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run([*COMPOSE, *args], timeout=timeout, check=check)


def clickhouse_query(query: str, timeout: int = 60) -> str:
    result = compose(
        [
            "exec",
            "-T",
            "clickhouse",
            "clickhouse-client",
            "--query",
            query,
        ],
        timeout=timeout,
    )
    return result.stdout.strip() + "\n"


def wait_for_clickhouse(timeout_s: int) -> None:
    deadline = time.monotonic() + timeout_s
    last_error = ""
    while time.monotonic() < deadline:
        result = compose(
            [
                "exec",
                "-T",
                "clickhouse",
                "clickhouse-client",
                "--query",
                "SELECT 1",
            ],
            timeout=20,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip() == "1":
            return
        last_error = (result.stderr or result.stdout).strip()
        time.sleep(5)
    raise RuntimeError(f"ClickHouse did not become queryable: {last_error}")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {repo_relative(path)}")


def capture(args: argparse.Namespace) -> int:
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_up:
        compose(["--profile", "core", "up", "-d", *CORE_SERVICES], timeout=args.up_timeout)
        wait_for_clickhouse(args.wait_timeout)
        compose(["--profile", "datagen", "up", "-d", DATAGEN_SERVICE], timeout=args.up_timeout)
        time.sleep(args.duration)

    generated_at = datetime.now(timezone.utc).isoformat()
    show_tables = clickhouse_query("SHOW TABLES FROM analytics")
    write_text(
        output_dir / "clickhouse-show-tables.txt",
        f"generated_at={generated_at}\ncommand=SHOW TABLES FROM analytics\n\n{show_tables}",
    )

    for file_name, query in COUNT_QUERIES.items():
        output = clickhouse_query(query)
        count = parse_count(output)
        write_text(
            output_dir / file_name,
            f"generated_at={generated_at}\ncommand={query}\n\n{output}",
        )
        if count <= 0 and not args.allow_zero:
            raise RuntimeError(
                f"{query} returned {count}; rerun with a longer --duration or "
                "--allow-zero for diagnostic capture"
            )

    logs = compose(
        ["logs", "--no-color", "--tail", str(args.log_tail), DATAGEN_SERVICE],
        check=False,
    )
    write_text(
        output_dir / "clickhouse-ingestion-log.txt",
        "\n".join(
            [
                f"generated_at={generated_at}",
                f"duration_seconds={args.duration}",
                f"command={shell_command([*COMPOSE, 'logs', '--no-color', '--tail', str(args.log_tail), DATAGEN_SERVICE])}",
                "",
                logs.stdout.strip(),
                logs.stderr.strip(),
                "",
            ]
        ),
    )

    if args.cleanup:
        compose(["stop", DATAGEN_SERVICE], timeout=60, check=False)

    return 0


def parse_count(output: str) -> int:
    stripped = output.strip()
    if not stripped:
        return 0
    try:
        return int(stripped.splitlines()[-1])
    except ValueError as exc:
        raise RuntimeError(f"Could not parse ClickHouse count output: {output!r}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=int, default=60, help="Seconds to let generator run.")
    parser.add_argument("--wait-timeout", type=int, default=180, help="ClickHouse readiness wait.")
    parser.add_argument("--up-timeout", type=int, default=600, help="Compose startup timeout.")
    parser.add_argument("--log-tail", type=int, default=200, help="Generator log lines to capture.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for evidence text files.",
    )
    parser.add_argument(
        "--skip-up",
        action="store_true",
        help="Capture from already running services without starting Compose.",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Stop data-generator after capture. Core services are left running for inspection.",
    )
    parser.add_argument(
        "--allow-zero",
        action="store_true",
        help="Write diagnostic count files even when one or more ClickHouse counts are zero.",
    )
    return parser.parse_args()


def main() -> int:
    return capture(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
