resource "aws_iam_role" "stepfunctions" {
  name = "secure-inspect-stepfunctions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "states.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "stepfunctions" {
  name = "secure-inspect-stepfunctions-policy"
  role = aws_iam_role.stepfunctions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDeliveryOptions",
          "logs:GetLogDeliveryOptions",
          "logs:UpdateLogDeliveryOptions",
          "logs:PutResourcePolicy"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_sfn_state_machine" "ct_pipeline" {
  name       = "secure-inspect-ct"
  role_arn   = aws_iam_role.stepfunctions.arn
  definition = jsonencode({
    Comment = "Continuous Training Pipeline"
    StartAt = "CheckNewData"
    States = {
      CheckNewData = {
        Type = "Pass"
        Next = "TrainModel"
      }
      TrainModel = {
        Type = "Pass"
        Next = "EvaluateModel"
      }
      EvaluateModel = {
        Type = "Pass"
        Next = "DecidePromotion"
      }
      DecidePromotion = {
        Type = "Choice"
        Choices = [
          {
            Variable = "$.passed_gate"
            BooleanEquals = true
            Next = "PromoteProduction"
          }
        ]
        Default = "StageForReview"
      }
      PromoteProduction = {
        Type = "Pass"
        Next = "Success"
      }
      StageForReview = {
        Type = "Pass"
        Next = "Success"
      }
      Success = {
        Type = "Succeed"
      }
    }
  })
}

output "stepfunctions_arn" {
  value = aws_sfn_state_machine.ct_pipeline.arn
}
