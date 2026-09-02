from django.test import SimpleTestCase

from .deployment_center import (
    DeploymentCenterError,
    FINAL_STATES,
    normalize_deployment_config,
    validate_transition,
)


class DeploymentCenterContractTests(SimpleTestCase):
    def test_missing_config_is_disabled(self):
        self.assertEqual(
            normalize_deployment_config(None),
            {"enabled": False, "environments": {}},
        )

    def test_local_development_is_normalized(self):
        config = normalize_deployment_config({
            "enabled": True,
            "environments": {
                "DEVELOPMENT": {
                    "executor": "LOCAL",
                    "strategy": "DOCKER_COMPOSE",
                    "working_directory": r"C:\apps\aprovaflow",
                }
            },
        })
        env = config["environments"]["DEVELOPMENT"]
        self.assertEqual(env["executor"], "local")
        self.assertEqual(env["strategy"], "docker_compose")
        self.assertEqual(env["compose_file"], "docker-compose.yml")

    def test_production_rejects_local_executor(self):
        with self.assertRaises(DeploymentCenterError) as ctx:
            normalize_deployment_config({
                "enabled": True,
                "environments": {
                    "PRODUCTION": {
                        "executor": "local",
                        "strategy": "docker_compose",
                        "working_directory": "/opt/app",
                    }
                },
            })
        self.assertEqual(ctx.exception.code, "local_executor_forbidden")

    def test_ssh_requires_safe_environment_variables(self):
        with self.assertRaises(DeploymentCenterError) as ctx:
            normalize_deployment_config({
                "enabled": True,
                "environments": {
                    "PRODUCTION": {
                        "executor": "ssh",
                        "strategy": "docker_compose",
                        "working_directory": "/opt/app",
                        "host": "app.example.org",
                        "username_env_var": "deploy-user",
                        "private_key_env_var": "DEPLOY_KEY",
                    }
                },
            })
        self.assertEqual(ctx.exception.code, "invalid_env_var")

    def test_plaintext_secret_fields_are_forbidden(self):
        with self.assertRaises(DeploymentCenterError) as ctx:
            normalize_deployment_config({
                "enabled": True,
                "environments": {
                    "TEST": {
                        "executor": "local",
                        "strategy": "docker_compose",
                        "working_directory": "/tmp/app",
                        "password": "segredo",
                    }
                },
            })
        self.assertEqual(ctx.exception.code, "plaintext_secret_forbidden")

    def test_working_directory_must_be_absolute(self):
        with self.assertRaises(DeploymentCenterError) as ctx:
            normalize_deployment_config({
                "enabled": True,
                "environments": {
                    "TEST": {
                        "executor": "local",
                        "strategy": "docker_compose",
                        "working_directory": "apps/aprovaflow",
                    }
                },
            })
        self.assertEqual(ctx.exception.code, "invalid_working_directory")

    def test_compose_file_rejects_parent_traversal(self):
        with self.assertRaises(DeploymentCenterError) as ctx:
            normalize_deployment_config({
                "enabled": True,
                "environments": {
                    "TEST": {
                        "executor": "local",
                        "strategy": "docker_compose",
                        "working_directory": "/tmp/app",
                        "compose_file": "../docker-compose.yml",
                    }
                },
            })
        self.assertEqual(ctx.exception.code, "invalid_compose_file")

    def test_unknown_environment_fails_closed(self):
        with self.assertRaises(DeploymentCenterError) as ctx:
            normalize_deployment_config({
                "enabled": True,
                "environments": {
                    "CUSTOM": {
                        "executor": "local",
                        "strategy": "docker_compose",
                        "working_directory": "/tmp/app",
                    }
                },
            })
        self.assertEqual(ctx.exception.code, "invalid_environment")

    def test_unknown_executor_fails_closed(self):
        with self.assertRaises(DeploymentCenterError) as ctx:
            normalize_deployment_config({
                "enabled": True,
                "environments": {
                    "TEST": {
                        "executor": "powershell",
                        "strategy": "docker_compose",
                        "working_directory": "/tmp/app",
                    }
                },
            })
        self.assertEqual(ctx.exception.code, "invalid_executor")

    def test_tolerant_mode_skips_stale_invalid_environment(self):
        config = normalize_deployment_config({
            "enabled": True,
            "environments": {
                "DEVELOPMENT": {
                    "executor": "local",
                    "strategy": "docker_compose",
                    "working_directory": "/tmp/app",
                },
                "LEGACY": {"executor": "custom"},
            },
        }, tolerant=True)
        self.assertTrue(config["enabled"])
        self.assertIn("DEVELOPMENT", config["environments"])
        self.assertNotIn("LEGACY", config["environments"])

    def test_tolerant_invalid_global_config_disables_deployment(self):
        self.assertEqual(
            normalize_deployment_config("legacy", tolerant=True),
            {"enabled": False, "environments": {}},
        )

    def test_valid_ssh_production(self):
        config = normalize_deployment_config({
            "enabled": True,
            "environments": {
                "PRODUCTION": {
                    "executor": "ssh",
                    "strategy": "docker_compose",
                    "working_directory": "/opt/aprovaflow",
                    "compose_file": "deploy/docker-compose.yml",
                    "host": "app.example.org",
                    "port": 2222,
                    "username_env_var": "DEPLOY_PROD_USERNAME",
                    "private_key_env_var": "DEPLOY_PROD_PRIVATE_KEY",
                    "known_hosts_env_var": "DEPLOY_PROD_KNOWN_HOSTS",
                }
            },
        })
        env = config["environments"]["PRODUCTION"]
        self.assertEqual(env["port"], 2222)
        self.assertEqual(env["compose_file"], "deploy/docker-compose.yml")

    def test_nominal_state_transitions(self):
        for current, target in [
            ("PLANNED", "VALIDATING"),
            ("VALIDATING", "READY"),
            ("READY", "RUNNING"),
            ("RUNNING", "VERIFYING"),
            ("VERIFYING", "SUCCEEDED"),
        ]:
            self.assertTrue(validate_transition(current, target))

    def test_failure_and_cancel_transitions(self):
        self.assertTrue(validate_transition("VALIDATING", "FAILED"))
        self.assertTrue(validate_transition("RUNNING", "FAILED"))
        self.assertTrue(validate_transition("VERIFYING", "FAILED"))
        self.assertTrue(validate_transition("PLANNED", "CANCELLED"))
        self.assertTrue(validate_transition("READY", "CANCELLED"))

    def test_final_states_are_immutable(self):
        self.assertEqual(FINAL_STATES, {"SUCCEEDED", "FAILED", "CANCELLED"})
        for state in FINAL_STATES:
            with self.assertRaises(DeploymentCenterError) as ctx:
                validate_transition(state, "PLANNED")
            self.assertEqual(ctx.exception.code, "invalid_transition")

    def test_invalid_transition_is_rejected(self):
        with self.assertRaises(DeploymentCenterError) as ctx:
            validate_transition("PLANNED", "SUCCEEDED")
        self.assertEqual(ctx.exception.code, "invalid_transition")
