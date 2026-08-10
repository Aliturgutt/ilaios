output "ecr_repository_url" { value = aws_ecr_repository.runtime.repository_url }
output "canary_dns_target" { value = var.enable_canary ? aws_lb.canary[0].dns_name : null }
output "rollback_command" {
  value = var.enable_canary ? "aws ecs update-service --region eu-central-1 --cluster ${aws_ecs_cluster.canary[0].name} --service ${aws_ecs_service.runtime[0].name} --task-definition <PRIOR_IMMUTABLE_TASK_DEFINITION_ARN> --force-new-deployment" : null
}
