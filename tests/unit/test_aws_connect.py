import json
from types import SimpleNamespace

import pytest

import aws_connect


class FakeRun:
    """Stands in for aws_connect.run: records commands, answers by matching their start."""

    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls = []

    def __call__(self, cmd, *, env=None, cwd=None, capture=True, check=True):
        self.calls.append({"cmd": cmd, "env": env})
        for prefix, out in self.answers.items():
            if " ".join(cmd).startswith(prefix):
                out = out(cmd) if callable(out) else out
                return SimpleNamespace(returncode=0, stdout=out, stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_clean_env_drops_ambient_credentials_and_bundled_pythonpath(monkeypatch):
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE", "PYTHONPATH"):
        monkeypatch.setenv(name, "workshop")
    env = aws_connect.clean_env({"AWS_REGION": "eu-west-1"})
    assert not {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE", "PYTHONPATH"} & set(env)
    assert env["AWS_REGION"] == "eu-west-1"


def test_terraform_gets_the_signed_in_profiles_temporary_keys(monkeypatch):
    creds = {"AccessKeyId": "AKIA", "SecretAccessKey": "secret", "SessionToken": "tok"}
    fake = FakeRun({"aws configure export-credentials": json.dumps(creds)})
    monkeypatch.setattr(aws_connect, "run", fake)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "workshop")
    env = aws_connect.terraform_env("linkedin-indo", "eu-west-1")
    assert env["AWS_ACCESS_KEY_ID"] == "AKIA" and env["AWS_SESSION_TOKEN"] == "tok" and env["AWS_REGION"] == "eu-west-1"
    assert fake.calls[0]["cmd"][-4:] == ["--profile", "linkedin-indo", "--output", "json"]


def test_stack_dir_is_the_checkout_when_writable_else_user_data(tmp_path, monkeypatch):
    monkeypatch.delenv("INDO_STACK_DIR", raising=False)
    assert aws_connect.stack_dir() == aws_connect.ROOT
    monkeypatch.setattr(aws_connect, "ROOT", tmp_path / "readonly")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    assert aws_connect.stack_dir() == tmp_path / "data" / "linkedin-indo" / "aws"


def test_sync_stack_copies_code_and_samples(tmp_path, monkeypatch):
    src = tmp_path / "pkg"
    for rel in ("infrastructure/main.tf", "infrastructure/.terraform.lock.hcl", "src/indo_core/llm.py",
                "src/handlers/draft.py", "src/requirements-lambda.txt"):
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(rel)
    samples = tmp_path / "samples"
    samples.mkdir()
    (samples / "old-post.md").write_text("my voice")
    monkeypatch.setattr(aws_connect, "ROOT", src)
    monkeypatch.setenv("INDO_SAMPLES_DIR", str(samples))
    stack = tmp_path / "stack"
    aws_connect.sync_stack(stack)
    assert (stack / "infrastructure/.terraform.lock.hcl").exists() and (stack / "src/handlers/draft.py").exists()
    assert (stack / "src/requirements-lambda.txt").exists() and (stack / "samples/old-post.md").read_text() == "my voice"


def test_plan_summary_counts_each_action(monkeypatch, capsys):
    plan = {"resource_changes": [
        {"address": "aws_lambda_function.fn", "change": {"actions": ["create"]}},
        {"address": "aws_iam_role.fn", "change": {"actions": ["update"]}},
        {"address": "aws_dynamodb_table.posts", "change": {"actions": ["delete", "create"]}},
        {"address": "data.aws_region.current", "change": {"actions": ["read"]}},
        {"address": "aws_ssm_parameter.key", "change": {"actions": ["no-op"]}},
    ]}
    monkeypatch.setattr(aws_connect, "run", FakeRun({"terraform": json.dumps(plan)}))
    assert aws_connect.summarize_plan(aws_connect.ROOT, {}) == 3
    out = capsys.readouterr().out
    assert "1 to add, 1 to change, 0 to destroy, 1 to replace" in out and "data.aws_region" not in out


def test_apply_only_runs_the_saved_plan_after_confirmation(monkeypatch):
    plan = {"resource_changes": [{"address": "aws_lambda_function.fn", "change": {"actions": ["create"]}}]}
    fake = FakeRun({"terraform -chdir": lambda cmd: json.dumps(plan) if "show" in cmd else ""})
    monkeypatch.setattr(aws_connect, "run", fake)
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    assert aws_connect.plan_and_apply(aws_connect.ROOT, {}) is False
    assert not any("apply" in c["cmd"] for c in fake.calls)

    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    assert aws_connect.plan_and_apply(aws_connect.ROOT, {}) is True
    applied = [c["cmd"] for c in fake.calls if "apply" in c["cmd"]]
    assert applied and applied[-1][-2:] == ["tfplan", "-no-color"]
    assert any("-out=tfplan" in c["cmd"] for c in fake.calls)


def test_api_key_never_appears_on_a_command_line(monkeypatch):
    seen = {}

    def run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["file"] = json.loads(open(cmd[cmd.index("--cli-input-json") + 1].removeprefix("file://")).read())
        return SimpleNamespace(returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(aws_connect, "run", run)
    monkeypatch.setattr(aws_connect.getpass, "getpass", lambda prompt: "sk-ant-secret")
    aws_connect.store_api_key("linkedin-indo", "/workshop/indo/anthropic-api-key")
    assert "sk-ant-secret" not in " ".join(seen["cmd"])
    assert seen["file"] == {"Name": "/workshop/indo/anthropic-api-key", "Type": "SecureString",
                            "Overwrite": True, "Value": "sk-ant-secret"}


def test_connect_refuses_to_deploy_over_a_stack_in_another_account(tmp_path, monkeypatch):
    (tmp_path / "infrastructure").mkdir()
    monkeypatch.setenv("INDO_STACK_DIR", str(tmp_path))
    aws_connect.marker(tmp_path).write_text(json.dumps({"profile": "p", "region": "eu-west-1", "account": "111"}))
    monkeypatch.setattr(aws_connect, "check_tools", lambda: None)
    monkeypatch.setattr(aws_connect, "choose_region", lambda profile, saved: "eu-west-1")
    monkeypatch.setattr(aws_connect, "sign_in", lambda profile, region: {"Account": "222", "Arn": "arn:aws:iam::222:user/me"})
    monkeypatch.setattr(aws_connect, "terraform_env", lambda profile, region: {})
    monkeypatch.setattr(aws_connect, "deployed", lambda stack, env: True)
    with pytest.raises(aws_connect.ConnectError, match="deployed in account 111"):
        aws_connect.connect("p")


def test_unknown_command_prints_help(capsys):
    assert aws_connect.main(["frobnicate"]) == 2
    assert "connect" in capsys.readouterr().out
