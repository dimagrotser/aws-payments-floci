# One bucket, two prefixes: decisions/ written by the processor, reports/ written by the
# daily reporter. Splitting them into two buckets would buy nothing here and would double
# the policy surface.

resource "aws_s3_bucket" "this" {
  bucket = var.name

  # This is a disposable local environment; make clean should not leave a bucket behind
  # that nothing can delete.
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
