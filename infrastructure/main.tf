data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  name   = "${var.workshop_stack_base_name}-indo"
  region = data.aws_region.current.region

  functions = {
    draft = {
      handler = "handlers.draft.handler"
      timeout = 30
      memory  = 512
      env = {
        API_KEY_PARAM    = aws_ssm_parameter.anthropic_api_key.name
        INDO_MODEL       = var.model
        INDO_SAMPLES_DIR = "/var/task/samples"
      }
    }
    posts = {
      handler = "handlers.posts.handler"
      timeout = 10
      memory  = 256
      env     = { TABLE_NAME = aws_dynamodb_table.posts.name }
    }
    authorizer = {
      handler = "handlers.authorizer.handler"
      timeout = 10
      memory  = 256
      env = {
        USER_POOL_ID  = aws_cognito_user_pool.users.id
        APP_CLIENT_ID = aws_cognito_user_pool_client.web.id
      }
    }
  }
}

# ---------- Data ----------

resource "aws_dynamodb_table" "posts" {
  name         = "${local.name}-posts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_sub"
  range_key    = "sk"

  attribute {
    name = "user_sub"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  tags = { Name = "${local.name}-posts" }
}

# Terraform stores only a placeholder. Set the real key out of band:
#   aws ssm put-parameter --name <output api_key_parameter> --type SecureString --overwrite --value "$ANTHROPIC_API_KEY"
resource "aws_ssm_parameter" "anthropic_api_key" {
  name        = "/${var.workshop_stack_base_name}/indo/anthropic-api-key"
  description = "Anthropic API key for the LinkedIn Indo draft Lambda"
  type        = "SecureString"
  value       = "REPLACE_ME"

  lifecycle {
    ignore_changes = [value]
  }

  tags = { Name = "${local.name}-anthropic-api-key" }
}
