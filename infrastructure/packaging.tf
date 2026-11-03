# Function code: indo_core + handlers + style samples, shared by all three functions.
locals {
  src_root     = "${path.module}/../src"
  samples_root = "${path.module}/../samples"
  code_files = merge(
    { for f in fileset(local.src_root, "{indo_core,handlers}/*.py") : f => "${local.src_root}/${f}" },
    { for f in fileset(local.samples_root, "*.{md,txt}") : "samples/${f}" => "${local.samples_root}/${f}" if lower(f) != "readme.md" },
  )
  layer_zip   = "${path.module}/build/layer.zip"
  lambda_reqs = "${local.src_root}/requirements-lambda.txt"
}

data "archive_file" "code" {
  type        = "zip"
  output_path = "${path.module}/build/code.zip"

  dynamic "source" {
    for_each = local.code_files
    content {
      filename = source.key
      content  = file(source.value)
    }
  }
}

# Dependencies: arm64 wheels for Python 3.13, fetched explicitly for the Lambda platform
# (the workstation's own architecture does not matter).
resource "terraform_data" "layer_build" {
  triggers_replace = [filesha256(local.lambda_reqs), var.python_bin]

  provisioner "local-exec" {
    working_dir = path.module
    command     = <<-EOT
      set -eu
      rm -rf build/layer build/layer.zip
      ${var.python_bin} -m pip install --quiet --target build/layer/python \
        --platform manylinux2014_aarch64 --platform manylinux_2_28_aarch64 --platform manylinux_2_34_aarch64 \
        --implementation cp --python-version 3.13 --only-binary=:all: \
        -r ${local.lambda_reqs}
      cd build/layer && ${var.python_bin} -m zipfile -c ../layer.zip python
    EOT
  }
}

resource "aws_lambda_layer_version" "deps" {
  layer_name               = "${local.name}-deps"
  filename                 = local.layer_zip
  compatible_runtimes      = ["python3.13"]
  compatible_architectures = ["arm64"]

  depends_on = [terraform_data.layer_build]

  lifecycle {
    replace_triggered_by = [terraform_data.layer_build]
  }
}
