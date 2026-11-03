# CLAUDE.md

## Project context

- This is a serverless Users Service built with Terraform and Python.
- Infrastructure lives in `infrastructure/` and uses Terraform (not SAM or CDK).
- Lambda functions use the `python3.13` runtime on `arm64` and live under `src/`. The workstation is arm64 (Graviton), so dependencies packaged on it are arm64 builds.
- Run Python as `python3.13`, never plain `python3` (that is the operating system's own, older Python). This applies in every shell and script, including Terraform `local-exec` commands:
  - Packages: `python3.13 -m pip install --user` (no virtual environment)
  - Tests: `python3.13 -m pytest`
  - Lambda dependencies: `python3.13 -m pip install -t`
- Tests use pytest with moto for AWS mocking and live under `tests/unit/`.
- The base name for all resources is `"workshop"`. Use the Terraform variable `workshop_stack_base_name`.
- Never hardcode an AWS region. The AWS provider reads it from the `AWS_REGION` environment variable, and Terraform code references it as `data.aws_region.current.region`.
- Follow least-privilege IAM principles.
- Tag all Terraform resources with:
  - `Name`
  - `Environment = "Workshop"`
  - `Project = "Serverless with AI"`
- Before every `terraform apply`:
  1. Run `terraform plan -out=tfplan`.
  2. Summarize what it will add, change, and destroy.
  3. Apply that saved plan.
- Every resource is removed with `terraform destroy` at the end of the workshop. Never add `lifecycle { prevent_destroy = true }` blocks or deletion protection.
