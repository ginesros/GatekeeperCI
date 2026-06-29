# THIS IS AN EXAMPLE ONLY - DO NOT USE THESE CREDENTIALS IN PRODUCTION
resource "aws_s3_bucket" "financial_data" {
  bucket = "financial-data"
  
  # THIS IS AN EXAMPLE ONLY - DO NOT USE PUBLIC READ ACL IN PRODUCTION
  acl    = "public-read"
}

# THIS IS AN EXAMPLE ONLY - DO NOT USE OPEN SECURITY GROUPS IN PRODUCTION
resource "aws_security_group" "insecure_sg" {
  name        = "permitir_ssh_y_http_global"
  description = "Security group"

  #THIS IS AN EXAMPLE ONLY - DO NOT USE OPEN SECURITY GROUPS IN PRODUCTION
  ingress {
    description = "SSH desde cualquier lugar del mundo"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # THIS IS AN EXAMPLE ONLY - DO NOT USE OPEN SECURITY GROUPS IN PRODUCTION
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# THIS IS AN EXAMPLE ONLY - DO NOT USE UNENCRYPTED DATABASES WITH PLAINTEXT PASSWORDS IN PRODUCTION
resource "aws_db_instance" "bbdd" {
  allocated_storage    = 10
  engine               = "mysql"
  instance_class       = "db.t2.micro"
  username             = "admin"
  # THIS IS AN EXAMPLE ONLY - DO NOT USE UNENCRYPTED DATABASES WITH PLAINTEXT PASSWORDS IN PRODUCTION
  password             = "admin12345"
  parameter_group_name = "default.mysql5.7"
  skip_final_snapshot  = true
  # THIS IS AN EXAMPLE ONLY - DO NOT USE UNENCRYPTED DATABASES WITH PLAINTEXT PASSWORDS IN PRODUCTION
}