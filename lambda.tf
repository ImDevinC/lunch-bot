resource "aws_lambda_function" "lunch-bot-lambda" {
  filename      = "${path.module}/function.zip"
  function_name = "lunch-bot"
  handler       = "lunch-bot.lambda_handler"
  runtime       = "python3.6"

  # source_code_hash = "${base64sha256(file("${path.module}/../function.zip"))}"
  source_code_hash = "${data.archive_file.lunch-bot-source.output_base64sha256}"
  role             = "${aws_iam_role.lunch-bot-lambda-exec.arn}"

  environment {
    variables {
      logging_level  = "${var.logging_level}"
      signing_secret = "${var.slack_signing_secret}"
    }
  }
}

resource "aws_iam_role" "lunch-bot-lambda-exec" {
  name = "lunch-bot-lambda"

  assume_role_policy = <<-EOF
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Effect": "Allow",
                "Sid": ""
            }
        ]
    }
    EOF
}

resource "aws_iam_policy" "lunch-bot-lambda-logging" {
  name        = "lunch-bot-logging"
  path        = "/"
  description = "IAM policy for logging from a lambda"

  policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource": "arn:aws:logs:*:*:*",
        "Effect": "Allow"
      }
    ]
  }
  EOF
}

resource "aws_iam_role_policy_attachment" "lunch-bot-lambda-logs" {
  role       = "${aws_iam_role.lunch-bot-lambda-exec.name}"
  policy_arn = "${aws_iam_policy.lunch-bot-lambda-logging.arn}"
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.lunch-bot-lambda.arn}"
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_deployment.lunch-bot-gw-deployment.execution_arn}/*"
}
