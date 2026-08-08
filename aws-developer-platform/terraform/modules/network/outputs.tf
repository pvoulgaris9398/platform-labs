output "vpc_id" { value = aws_vpc.this.id }
output "private_subnet_ids" { value = values(aws_subnet.private)[*].id }
output "api_security_group_id" { value = aws_security_group.api.id }
output "database_security_group_id" { value = aws_security_group.database.id }
