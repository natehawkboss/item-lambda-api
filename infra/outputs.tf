output "api_url" {
  description = "Public HTTPS endpoint for the API."
  value       = aws_lambda_function_url.api.function_url
}

output "docs_url" {
  description = "Swagger UI."
  value       = "${aws_lambda_function_url.api.function_url}docs"
}

output "seed_function_name" {
  description = "Invoke once after apply to create tables and load the CSVs."
  value       = aws_lambda_function.seed.function_name
}

output "db_endpoint" {
  description = "RDS endpoint (private — reachable only from the Lambda SG)."
  value       = aws_db_instance.this.endpoint
}
