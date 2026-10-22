# Task Manager API – Deployment Guide

Artifacts: `Dockerfile`, `docker-compose.yml`, `.dockerignore` (project root).

> The Dockerfile and compose file have **not** been built or run (Docker was not available when they were written). They were reviewed instruction by instruction only; gunicorn was not installed here, so the startup command was not run either. Do a first build and smoke test before relying on them.

## 1. Build the Docker image

```bash
cd task-manager
docker build -t task-manager:latest .
```

The image is based on `python:3.12-slim`. It installs `Flask` and `gunicorn` from `requirements.txt` (the `pytest` line is filtered out), copies only `app.py` and `task_manager/`, and runs as a non-root user.

## 2. Run locally with docker-compose

```bash
docker compose up --build        # start on http://localhost:8000
curl -i -X POST localhost:8000/tasks -H 'Content-Type: application/json' -d '{"title":"Buy milk"}'
curl -i localhost:8000/tasks
docker compose down              # stop (all tasks are lost: storage is in memory)
```

To run the tests, use a virtualenv on the host: `pip install -r requirements.txt && pytest tests/ -v`.

## 3. Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | Port gunicorn listens on inside the container. Set in the `Dockerfile` and `docker-compose.yml`. If you change it, change the port mappings, the ECS container port and the load balancer target port to match. |

No other configuration is needed: there is no database, no secrets and no authentication.

## 4. Deploy to AWS: ECS on Fargate (recommended)

### Choice: ECS Fargate, one task

The app keeps all tasks **in process memory** (`TaskRepository`) and the design assumes a single instance.

- **Lambda would give wrong behaviour.** AWS says Lambda functions should be treated as stateless: there is no guaranteed affinity to an execution environment, and Lambda can remove an environment at any time, so state must live in an external store such as DynamoDB or S3.[^lambda-state] Concurrent requests get separate environments, so users would see different, randomly vanishing task lists. Lambda is also positioned for on-demand, event-driven work, while ECS/Fargate suits long-running applications.[^choice]
- **Fargate fits.** It is serverless compute for containers and is described as ideal for long-running applications.[^choice] It runs the existing image unchanged as a long-lived process and can sit behind an Application Load Balancer using `ip` targets.[^fargate] Running exactly **one task** keeps the in-memory state coherent.

Consequences of this choice: data is lost on every deploy, restart or task replacement, and the service cannot scale out. If you need either, replace `TaskRepository` with a database-backed repository (DynamoDB or RDS). The layered design allows this without touching the routes or service. After that, Lambda or multiple Fargate tasks both become options.

### Steps (AWS CLI, region `us-east-1` as an example)

```bash
REGION=us-east-1
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REPO=task-manager
ECR=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com

# 1. Create the repository and push the image
aws ecr create-repository --repository-name $REPO --region $REGION
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR
docker build -t $REPO:latest .
docker tag $REPO:latest $ECR/$REPO:latest
docker push $ECR/$REPO:latest
```

2. **Cluster:** create an ECS cluster (Fargate capacity provider).
3. **Task definition:** `requiresCompatibilities: ["FARGATE"]`, `networkMode: awsvpc`, 0.25 vCPU / 0.5 GB is enough. Container port `8000`, image `$ECR/$REPO:latest`, env var `PORT=8000`. Use the `ecsTaskExecutionRole` so ECS can pull from ECR and write logs to CloudWatch.
4. **Load balancer:** create an Application Load Balancer, and a target group with target type **`ip`** (required for `awsvpc` tasks[^fargate]), port `8000`, health check path `/tasks` (returns `200` with `[]` when empty).
5. **Service:** create an ECS service with **desired count = 1**, launch type Fargate, attached to the target group. Security groups: ALB accepts 80/443 from the internet; the task accepts 8000 only from the ALB.
6. **HTTPS:** add an HTTPS listener with an ACM certificate (the API has no authentication, so restrict access with the security group, or put it behind a private ALB, if it should not be public).
7. **Deploys:** push a new image and run `aws ecs update-service --cluster ... --service ... --force-new-deployment`. For a single task, set the deployment's minimum healthy percent to 0 (or accept a brief overlap of two tasks that each have separate state).

## 5. Sources and how they were gathered

The Fargate-vs-Lambda choice was researched with the `aws-knowledge` MCP server (search results quoted below). The remaining guidance (ECR commands, task sizing, security groups, ACM/HTTPS, deployment percentages) is general knowledge and was not checked against the docs; verify it against current AWS documentation.

[^choice]: AWS Decision Guide, "AWS Fargate or AWS Lambda?": https://docs.aws.amazon.com/decision-guides/latest/decision-guides/fargate-or-lambda.html (Fargate "is ideal for long-running applications, microservices, or batch processing"; Lambda runs code as functions in response to events). See also "Use Amazon ECS": https://aws.amazon.com/modern-apps/recommendation-guide/serverless/amazon-ecs/ (Lambda is ideal for on-demand applications of 15 minutes or less).
[^lambda-state]: AWS Lambda Developer Guide, "Execution environment lifecycle": https://docs.aws.amazon.com/lambda/latest/dg/web-functions-env-lifecycle.html ("Lambda can remove an environment at any time... Persist important data to an external store such as DynamoDB or Amazon S3"). See also "Designing Lambda applications": https://docs.aws.amazon.com/lambda/latest/dg/concepts-application-design.html.
[^fargate]: Amazon ECS Developer Guide, "Architect for AWS Fargate for Amazon ECS": https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html (Fargate services support Application Load Balancers; target group type must be `ip`, not `instance`, for `awsvpc` tasks).
