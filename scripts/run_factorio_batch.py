#!/usr/bin/env python3
"""Run a three-repeat Factorio batch and report every run automatically."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP_SEED = 44340
DEFAULT_BATCH_COOLDOWN_MINUTES = 30
DEFAULT_START_TEMPERATURE_C = 55
DEFAULT_HARD_TEMPERATURE_C = 82
DEFAULT_RESUME_TEMPERATURE_C = 60


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except Exception:
        return "unavailable"


def windows_host() -> str:
    result = subprocess.check_output(
        ["sh", "-c", "ip route show | awk '/default/ {print $3; exit}'"],
        text=True,
    ).strip()
    if not result:
        raise RuntimeError("Could not determine the Windows host address from WSL.")
    return result


def cumulative_prompt(level: int, prompt_dir: Path) -> str:
    sections = []
    for number in range(1, level + 1):
        path = prompt_dir / f"level_{number:02d}.txt"
        if not path.is_file():
            raise FileNotFoundError(f"Missing prompt file: {path}")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError(f"Prompt file is empty: {path}")
        sections.append(text)
    return "\n\n".join(sections) + "\n"


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def gpu_snapshot(stage: str, run_id: str | None = None) -> dict:
    command = [
        "nvidia-smi",
        "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw",
        "--format=csv,noheader,nounits",
    ]
    output = subprocess.check_output(command, text=True).strip().splitlines()[0]
    values = [value.strip() for value in output.split(",")]
    return {
        "timestamp_utc": utc_now(),
        "stage": stage,
        "run_id": run_id,
        "gpu_name": values[0],
        "temperature_c": float(values[1]),
        "utilization_percent": float(values[2]),
        "memory_used_mib": float(values[3]),
        "memory_total_mib": float(values[4]),
        "power_draw_w": float(values[5]),
    }


def wait_for_temperature(maximum_c: float, stage: str, run_id: str | None,
                         manifest: dict, manifest_path: Path,
                         poll_seconds: int = 60) -> dict:
    while True:
        sample = gpu_snapshot(stage, run_id)
        manifest.setdefault("hardware_samples", []).append(sample)
        write_json(manifest_path, manifest)
        print(
            f"GPU: {sample['temperature_c']:.0f}°C, "
            f"{sample['utilization_percent']:.0f}% utilization, "
            f"{sample['power_draw_w']:.1f} W"
        )
        if sample["temperature_c"] <= maximum_c:
            return sample
        print(
            f"Waiting {poll_seconds} seconds for GPU temperature to fall "
            f"to {maximum_c:.0f}°C or below..."
        )
        time.sleep(poll_seconds)


def verify_reset_and_seed(expected_seed: int) -> dict:
    fle_spec = importlib.util.find_spec("fle")
    if fle_spec is None or fle_spec.origin is None:
        raise RuntimeError(
            "FLE is not installed in the active Python environment. "
            "Install requirements.txt before running a game batch."
        )
    fle_root = Path(fle_spec.origin).resolve().parent
    compose = fle_root / "cluster/docker-compose.yml"
    reset_lua = fle_root / "env/tools/admin/reset/server.lua"
    environment = fle_root / "env/gym_env/environment.py"
    checks = {
        "compose_exists": compose.is_file(),
        "reset_lua_exists": reset_lua.is_file(),
        "environment_exists": environment.is_file(),
    }
    if not all(checks.values()):
        raise RuntimeError(f"FLE control files are missing: {checks}")
    compose_text = compose.read_text(encoding="utf-8", errors="replace")
    reset_text = reset_lua.read_text(encoding="utf-8", errors="replace")
    environment_text = environment.read_text(encoding="utf-8", errors="replace")
    checks.update({
        "fixed_seed_present": f"--map-gen-seed {expected_seed}" in compose_text,
        "resources_regenerated": "regenerate_resources" in reset_text,
        "entities_cleared": "clear_entities" in reset_text,
        "production_stats_reset": "reset_production_stats" in reset_text,
        "research_reset": "force.reset()" in reset_text,
        "environment_calls_reset": "self.reset_instance(game_state)" in environment_text,
    })
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("Run-independence preflight failed: " + ", ".join(failed))
    return checks


def restart_factorio(container_name: str, timeout_seconds: int = 120) -> dict:
    started = utc_now()
    result = subprocess.run(
        ["docker", "restart", container_name],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Could not restart {container_name}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", 27000), timeout=2):
                time.sleep(2)
                return {
                    "container": container_name,
                    "restart_started_at_utc": started,
                    "rcon_ready_at_utc": utc_now(),
                    "status": "ready",
                }
        except OSError:
            time.sleep(2)
    raise RuntimeError(
        f"Factorio RCON did not become ready within {timeout_seconds} seconds "
        f"after restarting {container_name}."
    )


def enforce_prior_batch_cooldown(output_root: Path, cooldown_minutes: int,
                                 start_temperature_c: float) -> None:
    state_path = output_root / "hardware_cooldown.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        release = parse_utc(state["cooldown_required_until_utc"])
        while datetime.now(timezone.utc) < release:
            remaining = int((release - datetime.now(timezone.utc)).total_seconds())
            wait_seconds = min(60, max(1, remaining))
            print(
                f"Prior batch cooldown remains active for approximately "
                f"{max(1, remaining // 60)} minute(s)."
            )
            time.sleep(wait_seconds)
    # Temperature is checked again after the time-based cooldown by the caller.


def run_command(command: list[str], env: dict[str, str], log_path: Path) -> int:
    with log_path.open("w", encoding="utf-8", buffering=1) as log:
        log.write("COMMAND\n" + " ".join(command) + "\n\nOUTPUT\n")
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            log.write(line)
        return process.wait()


def locate_eval(raw_dir: Path) -> Path | None:
    files = sorted(raw_dir.rglob("*.eval"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=["fixed", "adaptive"], required=True)
    parser.add_argument("--level", type=int, choices=range(1, 13), required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--turns", type=int, default=150)
    parser.add_argument("--validation", action="store_true", help="Allow a non-production repeat/turn count.")
    parser.add_argument("--model", default="openai/gemma4-fle:26b")
    parser.add_argument("--reasoning-effort", default="none")
    parser.add_argument("--output-root", type=Path, default=ROOT / "experiment_runs")
    parser.add_argument("--prompt-dir", type=Path, default=ROOT / "prompts" / "fixed")
    parser.add_argument("--adaptive-review", type=Path)
    parser.add_argument("--map-seed", type=int, default=DEFAULT_MAP_SEED)
    parser.add_argument("--cooldown-minutes", type=int, default=DEFAULT_BATCH_COOLDOWN_MINUTES)
    parser.add_argument("--start-temperature-c", type=float, default=DEFAULT_START_TEMPERATURE_C)
    parser.add_argument("--hard-temperature-c", type=float, default=DEFAULT_HARD_TEMPERATURE_C)
    parser.add_argument("--resume-temperature-c", type=float, default=DEFAULT_RESUME_TEMPERATURE_C)
    parser.add_argument("--factorio-container", default="cluster-factorio_0-1")
    parser.add_argument(
        "--skip-reporting",
        action="store_true",
        help=(
            "Preserve Inspect .eval files without calling the archived "
            "project-local reporting programs. Use for validation or when "
            "the reporting layer has not been restored."
        ),
    )
    args = parser.parse_args()

    args.prompt_dir = Path(args.prompt_dir).resolve()
    os.environ["FLE_PROMPT_DIR"] = str(args.prompt_dir)
    print(f"Active prompt directory: {args.prompt_dir}")

    if not args.validation and (args.repeats != 3 or args.turns != 150):
        parser.error("Production batches require exactly --repeats 3 and --turns 150. Use --validation for test runs.")

    if args.arm == "adaptive" and not args.adaptive_review:
        parser.error("Adaptive batches require --adaptive-review pointing to the completed review record.")
    if args.adaptive_review and not args.adaptive_review.is_file():
        parser.error(f"Adaptive review file does not exist: {args.adaptive_review}")

    prompt = cumulative_prompt(args.level, args.prompt_dir)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    host = windows_host()
    base_url = f"http://{host}:11434/v1"
    with urlopen(f"http://{host}:11434/api/tags", timeout=5) as response:
        ollama_tags = json.loads(response.read().decode("utf-8"))

    batch_stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    batch_id = f"FLE_{args.arm}_L{args.level:02d}_B{batch_stamp}"
    batch_dir = args.output_root.resolve() / batch_id
    batch_dir.mkdir(parents=True, exist_ok=False)
    controls = verify_reset_and_seed(args.map_seed)
    enforce_prior_batch_cooldown(args.output_root.resolve(), args.cooldown_minutes, args.start_temperature_c)
    batch_evals: list[Path] = []

    batch_manifest = {
        "batch_id": batch_id,
        "arm": args.arm,
        "specificity_level": args.level,
        "planned_repeats": args.repeats,
        "turn_budget": args.turns,
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "validation_run": args.validation,
        "map_seed": args.map_seed,
        "run_independence_checks": controls,
        "fresh_scenario_before_each_run": True,
        "factorio_container": args.factorio_container,
        "hardware_monitoring": {
            "start_temperature_c": args.start_temperature_c,
            "hard_temperature_c": args.hard_temperature_c,
            "resume_temperature_c": args.resume_temperature_c,
            "batch_cooldown_minutes": args.cooldown_minutes,
        },
        "hardware_samples": [],
        "prompt_sha256": prompt_hash,
        "started_at_utc": utc_now(),
        "git_commit": safe_git_value("rev-parse", "HEAD"),
        "git_status": safe_git_value("status", "--short"),
        "ollama_tags": ollama_tags,
        "adaptive_review": str(args.adaptive_review.resolve()) if args.adaptive_review else None,
        "runs": [],
    }
    write_json(batch_dir / "batch_manifest.json", batch_manifest)
    (batch_dir / "prompt_snapshot.txt").write_text(prompt, encoding="utf-8")
    if args.adaptive_review:
        shutil.copy2(args.adaptive_review, batch_dir / "adaptive_batch_review.md")

    env = os.environ.copy()
    env.update({
        "OPENAI_BASE_URL": base_url,
        "OPENAI_API_KEY": "ollama",
        "OLLAMA_BASE_URL": base_url,
        "OLLAMA_API_KEY": "ollama",
        "FLE_SPECIFICITY_LEVEL": str(args.level),
        "FLE_TRAJECTORY_LENGTH": str(args.turns),
    })

    for repeat in range(1, args.repeats + 1):
        run_stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        run_id = f"FLE_{args.arm}_L{args.level:02d}_R{repeat:02d}_{run_stamp}"
        run_dir = batch_dir / run_id
        raw_dir = run_dir / "raw"
        report_dir = run_dir / "report"
        raw_dir.mkdir(parents=True)
        report_dir.mkdir()
        (run_dir / "prompt_snapshot.txt").write_text(prompt, encoding="utf-8")

        metadata = {
            "run_id": run_id,
            "batch_id": batch_id,
            "arm": args.arm,
            "specificity_level": args.level,
            "repeat": repeat,
            "turn_budget": args.turns,
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "prompt_sha256": prompt_hash,
            "started_at_utc": utc_now(),
            "status": "running",
            "platform": platform.platform(),
            "python": sys.version,
            "git_commit": batch_manifest["git_commit"],
        }
        write_json(run_dir / "metadata.json", metadata)

        print(
            f"Restarting {args.factorio_container} to create a fresh "
            f"seed-{args.map_seed} scenario..."
        )
        scenario_restart = restart_factorio(args.factorio_container)
        metadata["factorio_scenario_restart"] = scenario_restart
        write_json(run_dir / "metadata.json", metadata)

        pre_run_gpu = wait_for_temperature(
            args.start_temperature_c if repeat == 1 else args.hard_temperature_c - 1,
            "pre_run", run_id, batch_manifest,
            batch_dir / "batch_manifest.json",
        )
        metadata["gpu_before"] = pre_run_gpu
        write_json(run_dir / "metadata.json", metadata)

        command = [
            "inspect", "eval", "experiments/specificity_eval.py@specificity_experiment",
            "--model", args.model,
            "--reasoning-effort", args.reasoning_effort,
            "--log-dir", str(raw_dir),
            "--max-connections", "1",
            "--limit", "1",
        ]
        print(f"\n{'=' * 72}\nStarting {run_id}\n{'=' * 72}")
        exit_code = run_command(command, env, run_dir / "console.log")
        post_run_gpu = gpu_snapshot("post_run", run_id)
        batch_manifest.setdefault("hardware_samples", []).append(post_run_gpu)
        metadata["gpu_after"] = post_run_gpu
        if post_run_gpu["temperature_c"] >= args.hard_temperature_c and repeat < args.repeats:
            print(
                f"GPU reached {post_run_gpu['temperature_c']:.0f}°C. "
                f"Pausing before the next run."
            )
            wait_for_temperature(
                args.resume_temperature_c, "thermal_pause", run_id,
                batch_manifest, batch_dir / "batch_manifest.json",
            )
        eval_path = locate_eval(raw_dir)
        metadata.update({
            "completed_at_utc": utc_now(),
            "inspect_exit_code": exit_code,
            "status": "completed" if exit_code == 0 else "failed",
            "eval_file": str(eval_path.relative_to(run_dir)) if eval_path else None,
        })

        if eval_path:
            stable_eval = run_dir / f"{run_id}.eval"
            shutil.copy2(eval_path, stable_eval)
            batch_evals.append(stable_eval)
            if args.skip_reporting:
                metadata["report_exit_code"] = None
                metadata["report_status"] = "skipped"
            else:
                report_program = ROOT / "reporting" / "build_reports.py"
                if not report_program.is_file():
                    raise RuntimeError(
                        "reporting/build_reports.py is unavailable. Restore "
                        "the reporting layer or pass --skip-reporting."
                    )
                report_command = [
                    sys.executable, str(report_program),
                    str(stable_eval), "--output-dir", str(report_dir),
                    "--name-prefix", run_id,
                ]
                report_status = subprocess.run(
                    report_command, cwd=ROOT, env=env
                ).returncode
                metadata["report_exit_code"] = report_status
        else:
            metadata["report_exit_code"] = None
            metadata["report_error"] = "Inspect did not create an .eval archive. Review console.log."

        write_json(run_dir / "metadata.json", metadata)
        batch_manifest["runs"].append(metadata)
        write_json(batch_dir / "batch_manifest.json", batch_manifest)
        if exit_code != 0:
            print(f"Run {run_id} failed. Batch stopped; completed artifacts were preserved.")
            batch_manifest["status"] = "stopped_after_failure"
            batch_manifest["completed_at_utc"] = utc_now()
            write_json(batch_dir / "batch_manifest.json", batch_manifest)
            return exit_code

    if args.skip_reporting:
        batch_manifest.update({
            "status": "completed_without_reports",
            "aggregate_report_exit_code": None,
            "workbook_exit_code": None,
            "workbook_file": None,
            "completed_at_utc": utc_now(),
        })
        write_json(batch_dir / "batch_manifest.json", batch_manifest)
        cooldown_state = {
            "completed_batch_id": batch_id,
            "batch_completed_at_utc": batch_manifest["completed_at_utc"],
            "cooldown_minutes": args.cooldown_minutes,
            "cooldown_required_until_utc": (
                datetime.now(timezone.utc) + timedelta(minutes=args.cooldown_minutes)
            ).replace(microsecond=0).isoformat(),
        }
        write_json(args.output_root.resolve() / "hardware_cooldown.json", cooldown_state)
        print(f"\nBatch complete: {batch_dir}")
        print("Reporting was skipped; stable Inspect archives were preserved.")
        return 0

    aggregate_dir = batch_dir / "batch_report"
    aggregate_command = [
        sys.executable, str(ROOT / "reporting" / "build_reports.py"),
        *map(str, batch_evals), "--output-dir", str(aggregate_dir),
    ]
    aggregate_status = subprocess.run(aggregate_command, cwd=ROOT, env=env).returncode
    workbook_path = aggregate_dir / f"{batch_id}_results.xlsx"
    workbook_command = [
        sys.executable, str(ROOT / "reporting" / "build_workbook_portable.py"),
        str(aggregate_dir / "report_data.json"), str(workbook_path),
        "--batch-manifest", str(batch_dir / "batch_manifest.json"),
    ]
    workbook_status = (
        subprocess.run(workbook_command, cwd=ROOT, env=env).returncode
        if aggregate_status == 0 else None
    )
    batch_manifest.update({
        "status": "completed" if aggregate_status == 0 and workbook_status == 0 else "reporting_failed",
        "aggregate_report_exit_code": aggregate_status,
        "workbook_exit_code": workbook_status,
        "workbook_file": str(workbook_path.relative_to(batch_dir)) if workbook_status == 0 else None,
        "completed_at_utc": utc_now(),
    })
    write_json(batch_dir / "batch_manifest.json", batch_manifest)
    cooldown_state = {
        "completed_batch_id": batch_id,
        "batch_completed_at_utc": batch_manifest["completed_at_utc"],
        "cooldown_minutes": args.cooldown_minutes,
        "cooldown_required_until_utc": (
            datetime.now(timezone.utc)
            + timedelta(minutes=args.cooldown_minutes)
        ).replace(microsecond=0).isoformat(),
    }
    write_json(args.output_root.resolve() / "hardware_cooldown.json", cooldown_state)
    print(f"\nBatch complete: {batch_dir}")
    print(f"Readable logs: {batch_dir}/*/report/*_readable.txt")
    print(f"Aggregate tables: {aggregate_dir}")
    if workbook_status == 0:
        print(f"Compiled workbook: {workbook_path}")
    return aggregate_status or workbook_status or 0


if __name__ == "__main__":
    raise SystemExit(main())
