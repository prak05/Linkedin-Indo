# Explicit log groups so `terraform destroy` removes them too.
resource "aws_cloudwatch_log_group" "fn" {
  for_each          = local.functions
  name              = "/aws/lambda/${local.name}-${each.key}"
  retention_in_days = var.log_retention_days
  tags              = { Name = "${local.name}-${each.key}-logs" }
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# One role per function, each limited to what that function touches.
resource "aws_iam_role" "fn" {
  for_each           = local.functions
  name               = "${local.name}-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = { Name = "${local.name}-${each.key}-role" }
}

data "aws_iam_policy_document" "fn" {
  for_each = local.functions

  statement {
    sid       = "WriteOwnLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.fn[each.key].arn}:*"]
  }

  dynamic "statement" {
    for_each = each.key == "draft" ? [1] : []
    content {
      sid       = "ReadApiKey"
      actions   = ["ssm:GetParameter"]
      resources = [aws_ssm_parameter.anthropic_api_key.arn]
    }
  }

  dynamic "statement" {
    for_each = each.key == "draft" ? [1] : []
    content {
      sid       = "DecryptApiKeyViaSsm"
      actions   = ["kms:Decrypt"]
      resources = ["arn:${data.aws_partition.current.partition}:kms:${local.region}:${data.aws_caller_identity.current.account_id}:key/*"]
      condition {
        test     = "StringEquals"
        variable = "kms:ViaService"
        values   = ["ssm.${local.region}.amazonaws.com"]
      }
      condition {
        test     = "StringEquals"
        variable = "kms:EncryptionContext:PARAMETER_ARN"
        values   = [aws_ssm_parameter.anthropic_api_key.arn]
      }
    }
  }

  dynamic "statement" {
    for_each = each.key == "posts" ? [1] : []
    content {
      sid       = "OwnPostsTable"
      actions   = ["dynamodb:PutItem", "dynamodb:Query"]
      resources = [aws_dynamodb_table.posts.arn]
    }
  }
}

resource "aws_iam_role_policy" "fn" {
  for_each = local.functions
  name     = "${local.name}-${each.key}"
  role     = aws_iam_role.fn[each.key].id
  policy   = data.aws_iam_policy_document.fn[each.key].json
}

resource "aws_lambda_function" "fn" {
  for_each         = local.functions
  function_name    = "${local.name}-${each.key}"
  role             = aws_iam_role.fn[each.key].arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = each.value.handler
  timeout          = each.value.timeout
  memory_size      = each.value.memory
  filename         = data.archive_file.code.output_path
  source_code_hash = data.archive_file.code.output_base64sha256
  layers           = [aws_lambda_layer_version.deps.arn]

  # No VPC: functions reach the internet (Anthropic API, event pages, Cognito JWKS) directly.

  environment {
    variables = each.value.env
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.fn[each.key].name
  }

  depends_on = [aws_iam_role_policy.fn]
  tags       = { Name = "${local.name}-${each.key}" }
}
