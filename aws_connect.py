"""Connect LinkedIn Indo to your AWS account: sign in, then set up the CLOUD backend.

Run:  python3.13 aws_connect.py [connect|status|disconnect]
      (installed as: linkedin-indo-aws)

connect     Sign in with `aws login` (your AWS Console credentials, in the browser),
            show the account, then deploy infrastructure/ with Terraform, store the
            Anthropic API key in SSM (optional) and create your Cognito sign-in.
            The page's CLOUD target works as soon as this finishes.
disconnect  Remove everything with terraform destroy.
status      Show the signed-in account and whether the stack is deployed.

Terraform always runs as: plan -out=tfplan, a summary, your confirmation, apply tfplan.
"""

import getpass
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_PROFILE = "linkedin-indo"
# Credentials that would silently override the signed-in profile.
AWS_ENV_CREDS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_SECURITY_TOKEN", "AWS_PROFILE")
# The .deb launcher points Python at bundled packages; Terraform's pip step must not inherit that.
PYTHON_ENV = ("PYTHONPATH", "PYTHONNOUSERSITE")
STACK_FILES = ("infrastructure", "src/indo_core", "src/handlers", "src/requirements-lambda.txt")


class ConnectError(Exception):
    """A step failed. The message is shown to the user."""


# ---------- Small helpers ----------

def say(text=""):
    print(text, flush=True)


def confirm(prompt, default=False):
    hint = "[Y/n]" if default else "[y/N]"
    raw = input(f"{prompt} {hint}: ").strip().lower()
    return default if not raw else raw in ("y", "yes")


def clean_env(extra=None):
    env = {k: v for k, v in os.environ.items() if k not in AWS_ENV_CREDS + PYTHON_ENV}
    env.update(extra or {})
    return env


def run(cmd, *, env=None, cwd=None, capture=True, check=True):
    try:
        result = subprocess.run(cmd, env=env or clean_env(), cwd=cwd, text=True, check=False,
                                capture_output=capture)
    except FileNotFoundError:
        raise ConnectError(f"{cmd[0]} is not installed.") from None
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()[-1:] if capture else []
        raise ConnectError(f"`{' '.join(cmd[:3])}` failed{': ' + detail[0] if detail else ''}.")
    return result


def aws(profile, *args, check=True):
    """Run the AWS CLI as the signed-in profile, ignoring any credentials in the environment."""
    return run(["aws", *args, "--profile", profile, "--output", "json"], check=check)


# ---------- Stack location ----------

def stack_dir():
    """Where Terraform runs and keeps its state.

    From a source checkout: the checkout itself. From the .deb (read-only /usr/lib):
    a copy under ~/.local/share/linkedin-indo/aws, refreshed on each connect.
    """
    if os.environ.get("INDO_STACK_DIR"):
        return Path(os.environ["INDO_STACK_DIR"])
    if os.access(ROOT / "infrastructure", os.W_OK):
        return ROOT
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    return data / "linkedin-indo" / "aws"


def sync_stack(stack):
    """Copy the Terraform code and Lambda sources next to the state (packaged installs only)."""
    if stack == ROOT:
        return
    for rel in STACK_FILES:
        src, dst = ROOT / rel, stack / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            for f in src.iterdir():
                if f.is_file() and (f.suffix in (".tf", ".py") or f.name == ".terraform.lock.hcl"):
                    shutil.copy2(f, dst / f.name)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    # Lambda reads style samples from samples/; use the user's own.
    samples = Path(os.environ.get("INDO_SAMPLES_DIR") or ROOT / "samples")
    (stack / "samples").mkdir(exist_ok=True)
    if samples.is_dir():
        for f in samples.glob("*"):
            if f.suffix.lower() in (".md", ".txt"):
                shutil.copy2(f, stack / "samples" / f.name)


def marker(stack):
    return stack / "infrastructure" / ".indo-aws.json"


def read_marker(stack):
    try:
        return json.loads(marker(stack).read_text())
    except (OSError, ValueError):
        return {}


# ---------- Sign-in ----------

def check_tools():
    missing = [t for t in ("aws", "terraform") if not shutil.which(t)]
    if missing:
        raise ConnectError(f"Install {' and '.join(missing)} first (AWS CLI v2.32+ for `aws login`).")
    help_text = run(["aws", "login", "help"], check=False)
    if help_text.returncode != 0:
        raise ConnectError("This AWS CLI has no `aws login`. Update to AWS CLI v2.32 or later.")


def identity(profile):
    result = aws(profile, "sts", "get-caller-identity", check=False)
    return json.loads(result.stdout) if result.returncode == 0 else None


def choose_region(profile, saved):
    current = saved or run(["aws", "configure", "get", "region", "--profile", profile], check=False).stdout.strip() \
        or os.environ.get("AWS_REGION", "")
    while True:
        raw = input(f"AWS region to deploy to{f' (blank for {current})' if current else ' (for example eu-west-1)'}: ").strip()
        region = raw or current
        if region:
            return region
        say("  Enter a region.")


def sign_in(profile, region):
    run(["aws", "configure", "set", "region", region, "--profile", profile])
    who = identity(profile)
    if who and confirm(f"Already signed in as {who['Arn']}. Keep using it?", default=True):
        return who
    say("\nOpening the AWS sign-in page. Sign in with the AWS account you want to use.")
    remote = not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    cmd = ["aws", "login", "--profile", profile, "--region", region] + (["--remote"] if remote else [])
    run(cmd, capture=False)
    who = identity(profile)
    if not who:
        raise ConnectError("Sign-in did not produce working credentials. Try again.")
    return who


def terraform_env(profile, region):
    """Temporary keys from the signed-in profile, so Terraform uses exactly that account."""
    creds = json.loads(aws(profile, "configure", "export-credentials", "--format", "process").stdout)
    env = {"AWS_ACCESS_KEY_ID": creds["AccessKeyId"], "AWS_SECRET_ACCESS_KEY": creds["SecretAccessKey"],
           "AWS_REGION": region, "TF_IN_AUTOMATION": "1"}
    if creds.get("SessionToken"):
        env["AWS_SESSION_TOKEN"] = creds["SessionToken"]
    return clean_env(env)


# ---------- Terraform ----------

def python_bin():
    """An interpreter with pip, for packaging the arm64 Lambda layer (pip targets the platform explicitly)."""
    for candidate in (sys.executable, "python3.13", "python3"):
        if shutil.which(candidate) and run([candidate, "-m", "pip", "--version"], check=False).returncode == 0:
            return candidate
    raise ConnectError("No Python with pip was found. Install python3-pip.")


def tf(stack, env, *args, capture=True):
    return run(["terraform", f"-chdir={stack / 'infrastructure'}", *args, "-no-color"], env=env, capture=capture)


def summarize_plan(stack, env):
    plan = json.loads(tf(stack, env, "show", "-json", "tfplan").stdout)
    counts, lines = Counter(), []
    for rc in plan.get("resource_changes", []):
        actions = rc["change"]["actions"]
        if actions == ["no-op"] or actions == ["read"]:
            continue
        kind = "replace" if set(actions) == {"create", "delete"} else {"create": "add", "update": "change", "delete": "destroy"}[actions[0]]
        counts[kind] += 1
        lines.append(f"  {kind:8} {rc['address']}")
    say("\nTerraform plan:")
    say("\n".join(lines) or "  (no changes)")
    say(f"Summary: {counts['add']} to add, {counts['change']} to change, "
        f"{counts['destroy']} to destroy, {counts['replace']} to replace.")
    return sum(counts.values())


def plan_and_apply(stack, env, destroy=False, extra_vars=()):
    tf(stack, env, "init", "-input=false")
    args = ["plan", "-input=false", "-out=tfplan", *extra_vars] + (["-destroy"] if destroy else [])
    say("\nPlanning (this packages the Lambda code the first time)...")
    tf(stack, env, *args)
    if not summarize_plan(stack, env):
        return True
    if not confirm("Apply this plan?"):
        say("Nothing was changed.")
        return False
    say("Applying...")
    tf(stack, env, "apply", "-input=false", "tfplan", capture=False)
    return True


def outputs(stack, env):
    raw = json.loads(tf(stack, env, "output", "-json").stdout)
    return {k: v["value"] for k, v in raw.items()}


def deployed(stack, env):
    result = run(["terraform", f"-chdir={stack / 'infrastructure'}", "state", "list"], env=env, check=False)
    return result.returncode == 0 and bool(result.stdout.strip())


# ---------- After deploy ----------

def store_api_key(profile, parameter):
    say("\nThe LLM engine on CLOUD uses Claude through the Anthropic API. The Local ML engine needs no key.")
    key = getpass.getpass("Anthropic API key (blank to skip; input is hidden): ").strip()
    if not key:
        say("  Skipped. Cloud drafts will use the Local ML engine until a key is stored.")
        return
    # Pass the key in a private file so it never appears on a command line.
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        os.chmod(f.name, 0o600)
        json.dump({"Name": parameter, "Type": "SecureString", "Overwrite": True, "Value": key}, f)
    try:
        aws(profile, "ssm", "put-parameter", "--cli-input-json", f"file://{f.name}")
    finally:
        os.unlink(f.name)
    say("  Stored in SSM (encrypted).")


def create_user(profile, pool_id):
    email = input("\nEmail for your app sign-in (blank to skip): ").strip()
    if not email:
        return
    result = aws(profile, "cognito-idp", "admin-create-user", "--user-pool-id", pool_id, "--username", email,
                 "--user-attributes", f"Name=email,Value={email}", "Name=email_verified,Value=true", check=False)
    if result.returncode == 0:
        say(f"  Created. Cognito is emailing a temporary password to {email}.")
    elif "UsernameExists" in result.stderr:
        say("  That user already exists.")
    else:
        raise ConnectError(f"Could not create the user: {result.stderr.strip().splitlines()[-1]}")


# ---------- Commands ----------

def connect(profile):
    check_tools()
    stack = stack_dir()
    saved = read_marker(stack)
    region = choose_region(profile, saved.get("region"))
    who = sign_in(profile, region)
    say(f"\nSigned in to AWS account {who['Account']} as {who['Arn']} (region {region}).")
    if saved.get("account") and saved["account"] != who["Account"]:
        env = terraform_env(profile, region)
        if deployed(stack, env):
            raise ConnectError(f"The stack is deployed in account {saved['account']}. "
                               "Run `linkedin-indo-aws disconnect` with that account first.")
    if not confirm(f"Deploy LinkedIn Indo to account {who['Account']}?"):
        return 0
    sync_stack(stack)
    env = terraform_env(profile, region)
    marker(stack).write_text(json.dumps({"profile": profile, "region": region, "account": who["Account"]}))
    if not plan_and_apply(stack, env, extra_vars=[f"-var=python_bin={python_bin()}"]):
        return 0
    out = outputs(stack, env)
    store_api_key(profile, out["api_key_parameter"])
    create_user(profile, out["user_pool_id"])
    say(f"""
Connected. Cloud API: {out['api_url']}
Next: start the web UI (linkedin-indo-server, or python3.13 local_server.py), open
http://localhost:8787/, choose TARGET Cloud and sign in with the email above.
Remove everything later with: linkedin-indo-aws disconnect""")
    return 0


def disconnect(profile):
    check_tools()
    stack = stack_dir()
    saved = read_marker(stack)
    if not saved:
        say("Nothing is connected.")
        return 0
    profile = saved.get("profile", profile)
    who = identity(profile) or sign_in(profile, saved["region"])
    if who["Account"] != saved["account"]:
        raise ConnectError(f"Signed in to {who['Account']}, but the stack is in {saved['account']}. Sign in to that account.")
    env = terraform_env(profile, saved["region"])
    say(f"Removing LinkedIn Indo from account {saved['account']} ({saved['region']}).")
    if plan_and_apply(stack, env, destroy=True, extra_vars=[f"-var=python_bin={python_bin()}"]):
        if not deployed(stack, env):
            marker(stack).unlink(missing_ok=True)
            say("Disconnected. Every resource was removed.")
    return 0


def status(profile):
    stack = stack_dir()
    saved = read_marker(stack)
    profile = saved.get("profile", profile)
    who = identity(profile) if shutil.which("aws") else None
    say(f"Profile {profile}: " + (f"signed in to {who['Account']} as {who['Arn']}" if who else "not signed in"))
    if not saved:
        say("Stack: not deployed.")
    else:
        live = who and deployed(stack, terraform_env(profile, saved["region"]))
        say(f"Stack: {'deployed' if live else 'not deployed'} in account {saved['account']} ({saved['region']}), files in {stack}")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    command = argv[0] if argv else "connect"
    profile = os.environ.get("INDO_AWS_PROFILE") or DEFAULT_PROFILE
    commands = {"connect": connect, "disconnect": disconnect, "status": status}
    if command not in commands:
        say(__doc__)
        return 2
    try:
        return commands[command](profile)
    except ConnectError as e:
        print(f"\n{e}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        say("\nStopped.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
