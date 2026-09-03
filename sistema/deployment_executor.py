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
        working_directory = str(self.config.get("working_directory") or "").strip()
        self.working_directory = Path(working_directory) if working_directory else None
        self.compose_file = self.config.get("compose_file") or "docker-compose.yml"

    def prepare(self):
        if self.working_directory is None or not self.working_directory.is_dir():
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
        if self.working_directory is None:
            raise DeploymentExecutionError(
                "working_directory_missing",
                "O diretório de deployment não existe ou não está acessível.",
            )
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
            # Nunca propagar stdout/stderr para o plano: ferramentas externas podem
            # imprimir tokens, URLs autenticadas ou outras credenciais por engano.
            raise DeploymentExecutionError(
                "command_failed",
                "Um comando controlado de deployment falhou. Consulte os logs locais do host para detalhes.",
            )
        return completed
