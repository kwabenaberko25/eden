"""
Eden — Task Queue Management CLI

Unified commands for background tasks, workers, and schedulers.

Usage::

    eden tasks worker              # Start worker processes
    eden tasks scheduler           # Start periodic task scheduler
    eden tasks list                # List registered periodic tasks
    eden tasks status              # Show task execution status
    eden tasks dead-letter         # View permanently failed tasks
    eden tasks retry <task_id>     # Manually retry a failed task
"""

from __future__ import annotations

import importlib
import asyncio
import json
import logging
import sys
from typing import Optional

import click


@click.group()
def tasks() -> None:
    """⏰ Eden Tasks — Background job management."""
    pass


@tasks.command()
@click.option("--app", "app_path", default="app:app", help="App import path (module:variable).")
@click.option("--workers", default=2, type=int, help="Number of worker processes.")
@click.option("--log-level", default="INFO", help="Logging level.")
def worker(app_path: str, workers: int, log_level: str) -> None:
    """
    Start taskiq worker processes for background job execution.
    
    Workers pull tasks from the broker queue and execute them.
    
    Example::
    
        eden tasks worker --workers 4
    """
    click.echo(f"  🐝 Starting Eden worker: {app_path}")

    # Import the app to get its broker
    module_name, obj_name = app_path.split(":")
    module = importlib.import_module(module_name)
    app = getattr(module, obj_name)

    # Get the broker path for taskiq CLI
    broker_path = f"{module_name}:{obj_name}.broker"

    # Configure and run taskiq worker
    sys.argv = [
        "taskiq", "worker", broker_path,
        "--workers", str(workers),
        "--log-level", log_level,
    ]

    try:
        from taskiq.cli.worker.args import WorkerArgs
        from taskiq.cli.worker.run import run_worker

        run_worker(WorkerArgs(
            broker=broker_path,
            workers=workers,
            log_level=log_level,
        ))
    except ImportError:
        click.echo("  ✗ Taskiq worker CLI not available. Install taskiq with: pip install taskiq", err=True)
        raise click.ClickException("Taskiq not properly installed")


@tasks.command()
@click.option("--app", "app_path", default="app:app", help="App import path (module:variable).")
def scheduler(app_path: str) -> None:
    """
    Start the task scheduler for periodic/cron tasks.
    
    The scheduler runs periodic tasks registered via @app.task.every(...).
    
    Example::
    
        eden tasks scheduler
    """
    click.echo(f"  ⏰ Starting Eden scheduler: {app_path}")

    # Import the app
    module_name, obj_name = app_path.split(":")
    module = importlib.import_module(module_name)
    app = getattr(module, obj_name)

    # Run the scheduler event loop
    try:
        async def run_scheduler():
            click.echo(f"  ⏰ Periodic tasks registered: {len(app.broker.periodic_tasks)}")
            for task in app.broker.periodic_tasks:
                click.echo(f"     → {task.func.__name__} (every {task.interval}s)")
            
            # Start the broker (which starts periodic tasks)
            await app.broker.startup()
            
            try:
                # Keep scheduler running
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                click.echo("\n  Shutting down scheduler...")
                await app.broker.shutdown()
                click.echo("  ✓ Scheduler stopped")

        asyncio.run(run_scheduler())
    except Exception as e:
        click.echo(f"  ✗ Scheduler error: {e}", err=True)
        raise click.ClickException(str(e))


@tasks.command()
@click.option("--app", "app_path", default="app:app", help="App import path (module:variable).")
def list(app_path: str) -> None:
    """
    List all registered periodic tasks.
    
    Shows task names, intervals, and status.
    
    Example::
    
        eden tasks list
    """
    module_name, obj_name = app_path.split(":")
    module = importlib.import_module(module_name)
    app = getattr(module, obj_name)

    tasks_list = app.broker.periodic_tasks
    
    if not tasks_list:
        click.echo("  ℹ No periodic tasks registered")
        return

    click.echo(f"  📋 Registered Periodic Tasks ({len(tasks_list)}):")
    click.echo()

    for task in tasks_list:
        click.echo(f"    • {task.func.__name__}")
        click.echo(f"      Interval: {task.interval}s")
        if task.last_error:
            click.echo(f"      Last Error: {task.last_error}")
        click.echo()


@tasks.command()
@click.option("--app", "app_path", default="app:app", help="App import path (module:variable).")
def status(app_path: str) -> None:
    """
    Show task execution status and statistics.
    
    Displays broker status, task queue info, and periodic task state.
    
    Example::
    
        eden tasks status
    """
    module_name, obj_name = app_path.split(":")
    module = importlib.import_module(module_name)
    app = getattr(module, obj_name)

    broker = app.broker
   
    click.echo(f"  📊 Task Broker Status:")
    click.echo(f"     Running: {broker.is_running}")
    click.echo(f"     Periodic Tasks: {len(broker.periodic_tasks)}")
    click.echo()

    # Show details for each periodic task
    click.echo(f"  🔄 Periodic Task Details:")
    for task in broker.periodic_tasks:
        status_icon = "✓" if task.execution_count > 0 else "⏱"
        click.echo(f"     {status_icon} {task.func.__name__}")
        click.echo(f"        Executions: {task.execution_count}")
        click.echo(f"        Interval: {task.interval}s")
        if task.last_error:
            click.echo(f"        Last Error: {str(task.last_error)[:60]}...")
        click.echo()


@tasks.command()
@click.option("--app", "app_path", default="app:app", help="App import path (module:variable).")
def dead_letter(app_path: str) -> None:
    """
    View tasks that failed permanently (exhausted retries).
    
    Shows all tasks in the dead-letter queue with error details.
    
    Example::
    
        eden tasks dead-letter
    """
    module_name, obj_name = app_path.split(":")
    module = importlib.import_module(module_name)
    app = getattr(module, obj_name)

    async def get_dead_letter():
        tasks = await app.broker.get_dead_letter_tasks()
        return tasks

    try:
        tasks = asyncio.run(get_dead_letter())
        
        if not tasks:
            click.echo("  ✓ No dead-letter tasks (all good!)")
            return

        click.echo(f"  ⚠ Dead-Letter Tasks: {len(tasks)}")
        click.echo()

        for result in tasks:
            click.echo(f"    {result.task_id}: {result.task_name}")
            click.echo(f"      Status: {result.status}")
            click.echo(f"      Retries: {result.retries}")
            click.echo(f"      Error: {result.error}")
            click.echo()

    except Exception as e:
        click.echo(f"  ✗ Error retrieving dead-letter tasks: {e}", err=True)


__all__ = ["tasks"]
