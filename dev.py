"""
dev.py

Unified Local Development Kickstart for Medical Exam AI.
Starts Docker infrastructure (Postgres + Redis), initializes/seeds the database,
and launches the FastAPI backend and Next.js frontend concurrently.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

# Fix Windows console UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Paths
ROOT_DIR = Path(__file__).resolve().parent
ENV_FILE = ROOT_DIR / ".env"
ENV_EXAMPLE = ROOT_DIR / ".env.example"
DOCKER_COMPOSE_FILE = ROOT_DIR / "infrastructure" / "docker-compose.yml"

# ANSI Colors for terminal output
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_CYAN = "\033[36m"
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_MAGENTA = "\033[35m"
COLOR_RED = "\033[31m"
COLOR_BLUE = "\033[34m"

# Enable Windows VT100 colors if possible
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


def log(prefix: str, message: str, color: str = COLOR_CYAN) -> None:
    """Prints a styled log line with auto-flush."""
    print(f"{color}{COLOR_BOLD}[{prefix}]{COLOR_RESET} {message}", flush=True)


def ensure_env_file() -> None:
    """Ensures .env exists; copies from .env.example if missing."""
    if not ENV_FILE.exists():
        if ENV_EXAMPLE.exists():
            shutil.copy(ENV_EXAMPLE, ENV_FILE)
            log("SETUP", "Created .env from .env.example", COLOR_GREEN)
        else:
            log("SETUP", "Warning: .env.example not found. Using default environment variables.", COLOR_YELLOW)
    else:
        log("SETUP", ".env configuration detected.", COLOR_GREEN)


def is_docker_running() -> bool:
    """Checks if Docker daemon is running."""
    try:
        res = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=4,
        )
        return res.returncode == 0
    except Exception:
        return False


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Checks if a TCP port is responding."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def start_docker_services() -> bool:
    """Starts PostgreSQL & Redis containers via docker-compose."""
    if not DOCKER_COMPOSE_FILE.exists():
        log("DOCKER", f"Compose file not found at {DOCKER_COMPOSE_FILE}", COLOR_YELLOW)
        return False

    if not is_docker_running():
        log("DOCKER", "Docker daemon is not running or not installed.", COLOR_YELLOW)
        log("DOCKER", "Skipping container startup (will use existing DB or fallback).", COLOR_YELLOW)
        return False

    log("DOCKER", "Starting PostgreSQL & Redis containers...", COLOR_BLUE)
    try:
        res = subprocess.run(
            ["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "up", "-d"],
            cwd=str(ROOT_DIR),
            check=False,
        )
        if res.returncode == 0:
            log("DOCKER", "Containers active. Verifying Postgres readiness...", COLOR_GREEN)
            for _ in range(15):
                if is_port_open("localhost", 5432):
                    time.sleep(1)
                    log("DOCKER", "PostgreSQL (port 5432) & Redis (port 6379) are READY!", COLOR_GREEN)
                    return True
                time.sleep(1)
            log("DOCKER", "Postgres container started; continuing startup.", COLOR_YELLOW)
            return True
        else:
            log("DOCKER", "Failed to start docker-compose services. Continuing anyway...", COLOR_RED)
            return False
    except Exception as e:
        log("DOCKER", f"Error launching docker: {e}", COLOR_RED)
        return False


def initialize_database(force_seed: bool = False) -> None:
    """Ensures database tables exist and seeds curriculum if empty."""
    sys.path.insert(0, str(ROOT_DIR))
    try:
        from database.db import init_db, session_scope
        from database.models import Course

        log("DATABASE", "Checking database schema...", COLOR_BLUE)
        init_db()
        log("DATABASE", "Database tables verified / initialized.", COLOR_GREEN)

        with session_scope() as session:
            course_count = session.query(Course).count()

        if course_count == 0 or force_seed:
            log("DATABASE", "Seeding foundational pathology curriculum & courses...", COLOR_CYAN)
            subprocess.run([sys.executable, str(ROOT_DIR / "scripts" / "seed_curriculum.py")], cwd=str(ROOT_DIR))
            log("DATABASE", "Curriculum seeded successfully.", COLOR_GREEN)
        else:
            log("DATABASE", f"Curriculum populated ({course_count} courses active).", COLOR_GREEN)
    except Exception as e:
        log("DATABASE", f"Database check note: {e}", COLOR_YELLOW)
        log("DATABASE", "Continuing startup; backend will connect on demand.", COLOR_YELLOW)


def find_frontend_runner() -> tuple[str, list[str]]:
    """Detects available frontend package manager (bun, npm, pnpm, yarn)."""
    if shutil.which("bun"):
        return "bun", ["bun", "--filter", "web", "dev"]
    elif shutil.which("pnpm"):
        return "pnpm", ["pnpm", "--filter", "web", "dev"]
    elif shutil.which("yarn"):
        return "yarn", ["yarn", "workspace", "web", "dev"]
    elif shutil.which("npm"):
        return "npm", ["npm", "--prefix", "apps/web", "run", "dev"]
    return "npx", ["npx", "next", "dev", "apps/web", "-p", "3000"]


def stream_pipe(pipe, prefix: str, color: str) -> None:
    """Reads lines from a text pipe and prints them prefixed."""
    try:
        for line in iter(pipe.readline, ""):
            cleaned = line.rstrip()
            if cleaned:
                print(f"{color}{COLOR_BOLD}[{prefix}]{COLOR_RESET} {cleaned}", flush=True)
    except Exception:
        pass


def print_banner() -> None:
    """Displays the interactive service dashboard banner."""
    print(f"""
{COLOR_CYAN}{COLOR_BOLD}===========================================================================
  [+] MEDICAL EXAM AI — LOCAL DEVELOPMENT ENVIRONMENT ACTIVE
==========================================================================={COLOR_RESET}
  {COLOR_GREEN}* {COLOR_BOLD}Frontend Web App:{COLOR_RESET}        {COLOR_CYAN}http://localhost:3000{COLOR_RESET}
  {COLOR_GREEN}* {COLOR_BOLD}FastAPI Backend API:{COLOR_RESET}     {COLOR_CYAN}http://localhost:8000{COLOR_RESET}
  {COLOR_GREEN}* {COLOR_BOLD}Interactive API Docs:{COLOR_RESET}    {COLOR_CYAN}http://localhost:8000/docs{COLOR_RESET}
  {COLOR_GREEN}* {COLOR_BOLD}PostgreSQL Database:{COLOR_RESET}     {COLOR_CYAN}localhost:5432{COLOR_RESET} (DB: medical_exam_ai)
  {COLOR_GREEN}* {COLOR_BOLD}Redis Queue & Cache:{COLOR_RESET}     {COLOR_CYAN}localhost:6379{COLOR_RESET}
{COLOR_CYAN}==========================================================================={COLOR_RESET}
  {COLOR_YELLOW}Press Ctrl+C to stop all development services gracefully.{COLOR_RESET}
""", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Medical Exam AI - Local Development Kickstart")
    parser.add_argument("--no-docker", action="store_true", help="Skip starting Docker containers")
    parser.add_argument("--backend-only", action="store_true", help="Run only the FastAPI backend")
    parser.add_argument("--web-only", action="store_true", help="Run only the Next.js frontend")
    parser.add_argument("--seed", action="store_true", help="Force re-seeding the curriculum database")
    args = parser.parse_args()

    print(f"\n{COLOR_CYAN}{COLOR_BOLD}>>> Kickstarting Medical Exam AI Development Environment...{COLOR_RESET}\n", flush=True)

    # Step 1: Environment file verification
    ensure_env_file()

    # Step 2: Docker containers
    if not args.no_docker and not args.web_only:
        start_docker_services()

    # Step 3: Database tables & curriculum seed
    if not args.web_only:
        initialize_database(force_seed=args.seed)

    processes: list[subprocess.Popen] = []

    def cleanup(*_) -> None:
        print(f"\n{COLOR_YELLOW}Stopping development services...{COLOR_RESET}", flush=True)
        for p in processes:
            try:
                p.terminate()
                p.wait(timeout=2)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        print(f"{COLOR_GREEN}[*] All services stopped. Goodbye!{COLOR_RESET}\n", flush=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Step 4: Launch Backend API
    if not args.web_only:
        log("BACKEND", "Launching FastAPI Backend on http://127.0.0.1:8000...", COLOR_GREEN)
        backend_cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.api.main:app",
            "--reload",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ]
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=str(ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        processes.append(backend_proc)

        threading.Thread(
            target=stream_pipe,
            args=(backend_proc.stdout, "BACKEND", COLOR_GREEN),
            daemon=True,
        ).start()
        threading.Thread(
            target=stream_pipe,
            args=(backend_proc.stderr, "BACKEND", COLOR_GREEN),
            daemon=True,
        ).start()

    # Step 5: Launch Frontend Web App
    if not args.backend_only:
        runner_name, frontend_cmd = find_frontend_runner()
        log("FRONTEND", f"Launching Next.js web application via {runner_name} on http://localhost:3000...", COLOR_MAGENTA)
        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=str(ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        processes.append(frontend_proc)

        threading.Thread(
            target=stream_pipe,
            args=(frontend_proc.stdout, "WEB", COLOR_MAGENTA),
            daemon=True,
        ).start()
        threading.Thread(
            target=stream_pipe,
            args=(frontend_proc.stderr, "WEB", COLOR_MAGENTA),
            daemon=True,
        ).start()

    # Step 6: Print Dashboard Banner
    time.sleep(2)
    print_banner()

    # Keep main thread alive and supervise children
    try:
        while True:
            time.sleep(0.5)
            for p in processes:
                if p.poll() is not None:
                    log("SUPERVISOR", f"A service process exited with code {p.returncode}.", COLOR_YELLOW)
                    cleanup()
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
