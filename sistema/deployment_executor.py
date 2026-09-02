import subprocess
from pathlib import Path


class DeploymentExecutionError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class LocalDockerComposeExecutor:
    DEFAULT_TIMEOUT = 120

    def __init__(self, config, *, runner=None):
        self.config = dict(config or {})
        self.runner = runner or subprocess.run
        self.working_directory = Path(self.config.get("working_directory", ""))
        self.compose_file = self.config.get("compose_file") or "docker-compose.yml"

    def prepare(self):
        if not self.working_directory.is_dir():
            raise DeploymentExecutionError(
                "working_directory_missing",
                "O diretório de deployment não existe ou não está acessível.",
            )
        compose_path = self.working_directory / self.compose_file
        if not compose_path.is_file():
            raise DeploymentExecutionError(
                "compose_file_missing",
                "O arquivo Docker Compose configurado não foi encontrado.",
            )
        self._run(["docker", "--version"], timeout=30)
        self._run(["docker", "compose", "version"], timeout=30)
        self._run(["docker", "compose", "-f", self.compose_file, "config", "--quiet"])
        return True

    def deploy(self):
        self._run(["docker", "compose", "-f", self.compose_file, "pull"])
        self._run(["docker", "compose", "-f", self.compose_file, "build"])
        self._run(["docker", "compose", "-f", self.compose_file, "up", "-d"])
        return True

    def _run(self, args, *, timeout=None):
        try:
            completed = self.runner(
                args,
                cwd=str(self.working_directory),
                capture_output=True,
                text=True,
                timeout=timeout or self.DEFAULT_TIMEOUT,
                check=False,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise DeploymentExecutionError(
                "command_not_found",
                "Docker não foi encontrado no host de deployment.",
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise DeploymentExecutionError(
                "command_timeout",
                "Uma etapa de deployment excedeu o tempo limite.",
            ) from exc
        except OSError as exc:
            raise DeploymentExecutionError(
                "command_error",
                "Não foi possível executar uma etapa de deployment.",
            ) from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            detail = stderr or stdout
            if detail:
                detail = detail.replace("\r", " ").replace("\n", " ")[:300]
                message = f"Comando de deployment falhou: {detail}"
            else:
                message = "Comando de deployment falhou."
            raise DeploymentExecutionError("command_failed", message)
        return completed
