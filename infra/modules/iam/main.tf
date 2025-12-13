data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

########################################
# ECS Execution Role (pull image, send logs)
########################################

resource "aws_iam_role" "ecs_execution" {
  name               = "${var.name}-ecs-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn  = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

########################################
# ECS Task Role (application permissions)
########################################

resource "aws_iam_role" "ecs_task" {
  name               = "${var.name}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

# App permissions:
# - evidence bucket access
# - read DB password from SSM parameter (SecureString)
data "aws_iam_policy_document" "ecs_task_inline" {
  statement {
    sid     = "EvidenceBucketAccess"
    effect  = "Allow"
    actions = [
      "s3:ListBucket"
    ]
    resources = [
      var.evidence_bucket_arn
    ]
  }

  statement {
    sid     = "EvidenceObjectAccess"
    effect  = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:AbortMultipartUpload",
      "s3:ListBucketMultipartUploads",
      "s3:ListMultipartUploadParts"
    ]
    resources = [
      "${var.evidence_bucket_arn}/*"
    ]
  }

  statement {
    sid     = "ReadDbPasswordFromSSM"
    effect  = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters"
    ]
    resources = [
      var.db_password_ssm_arn
    ]
  }
}

resource "aws_iam_policy" "ecs_task_policy" {
  name   = "${var.name}-ecs-task-policy"
  policy = data.aws_iam_policy_document.ecs_task_inline.json
}

resource "aws_iam_role_policy_attachment" "ecs_task_attach" {
  role      = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_task_policy.arn
}
