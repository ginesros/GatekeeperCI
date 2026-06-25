terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region     = "eu-west-1"
  # THIS IS AN EXAMPLE ONLY - DO NOT USE THESE CREDENTIALS IN PRODUCTION
  access_key = "AKIA1234567890EXAMPLE"
  secret_key = "abc123DEF456ghi789JKL012mno345PQR678STU"
}