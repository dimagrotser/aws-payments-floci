# Everything that exists only because the target is Floci rather than AWS.
# Each value carries the difference it papers over.
locals {
  # AWS endpoints are per-service and have no global override, so every service used
  # below points here. Terraform runs inside the compose network (scripts/tf.sh), which
  # is why this is a container name and not localhost.
  floci_endpoint = "http://floci:4566"
}
