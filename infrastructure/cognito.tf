# Single-user pool: no self sign-up. Create your user with the command in the outputs.
resource "aws_cognito_user_pool" "users" {
  name                = "${local.name}-users"
  deletion_protection = "INACTIVE"
  username_attributes = ["email"]

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = false
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  tags = { Name = "${local.name}-users" }
}

resource "random_id" "domain" {
  byte_length = 4
}

resource "aws_cognito_user_pool_domain" "hosted_ui" {
  domain       = "${local.name}-${random_id.domain.hex}"
  user_pool_id = aws_cognito_user_pool.users.id
}

# Public client for the browser: authorization code + PKCE, no secret.
resource "aws_cognito_user_pool_client" "web" {
  name                                 = "${local.name}-web"
  user_pool_id                         = aws_cognito_user_pool.users.id
  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = [var.redirect_uri]
  logout_urls                          = [var.redirect_uri]
  explicit_auth_flows                  = ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  prevent_user_existence_errors        = "ENABLED"
  id_token_validity                    = 60
  access_token_validity                = 60
  token_validity_units {
    id_token     = "minutes"
    access_token = "minutes"
  }
}
