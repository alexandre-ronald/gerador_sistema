import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

from django.test import SimpleTestCase

from .deployment_executor import DeploymentExecutionError, LocalDockerComposeExecutor


class LocalDockerComposeExecutorTests(SimpleTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.working_directory = Path(self.tempdir.name)
        (self.working_directory / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
        self.calls = []

    def tearDown(self):
        self.tempdir.cleanup()

    def runner(self, args, **kwargs):
        self.calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def executor(self, runner=None):
        return LocalDockerComposeExecutor(
            {
                "working_directory": str(self.working_directory),
                "compose_file": "docker-compose.yml",
            },
            runner=runner or self.runner,
        )

    def test_prepare_uses_closed_commands_and_shell_false(self):
        self.executor().prepare()
        self.assertEqual(
            [call[0] for call in self.calls],
            [
                ["docker", "--version"],
                ["docker", "compose", "version"],
                ["docker", "compose", "-f", "docker-compose.yml", "config", "--quiet"],
            ],
        )
        for _, kwargs in self.calls:
            self.assertFalse(kwargs["shell"])
            self.assertEqual(kwargs["cwd"], str(self.working_directory))

    def test_deploy_uses_only_expected_compose_commands(self):
        self.executor().deploy()
        self.assertEqual(
            [call[0] for call in self.calls],
            [
                ["docker", "compose", "-f", "docker-compose.yml", "pull"],
                ["docker", "compose", "-f", "docker-compose.yml", "build"],
                ["docker", "compose", "-f", "docker-compose.yml", "up", "-d"],
            ],
        )

    def test_empty_working_directory_fails_closed(self):
        executor = LocalDockerComposeExecutor(
            {"working_directory": "", "compose_file": "docker-compose.yml"},
            runner=self.runner,
        )
        with self.assertRaises(DeploymentExecutionError) as ctx:
            executor.prepare()
        self.assertEqual(ctx.exception.code, "working_directory_missing")
        self.assertEqual(self.calls, [])

    def test_missing_working_directory_fails_before_commands(self):
        executor = LocalDockerComposeExecutor(
            {"working_directory": str(self.working_directory / "missing"), "compose_file": "docker-compose.yml"},
            runner=self.runner,
        )
        with self.assertRaises(DeploymentExecutionError) as ctx:
            executor.prepare()
        self.assertEqual(ctx.exception.code, "working_directory_missing")
        self.assertEqual(self.calls, [])

    def test_missing_compose_file_fails_before_commands(self):
        (self.working_directory / "docker-compose.yml").unlink()
        with self.assertRaises(DeploymentExecutionError) as ctx:
            self.executor().prepare()
        self.assertEqual(ctx.exception.code, "compose_file_missing")
        self.assertEqual(self.calls, [])

    def test_command_failure_does_not_expose_process_output(self):
        secret = "TOKEN_SUPER_SECRETO"

        def failing_runner(args, **kwargs):
            return SimpleNamespace(returncode=1, stdout=f"url?token={secret}", stderr=f"password={secret}")

        with self.assertRaises(DeploymentExecutionError) as ctx:
            self.executor(failing_runner).deploy()
        self.assertEqual(ctx.exception.code, "command_failed")
        self.assertNotIn(secret, ctx.exception.message)
        self.assertNotIn("password=", ctx.exception.message)
        self.assertNotIn("token=", ctx.exception.message)

    def test_timeout_has_safe_error(self):
        def timeout_runner(args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=args, timeout=kwargs["timeout"])

        with self.assertRaises(DeploymentExecutionError) as ctx:
            self.executor(timeout_runner).deploy()
        self.assertEqual(ctx.exception.code, "command_timeout")
