data "aws_caller_identity" "current" {}

locals {
  name = "ilaios-r01-canary"
  tags = {
    Application  = "ILAIOS"
    Environment  = lower(var.release_state)
    ManagedBy    = "OpenTofu"
    Release      = var.release_state == "PRODUCTION" ? "RELEASE.R03" : (var.release_state == "LIMITED" ? "RELEASE.R02" : "RELEASE.R01")
    ReleaseState = var.enable_canary ? var.release_state : "NOT_DEPLOYED"
  }
}

check "account_boundary" {
  assert {
    condition     = data.aws_caller_identity.current.account_id == "101180464425"
    error_message = "Wrong AWS account for staged ILAIOS release."
  }
}

resource "aws_ecr_repository" "runtime" {
  name                 = local.name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
}

resource "aws_vpc" "canary" {
  count                = var.enable_canary ? 1 : 0
  cidr_block           = "10.71.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
}

resource "aws_internet_gateway" "canary" {
  count  = var.enable_canary ? 1 : 0
  vpc_id = aws_vpc.canary[0].id
}

resource "aws_subnet" "runtime" {
  count                   = var.enable_canary ? 2 : 0
  vpc_id                  = aws_vpc.canary[0].id
  cidr_block              = cidrsubnet(aws_vpc.canary[0].cidr_block, 8, count.index)
  availability_zone       = "${var.aws_region}${count.index == 0 ? "a" : "b"}"
  map_public_ip_on_launch = true
}

resource "aws_route_table" "egress" {
  count  = var.enable_canary ? 1 : 0
  vpc_id = aws_vpc.canary[0].id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.canary[0].id
  }
}

resource "aws_route_table_association" "egress" {
  count          = var.enable_canary ? 2 : 0
  subnet_id      = aws_subnet.runtime[count.index].id
  route_table_id = aws_route_table.egress[0].id
}

resource "aws_security_group" "alb" {
  count       = var.enable_canary ? 1 : 0
  name_prefix = "${local.name}-alb-"
  vpc_id      = aws_vpc.canary[0].id
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.canary_ipv4_cidrs
  }
  egress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.canary[0].cidr_block]
  }
  lifecycle { create_before_destroy = true }
}

resource "aws_security_group" "runtime" {
  count       = var.enable_canary ? 1 : 0
  name_prefix = "${local.name}-runtime-"
  vpc_id      = aws_vpc.canary[0].id
  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb[0].id]
  }
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = [aws_vpc.canary[0].cidr_block]
  }
  egress {
    from_port   = 2049
    to_port     = 2049
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.canary[0].cidr_block]
  }
  lifecycle { create_before_destroy = true }
}

resource "aws_security_group" "efs" {
  count       = var.enable_canary ? 1 : 0
  name_prefix = "${local.name}-efs-"
  vpc_id      = aws_vpc.canary[0].id
  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.runtime[0].id]
  }
  lifecycle { create_before_destroy = true }
}

resource "aws_efs_file_system" "state" {
  count          = var.enable_canary ? 1 : 0
  encrypted      = true
  creation_token = local.name
}

resource "aws_efs_access_point" "state" {
  count          = var.enable_canary ? 1 : 0
  file_system_id = aws_efs_file_system.state[0].id
  posix_user {
    gid = 1000
    uid = 1000
  }
  root_directory {
    path = "/runtime"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "0700"
    }
  }
}

resource "aws_efs_mount_target" "state" {
  count           = var.enable_canary ? 2 : 0
  file_system_id  = aws_efs_file_system.state[0].id
  subnet_id       = aws_subnet.runtime[count.index].id
  security_groups = [aws_security_group.efs[0].id]
}

resource "aws_cloudwatch_log_group" "runtime" {
  count             = var.enable_canary ? 1 : 0
  name              = "/ilaios/r01/canary/runtime"
  retention_in_days = 14
}

data "aws_iam_policy_document" "ecs_assume" {
  count = var.enable_canary ? 1 : 0
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  count              = var.enable_canary ? 1 : 0
  name               = "${local.name}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume[0].json
}

resource "aws_iam_role_policy" "execution" {
  count = var.enable_canary ? 1 : 0
  role  = aws_iam_role.execution[0].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
    { Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"], Resource = aws_ecr_repository.runtime.arn },
    { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.runtime[0].arn}:*" },
    { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = var.control_plane_secret_arn }
  ] })
}

resource "aws_iam_role" "task" {
  count              = var.enable_canary ? 1 : 0
  name               = "${local.name}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume[0].json
}

resource "aws_iam_role_policy" "task" {
  count = var.enable_canary ? 1 : 0
  role  = aws_iam_role.task[0].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Action = ["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite"], Resource = aws_efs_file_system.state[0].arn
  }] })
}

resource "aws_ecs_cluster" "canary" {
  count = var.enable_canary ? 1 : 0
  name  = local.name
  tags  = local.tags
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "runtime" {
  count                    = var.enable_canary ? 1 : 0
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 1024
  execution_role_arn       = aws_iam_role.execution[0].arn
  task_role_arn            = aws_iam_role.task[0].arn
  tags                     = local.tags
  volume {
    name = "state"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.state[0].id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.state[0].id
        iam             = "ENABLED"
      }
    }
  }
  container_definitions = jsonencode([{
    name             = "runtime", image = "${aws_ecr_repository.runtime.repository_url}@${var.image_digest}", essential = true,
    user             = "1000:1000", readonlyRootFilesystem = true,
    portMappings     = [{ containerPort = 8080, hostPort = 8080, protocol = "tcp" }],
    environment      = local.runtime_environment,
    secrets          = [{ name = "ILAIOS_CONTROL_PLANE_TOKEN", valueFrom = var.control_plane_secret_arn }],
    mountPoints      = [{ sourceVolume = "state", containerPath = "/var/lib/ilaios", readOnly = false }],
    healthCheck      = { command = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/ready',timeout=2)\""], interval = 30, timeout = 5, retries = 3, startPeriod = 30 },
    logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.runtime[0].name, awslogs-region = var.aws_region, awslogs-stream-prefix = "runtime" } }
  }])
}

resource "aws_lb" "canary" {
  count                      = var.enable_canary ? 1 : 0
  name                       = local.name
  load_balancer_type         = "application"
  drop_invalid_header_fields = true
  security_groups            = [aws_security_group.alb[0].id]
  subnets                    = aws_subnet.runtime[*].id
}

resource "aws_lb_target_group" "runtime" {
  count                = var.enable_canary ? 1 : 0
  name                 = local.name
  port                 = 8080
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = aws_vpc.canary[0].id
  deregistration_delay = 30
  health_check {
    path    = "/health/ready"
    matcher = "200"
  }
}

resource "aws_lb_listener" "https" {
  count             = var.enable_canary ? 1 : 0
  load_balancer_arn = aws_lb.canary[0].arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.runtime[0].arn
  }
}

resource "aws_ecs_service" "runtime" {
  count           = var.enable_canary ? 1 : 0
  name            = local.name
  cluster         = aws_ecs_cluster.canary[0].id
  task_definition = aws_ecs_task_definition.runtime[0].arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  tags            = local.tags
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  network_configuration {
    subnets          = aws_subnet.runtime[*].id
    security_groups  = [aws_security_group.runtime[0].id]
    assign_public_ip = true
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.runtime[0].arn
    container_name   = "runtime"
    container_port   = 8080
  }
  depends_on = [aws_lb_listener.https, aws_efs_mount_target.state]
}
