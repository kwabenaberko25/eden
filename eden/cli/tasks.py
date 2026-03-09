"""
Eden — Task Worker CLI
"""

import importlib
import sys

import click


@click.command()
@click.option("--app", "app_path", default="app:app", help="App import path (module:variable).")
@click.option("--workers", default=2, type=int, help="Number of worker processes.")
@click.option("--log-level", default="INFO", help="Logging level.")
def worker(app_path: str, workers: int, log_level: str) -> None:
    """Start taskiq worker processes."""
    click.echo(f"  🐝 Starting Eden worker: {app_path}")

    # We need to pass the broker to taskiq
    module_name, obj_name = app_path.split(":")
    module = importlib.import_module(module_name)
    getattr(module, obj_name)

    # Taskiq expects the broker path or object
    # For simplicity, we can use the app's broker

    # Run the worker
    # Note: taskiq.run_worker is what the CLI uses
    # We might need to adapt this to how taskiq CLI works
    # Actually, taskiq CLI usually takes the broker path: 'module:broker'
    broker_path = f"{module_name}:{obj_name}.broker"

    sys.argv = [
        "taskiq", "worker", broker_path,
        "--workers", str(workers),
        "--log-level", log_level,
    ]

    from taskiq.cli.worker.args import WorkerArgs
    from taskiq.cli.worker.run import run_worker

    # This is a bit hacky but it avoids re-implementing taskiq's complex CLI logic
    # Real implementation would be more robust
    run_worker(WorkerArgs(
        broker=broker_path,
        workers=workers,
        log_level=log_level,
    ))

@click.command()
@click.option("--app", "app_path", default="app:app", help="App import path (module:variable).")
def scheduler(app_path: str) -> None:
    """Start taskiq scheduler."""
    click.echo(f"  ⏰ Starting Eden scheduler: {app_path}")

    module_name, obj_name = app_path.split(":")
    broker_path = f"{module_name}:{obj_name}.broker"

    from taskiq.cli.scheduler.args import SchedulerArgs
    from taskiq.cli.scheduler.run import run_scheduler

    run_scheduler(SchedulerArgs(
        broker=broker_path,
    ))
