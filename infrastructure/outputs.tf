# The page reads cloud settings from config.cloud.js. Destroy removes this file,
# and the page falls back to "Not configured".
resource "local_file" "web_config" {
  filename        = "${path.module}/../config.cloud.js"
  file_permission = "0644"
  content = <<-EOT
    // Written by Terraform (infrastructure/outputs.tf). Do not edit.
    window.INDO_CLOUD = ${jsonencode({
  baseUrl = aws_apigatewayv2_stage.default.invoke_url
  cognito = {
    domain      = "https://${aws_cognito_user_pool_domain.hosted_ui.domain}.auth.${local.region}.amazoncognito.com"
    clientId    = aws_cognito_user_pool_client.web.id
    redirectUri = var.redirect_uri
  }
})};
  EOT
}

output "api_url" {
  value = aws_apigatewayv2_stage.default.invoke_url
}

output "api_key_parameter" {
  value = aws_ssm_parameter.anthropic_api_key.name
}

output "user_pool_id" {
  value = aws_cognito_user_pool.users.id
}

output "hosted_ui_domain" {
  value = "https://${aws_cognito_user_pool_domain.hosted_ui.domain}.auth.${local.region}.amazoncognito.com"
}

output "next_steps" {
  value = <<-EOT
    1. Store the API key:   aws ssm put-parameter --name ${aws_ssm_parameter.anthropic_api_key.name} --type SecureString --overwrite --value "$ANTHROPIC_API_KEY"
    2. Create your user:    aws cognito-idp admin-create-user --user-pool-id ${aws_cognito_user_pool.users.id} --username you@example.com --user-attributes Name=email,Value=you@example.com Name=email_verified,Value=true
    3. Serve the page:      python3.13 local_server.py, open ${var.redirect_uri}, choose CLOUD, sign in.
    (linkedin-indo-aws connect does steps 1 and 2 for you.)
  EOT
}
