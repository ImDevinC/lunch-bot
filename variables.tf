variable "subnet_ids" {
  type = "list"
}

variable "security_group_ids" {
  type = "list"
}

variable "logging_level" {
  default = "info"
}

variable "slack_signing_secret" {}
