provider "aws" {
  region = var.region

  # Credentials come from the environment so no dummy key pair is written down here.
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  endpoints {
    iam    = local.floci_endpoint
    lambda = local.floci_endpoint
    logs   = local.floci_endpoint
    s3     = local.floci_endpoint
    sqs    = local.floci_endpoint
    sts    = local.floci_endpoint
  }

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
    }
  }
}
