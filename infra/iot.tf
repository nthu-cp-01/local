resource "aws_iot_thing" "lab_thing" {
  name = "named_test"
}


data "aws_iot_endpoint" "lab_iot_endpoint" {}

output "aws_iot_endpoint" {
  value       = data.aws_iot_endpoint.lab_iot_endpoint.endpoint_address
  description = "Endpoint for IoT devices to connect."
}


# Export credentials
locals {
  parent_dir = abspath("${path.module}/..")
}

resource "local_sensitive_file" "aws_iot_certificate" {
  filename = "${local.parent_dir}/certificate.pem"
  content  = aws_iot_certificate.lab_iot_certificate.certificate_pem
}

resource "local_sensitive_file" "aws_iot_certificate_private" {
  filename = "${local.parent_dir}/id.pem"
  content  = aws_iot_certificate.lab_iot_certificate.private_key
}

resource "local_sensitive_file" "aws_iot_certificate_public" {
  filename = "${local.parent_dir}/id.pub"
  content  = aws_iot_certificate.lab_iot_certificate.public_key
}
