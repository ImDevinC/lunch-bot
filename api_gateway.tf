resource "aws_api_gateway_rest_api" "lunch-bot-gw-api" {
  name        = "lunch-bot"
  description = "Allows for easy lunch lookup"
}

resource "aws_api_gateway_resource" "lunch-bot-gw-proxy-resource" {
  rest_api_id = "${aws_api_gateway_rest_api.lunch-bot-gw-api.id}"
  parent_id   = "${aws_api_gateway_rest_api.lunch-bot-gw-api.root_resource_id}"
  path_part   = "${aws_api_gateway_rest_api.lunch-bot-gw-api.name}"
}

resource "aws_api_gateway_method" "lunch-bot-gw-proxy-method" {
  rest_api_id   = "${aws_api_gateway_rest_api.lunch-bot-gw-api.id}"
  resource_id   = "${aws_api_gateway_resource.lunch-bot-gw-proxy-resource.id}"
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lunch-box-gw-lambda-integration" {
  rest_api_id = "${aws_api_gateway_rest_api.lunch-bot-gw-api.id}"
  resource_id = "${aws_api_gateway_method.lunch-bot-gw-proxy-method.resource_id}"
  http_method = "${aws_api_gateway_method.lunch-bot-gw-proxy-method.http_method}"

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "${aws_lambda_function.lunch-bot-lambda.invoke_arn}"
  content_handling        = "CONVERT_TO_TEXT"
}

resource "aws_api_gateway_deployment" "lunch-bot-gw-deployment" {
  depends_on = [
    "aws_api_gateway_integration.lunch-box-gw-lambda-integration",
  ]

  rest_api_id = "${aws_api_gateway_rest_api.lunch-bot-gw-api.id}"
  stage_name  = "prod"
}

output "url" {
  value = "${aws_api_gateway_deployment.lunch-bot-gw-deployment.invoke_url}"
}
