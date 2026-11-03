variable "workshop_stack_base_name" {
  description = "Base name for every resource."
  type        = string
  default     = "workshop"
}

variable "python_bin" {
  description = "Interpreter used to package Lambda dependencies."
  type        = string
  default     = "python3.13"
}

variable "model" {
  description = "Claude model used by the LLM engine (provider anthropic)."
  type        = string
  default     = "claude-opus-5-5"
}

variable "app_origins" {
  description = "Origins allowed to call the API and to receive Cognito redirects (the page served by local_server.py)."
  type        = list(string)
  default     = ["http://localhost:8787", "http://127.0.0.1:8787"]
}

variable "redirect_uri" {
  description = "Cognito Hosted UI callback. Cognito allows plain http only for localhost."
  type        = string
  default     = "http://localhost:8787/"
}

variable "log_retention_days" {
  type    = number
  default = 7
}
