terraform {
  required_version = ">= 1.6"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

provider "aws" {
  region  = var.region
  profile = var.aws_profile

  default_tags {
    tags = {
      Project   = "nextera-demo"
      ManagedBy = "terraform"
    }
  }
}

# ---------------------------------------------------------------------------
# Network. The default VPC is used deliberately — this is a demo, and standing
# up a bespoke VPC would add cost and moving parts without changing the point.
# The database is private regardless: publicly_accessible = false, and its
# security group only accepts traffic from the Lambda's security group.
# ---------------------------------------------------------------------------

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_security_group" "lambda" {
  name        = "${var.name}-lambda"
  description = "Lambda egress to Postgres"
  vpc_id      = data.aws_vpc.default.id

  egress {
    description = "All egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name        = "${var.name}-db"
  description = "Postgres, reachable only from the Lambda security group"
  vpc_id      = data.aws_vpc.default.id

  # Security-group reference, not a CIDR block. Nothing outside this app's
  # Lambdas can open a connection, regardless of what else lives in the VPC.
  ingress {
    description     = "Postgres from Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }
}

# ---------------------------------------------------------------------------
# Database. The reason this exists rather than a SQLite file: data on a local
# disk makes the compute un-replaceable. Over the network, the Lambdas are
# disposable and can scale to any concurrency without owning any state.
# ---------------------------------------------------------------------------

resource "random_password" "db" {
  length  = 32
  special = false # keeps the URL free of characters needing escaping
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-db"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_db_instance" "this" {
  identifier     = "${var.name}-db"
  engine         = "postgres"
  engine_version = var.postgres_version
  instance_class = var.db_instance_class

  db_name  = "nextera"
  username = "nextera"
  password = random_password.db.result

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"
  storage_encrypted     = true

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false

  backup_retention_period = 1
  skip_final_snapshot     = true # demo: destroy cleanly without a snapshot
  deletion_protection     = false
  apply_immediately       = true
  auto_minor_version_upgrade = true
}

# ---------------------------------------------------------------------------
# IAM. Two distinct roles is the production shape; here one execution role is
# enough because the functions call no other AWS services.
# ---------------------------------------------------------------------------

resource "aws_iam_role" "lambda" {
  name = "${var.name}-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Logs to CloudWatch + permission to create the ENIs that VPC attachment needs.
resource "aws_iam_role_policy_attachment" "vpc_access" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# ---------------------------------------------------------------------------
# Compute. Same zip, two entrypoints: the API and a one-off seeder.
# ---------------------------------------------------------------------------

locals {
  lambda_zip = "${path.module}/../build/lambda.zip"

  environment = {
    # DATABASE_URL carries the password in plaintext in the function config.
    # The production answer is Secrets Manager with the Lambda reading the
    # secret at cold start; left direct here so the demo has no extra moving
    # parts and no extra monthly cost.
    DATABASE_URL = "postgresql+psycopg://${aws_db_instance.this.username}:${random_password.db.result}@${aws_db_instance.this.endpoint}/${aws_db_instance.this.db_name}"

    # Anything other than "local" makes app/db.py refuse to start on SQLite.
    ENVIRONMENT = "production"
    DEBUG       = "false"
  }
}

resource "aws_lambda_function" "api" {
  function_name    = var.name
  role             = aws_iam_role.lambda.arn
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)

  runtime       = "python3.12"
  architectures = ["arm64"] # Graviton: cheaper per millisecond
  handler       = "app.lambda_handler.handler"
  timeout       = 30
  memory_size   = 512

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment { variables = local.environment }

  depends_on = [aws_iam_role_policy_attachment.vpc_access]
}

resource "aws_lambda_function" "seed" {
  function_name    = "${var.name}-seed"
  role             = aws_iam_role.lambda.arn
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)

  runtime       = "python3.12"
  architectures = ["arm64"]
  handler       = "app.lambda_handler.seed_handler"
  timeout       = 120
  memory_size   = 512

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment { variables = local.environment }

  depends_on = [aws_iam_role_policy_attachment.vpc_access]
}

# A Function URL rather than API Gateway: built-in HTTPS, no per-request
# gateway cost, and no 29-second integration ceiling.
#
# authorization_type = "NONE" so the endpoint is open for anyone who wants to
# try it. "AWS_IAM" is the production setting — callers then sign requests with
# SigV4 against an IAM role and the service stores no credential at all.
resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"
}

# authorization_type = "NONE" only turns off IAM *authentication*. Lambda still
# checks its resource policy for authorization, and an unlisted caller is denied
# — so without this the URL answers 403 to everyone. Switching the URL to
# AWS_IAM makes this permission unnecessary and should be deleted with it.
resource "aws_lambda_permission" "public_function_url" {
  statement_id           = "AllowPublicFunctionUrlInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.api.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "seed" {
  name              = "/aws/lambda/${aws_lambda_function.seed.function_name}"
  retention_in_days = 7
}
