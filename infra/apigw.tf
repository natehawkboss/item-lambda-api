# API Gateway HTTP API in front of the same Lambda.
#
# Why this exists alongside the Function URL: the Function URL returns 403 in
# this account even with authorization_type = NONE and a resource policy that
# allows public invoke. An HTTP API is not gated the same way, so it is the
# reliable public entrypoint here.
#
# The tradeoff, stated plainly: HTTP API integrations time out at 29 seconds.
# Irrelevant for this app — every endpoint is a small indexed query — but it is
# exactly the ceiling that would rule this out for heavy report generation.

resource "aws_apigatewayv2_api" "http" {
  name          = "${var.name}-http"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0" # what Mangum expects
}

# $default catches every method and path, so FastAPI does all the routing.
resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    # Machine clients retry; a public demo endpoint should not be free to hammer.
    throttling_burst_limit = 20
    throttling_rate_limit  = 10
  }
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

output "public_url" {
  description = "Public HTTPS endpoint (use this one)."
  value       = aws_apigatewayv2_stage.default.invoke_url
}
