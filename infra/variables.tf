variable "name" {
  description = "Name prefix for every resource."
  type        = string
  default     = "nextera-demo"
}

variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Local AWS CLI profile to deploy with."
  type        = string
}

variable "db_instance_class" {
  description = "RDS instance class. t4g.micro is the cheapest Graviton option."
  type        = string
  default     = "db.t4g.micro"
}

variable "postgres_version" {
  description = "Major Postgres version; AWS resolves the latest minor."
  type        = string
  default     = "16"
}
