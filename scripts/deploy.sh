#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# AdaptivHealth Backend Deploy Script
#
# Builds, pushes to ECR, and triggers ECS rolling update.
# Supports both local dev builds and full AWS deployment.
#
# Usage:
#   ./scripts/deploy.sh              # Full deploy (build + push + ECS update)
#   ./scripts/deploy.sh --push-only  # Build and push image without ECS update
# ---------------------------------------------------------------------------

AWS_ACCOUNT="${AWS_ACCOUNT_ID:-991940085325}"
AWS_REGION="${AWS_REGION:-me-central-1}"
ECS_CLUSTER="${ECS_CLUSTER:-adaptivhealth-cluster}"
ECS_SERVICE="${ECS_SERVICE:-adaptivhealth-backend-service}"
IMAGE_NAME="adaptivhealth-backend"
ECR_URI="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${IMAGE_NAME}"

PUSH_ONLY=false
if [[ "${1:-}" == "--push-only" ]]; then
  PUSH_ONLY=true
fi

echo "=== AdaptivHealth Deploy ==="
echo "Region:  $AWS_REGION"
echo "Account: $AWS_ACCOUNT"
echo "Image:   $ECR_URI"
echo ""

# Step 1: ECR Login
echo "[1/5] Logging in to AWS ECR..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
    "${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Step 2: Build
echo "[2/5] Building Docker image..."
docker build -t "$IMAGE_NAME" .

# Step 3: Tag
echo "[3/5] Tagging image for ECR..."
docker tag "$IMAGE_NAME:latest" "$ECR_URI:latest"

# Step 4: Push
echo "[4/5] Pushing image to ECR..."
docker push "$ECR_URI:latest"

# Step 5: ECS Rolling Update
if [ "$PUSH_ONLY" = true ]; then
  echo "[5/5] Skipped ECS update (--push-only mode)"
else
  echo "[5/5] Triggering ECS service rolling update..."
  aws ecs update-service \
    --cluster "$ECS_CLUSTER" \
    --service "$ECS_SERVICE" \
    --force-new-deployment \
    --region "$AWS_REGION"

  echo ""
  echo "ECS rolling update started. Monitor progress with:"
  echo "  aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION --query 'services[0].deployments'"
fi

echo ""
echo "Deploy complete: $ECR_URI:latest"
