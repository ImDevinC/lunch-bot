provider "aws" {
  region  = "us-west-1"
  profile = "imdevinc"
}

terraform {
  backend "s3" {
    encrypt        = true
    bucket         = "imdevinc-tf-storage"
    dynamodb_table = "terraform-state-lock-dynamo"
    key            = "lunchbot"
    region         = "us-west-1"
    profile        = "imdevinc"
  }
}
