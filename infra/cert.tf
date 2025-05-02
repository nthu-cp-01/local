resource "aws_iot_certificate" "lab_iot_certificate" {
  active = true
}

data "aws_iam_policy_document" "pubsub" {
  statement {
    effect    = "Allow"
    actions   = ["iot:*"]
    resources = ["*"]
  }
}

resource "aws_iot_policy" "pubsub" {
  name   = "PubSubToAnyTopic"
  policy = data.aws_iam_policy_document.pubsub.json
}

resource "aws_iot_policy_attachment" "lab_policy_attachment" {
  policy = aws_iot_policy.pubsub.name
  target = aws_iot_certificate.lab_iot_certificate.arn
}


