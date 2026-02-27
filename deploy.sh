#!/usr/bin/env bash
set -euo pipefail

AWS_ACCOUNT="991940085325"
AWS_REGION="me-central-1"
IMAGE_NAME="adaptivhealth-backend"
ECR_URI="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${IMAGE_NAME}"

echo "Logging in to AWS ECR..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
    "${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "Building Docker image..."
docker build -t "$IMAGE_NAME" .

echo "Tagging image for ECR..."
docker tag "$IMAGE_NAME:latest" "$ECR_URI:latest"

echo "Pushing image to ECR..."
docker push "$ECR_URI:latest"

echo "Deploy complete: $ECR_URI:latest"
