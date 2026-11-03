resource "aws_apigatewayv2_api" "http" {
  name          = "${local.name}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = var.app_origins
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["authorization", "content-type"]
    max_age       = 600
  }

  tags = { Name = "${local.name}-api" }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 20
    throttling_rate_limit  = 10
  }

  tags = { Name = "${local.name}-default-stage" }
}

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id                            = aws_apigatewayv2_api.http.id
  name                              = "${local.name}-cognito-id-token"
  authorizer_type                   = "REQUEST"
  authorizer_uri                    = aws_lambda_function.fn["authorizer"].invoke_arn
  authorizer_payload_format_version = "2.0"
  enable_simple_responses           = true
  identity_sources                  = ["$request.header.Authorization"]
  authorizer_result_ttl_in_seconds  = 300
}

resource "aws_apigatewayv2_integration" "fn" {
  for_each               = toset(["draft", "posts"])
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.fn[each.key].invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 30000
}

locals {
  routes = {
    "POST /drafts"        = { fn = "draft", auth = true }
    "POST /drafts/revise" = { fn = "draft", auth = true }
    "POST /posts"         = { fn = "posts", auth = true }
    "GET /posts"          = { fn = "posts", auth = true }
    "GET /health"         = { fn = "posts", auth = false }
  }
}

resource "aws_apigatewayv2_route" "r" {
  for_each           = local.routes
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = each.key
  target             = "integrations/${aws_apigatewayv2_integration.fn[each.value.fn].id}"
  authorization_type = each.value.auth ? "CUSTOM" : "NONE"
  authorizer_id      = each.value.auth ? aws_apigatewayv2_authorizer.cognito.id : null
}

resource "aws_lambda_permission" "api" {
  for_each      = toset(["draft", "posts", "authorizer"])
  statement_id  = "AllowHttpApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fn[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn = (each.key == "authorizer"
    ? "${aws_apigatewayv2_api.http.execution_arn}/authorizers/${aws_apigatewayv2_authorizer.cognito.id}"
  : "${aws_apigatewayv2_api.http.execution_arn}/*/*")
}
