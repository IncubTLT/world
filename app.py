#!/usr/bin/env python3

import os
import subprocess
import sys

import click

NETWORK_NAME = "common-network"


def load_dotenv_file(path: str) -> dict:
    vals = {}
    if not os.path.exists(path):
        return vals
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


def check_file_exists(file_path: str) -> None:
    if not os.path.exists(file_path):
        print(f"File '{file_path}' does not exist.")
        sys.exit(1)


def ensure_network_exists(network_name: str) -> None:
    result = subprocess.run(
        ["docker", "network", "ls", "--filter", f"name={network_name}", "--format", "{{.Name}}"],
        capture_output=True,
        text=True,
    )
    if network_name not in result.stdout.splitlines():
        print(f"Creating network '{network_name}'...")
        subprocess.run(["docker", "network", "create", "--driver", "bridge", network_name])


def start_docker_compose(
    compose_file: str,
    detached: bool = False,
    custom_env: dict | None = None,
    profiles: list[str] | None = None,
) -> None:
    """
    Запускает docker compose с учётом:
    - общих .env (возле compose и возле скрипта),
    - дополнительных переменных окружения (custom_env),
    - профилей docker compose (profiles).
    """
    ensure_network_exists(NETWORK_NAME)

    compose_file = os.path.abspath(compose_file)
    compose_dir = os.path.dirname(compose_file)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # кандидаты для .env
    env_from_compose_dir = os.path.join(compose_dir, ".env")
    env_from_script_dir = os.path.join(script_dir, ".env")

    check_file_exists(compose_file)  # .env может отсутствовать — это ок

    # База окружения: системные → из .env возле compose → из .env возле скрипта → кастом
    env_vars = os.environ.copy()
    env_vars.update(load_dotenv_file(env_from_compose_dir))
    env_vars.update(load_dotenv_file(env_from_script_dir))
    if custom_env:
        env_vars.update(custom_env)

    cmd = ["docker", "compose", "-f", compose_file]

    # Поддержка профилей (например, backend)
    if profiles:
        for profile in profiles:
            cmd.extend(["--profile", profile])

    cmd.extend(["up", "--build"])
    if detached:
        cmd.append("-d")

    # Важно: cwd = каталог compose-файла
    result = subprocess.run(cmd, env=env_vars, cwd=compose_dir)
    if result.returncode != 0:
        print(f"Error: docker compose failed with return code {result.returncode}")
        sys.exit(result.returncode)


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "-m",
    "--mode",
    type=click.Choice(["frontend", "full"], case_sensitive=False),
    default="frontend",
    show_default=True,
    help=(
        "frontend — без backend-контейнера (backend запущен локально); "
        "full — со всеми сервисами, включая backend в контейнере."
    ),
)
def debug(mode: str):
    """
    Запуск dev-окружения.

    Примеры:
      - ./app.py debug
          поднимет всё без backend-контейнера (режим разработки backend локально).

      - ./app.py debug --mode full
          поднимет весь стек, включая backend в контейнере (для разработки фронта).
    """
    custom_env = {
        "PGADMIN_DEFAULT_EMAIL": "admin@admin.ru",
        "PGADMIN_DEFAULT_PASSWORD": "admin_password",
    }

    profiles: list[str] | None = None
    if mode.lower() == "full":
        profiles = ["backend"]

    start_docker_compose("infra/debug/docker-compose.yml", custom_env=custom_env, profiles=profiles)


@cli.command()
@click.option(
    "--clean",
    is_flag=True,
    help="Удалить висячие образы и тома после остановки контейнеров",
)
def stop(clean: bool):
    """
    Грубая остановка и очистка всех контейнеров (как сейчас).
    """
    try:
        # Останавливаем все running-контейнеры
        result = subprocess.run(
            "docker ps -q",
            shell=True,
            check=True,
            capture_output=True,
            text=True,
        )
        container_ids = result.stdout.strip().split()

        if container_ids:
            container_ids_str = " ".join(container_ids)
            subprocess.run(f"docker stop {container_ids_str}", shell=True, check=True)
        else:
            print("No running containers to stop.")

        # Удаляем все контейнеры
        result = subprocess.run(
            "docker ps -a -q",
            shell=True,
            check=True,
            capture_output=True,
            text=True,
        )
        all_container_ids = result.stdout.strip().split()

        if all_container_ids:
            all_container_ids_str = " ".join(all_container_ids)
            subprocess.run(f"docker rm {all_container_ids_str}", shell=True, check=True)
        else:
            print("No containers to remove.")

        if clean:
            print("Cleaning up dangling images...")
            subprocess.run("docker image prune -f", shell=True, check=True)

            print("Cleaning up dangling volumes...")
            subprocess.run(
                'docker volume ls -qf dangling=true | grep -E "^[0-9a-f]{64}$" | xargs -r docker volume rm',
                shell=True,
                check=True,
            )
            print("Done!")

    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
