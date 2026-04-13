# Adaptix Insight Deployment Guide

## Overview

This guide covers deploying Adaptix Insight to production environments, including AWS ECS, Docker, and local development.

## Prerequisites

### Required

- **Docker** 20.10+
- **Docker Compose** 2.0+ (for local development)
- **PostgreSQL** 16+ (or AWS RDS)
- **Python** 3.11+ (for local development without Docker)

### Recommended

- **AWS Account** (for ECS deployment)
- **AWS CLI** configured
- **Terraform** or AWS CDK (for infrastructure as code)

## Local Development Deployment

### Using Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone git@github.com:joshuawendorf21310/adaptix-insight.git
   cd adaptix-insight
   ```

2. **Start services**:
   ```bash
   docker-compose up -d
   ```

3. **Verify deployment**:
   ```bash
   curl http://localhost:8000/health
   ```

4. **View logs**:
   ```bash
   docker-compose logs -f backend
   ```

5. **Stop services**:
   ```bash
   docker-compose down
   ```

### Manual Local Deployment

1. **Set up PostgreSQL**:
   ```bash
   # Install PostgreSQL 16
   # Create database
   createdb adaptix_insight
   ```

2. **Set up Python environment**:
   ```bash
   cd backend
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

4. **Run migrations** (when implemented):
   ```bash
   alembic upgrade head
   ```

5. **Start application**:
   ```bash
   uvicorn core_app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Docker Deployment

### Building the Image

```bash
cd backend
docker build -t adaptix-insight:latest .
```

### Running the Container

```bash
docker run -d \
  --name adaptix-insight \
  -p 8000:8000 \
  -e ADAPTIX_INSIGHT_ENV=production \
  -e ADAPTIX_INSIGHT_DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db" \
  -e ADAPTIX_INSIGHT_DATABASE_URL_SYNC="postgresql://user:pass@host:5432/db" \
  adaptix-insight:latest
```

### Health Check

```bash
docker exec adaptix-insight curl http://localhost:8000/health
```

## AWS ECS Deployment

### Infrastructure Setup

1. **Create RDS PostgreSQL Instance**:
   - Engine: PostgreSQL 16.x
   - Instance class: db.t3.medium (minimum)
   - Multi-AZ: Yes (production)
   - Storage: 100 GB SSD
   - Backup retention: 7 days
   - Security group: Allow port 5432 from ECS tasks

2. **Create ECS Cluster**:
   ```bash
   aws ecs create-cluster --cluster-name adaptix-insight-prod
   ```

3. **Create ECR Repository**:
   ```bash
   aws ecr create-repository --repository-name adaptix-insight
   ```

### Building and Pushing Image

```bash
# Authenticate to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t adaptix-insight:latest ./backend

# Tag image
docker tag adaptix-insight:latest \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/adaptix-insight:latest

# Push image
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/adaptix-insight:latest
```

### Task Definition

Create `task-definition.json`:

```json
{
  "family": "adaptix-insight",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::<account-id>:role/adaptixInsightTaskRole",
  "containerDefinitions": [
    {
      "name": "adaptix-insight",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/adaptix-insight:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ADAPTIX_INSIGHT_ENV",
          "value": "production"
        },
        {
          "name": "ADAPTIX_INSIGHT_LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "ADAPTIX_INSIGHT_DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:adaptix-insight/db-url"
        },
        {
          "name": "ADAPTIX_INSIGHT_DATABASE_URL_SYNC",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:adaptix-insight/db-url-sync"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/adaptix-insight",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

Register task definition:

```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

### ECS Service

Create `service.json`:

```json
{
  "cluster": "adaptix-insight-prod",
  "serviceName": "adaptix-insight",
  "taskDefinition": "adaptix-insight",
  "desiredCount": 2,
  "launchType": "FARGATE",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ["subnet-xxx", "subnet-yyy"],
      "securityGroups": ["sg-xxx"],
      "assignPublicIp": "DISABLED"
    }
  },
  "loadBalancers": [
    {
      "targetGroupArn": "arn:aws:elasticloadbalancing:us-east-1:<account-id>:targetgroup/adaptix-insight/xxx",
      "containerName": "adaptix-insight",
      "containerPort": 8000
    }
  ],
  "healthCheckGracePeriodSeconds": 60
}
```

Create service:

```bash
aws ecs create-service --cli-input-json file://service.json
```

### Application Load Balancer

1. **Create Target Group**:
   - Protocol: HTTP
   - Port: 8000
   - Health check path: `/health`
   - Health check interval: 30 seconds

2. **Create ALB**:
   - Scheme: Internal (for internal APIs) or Internet-facing
   - Listeners: HTTP (80) or HTTPS (443)
   - Security groups: Allow inbound on 80/443

3. **Configure Listener Rules**:
   - Path pattern: `/api/insight/*` → Forward to target group
   - Path pattern: `/health` → Forward to target group

## Environment Variables

### Required

- `ADAPTIX_INSIGHT_DATABASE_URL` - Async PostgreSQL connection URL
- `ADAPTIX_INSIGHT_DATABASE_URL_SYNC` - Sync PostgreSQL URL for migrations

### Recommended

- `ADAPTIX_INSIGHT_ENV` - Environment (development, staging, production)
- `ADAPTIX_INSIGHT_LOG_LEVEL` - Log level (DEBUG, INFO, WARNING, ERROR)
- `ADAPTIX_INSIGHT_CORS_ORIGINS` - Comma-separated allowed origins

### Optional

See `backend/.env.example` for full list.

## Secrets Management

### AWS Secrets Manager

Store production secrets:

```bash
# Database URL
aws secretsmanager create-secret \
  --name adaptix-insight/db-url \
  --secret-string "postgresql+asyncpg://user:pass@rds-endpoint:5432/adaptix_insight"

# Database URL (sync)
aws secretsmanager create-secret \
  --name adaptix-insight/db-url-sync \
  --secret-string "postgresql://user:pass@rds-endpoint:5432/adaptix_insight"
```

Grant ECS task execution role access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:<account-id>:secret:adaptix-insight/*"
      ]
    }
  ]
}
```

## Monitoring

### CloudWatch Logs

ECS tasks log to CloudWatch Logs group `/ecs/adaptix-insight`.

View logs:

```bash
aws logs tail /ecs/adaptix-insight --follow
```

### CloudWatch Metrics

Monitor via AWS Console or CLI:

- ECS service CPU utilization
- ECS service memory utilization
- Target group healthy host count
- ALB request count and latency

### Custom Metrics

Application exports Prometheus metrics at `/metrics` (not publicly exposed).

For production monitoring, scrape metrics with Prometheus or use a CloudWatch agent.

## Auto-Scaling

### ECS Service Auto-Scaling

Create scaling policy:

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/adaptix-insight-prod/adaptix-insight \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/adaptix-insight-prod/adaptix-insight \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-scale-up \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

`scaling-policy.json`:

```json
{
  "TargetValue": 70.0,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
  },
  "ScaleInCooldown": 300,
  "ScaleOutCooldown": 60
}
```

## Database Migrations

(Alembic migrations implementation in progress)

When implemented:

```bash
# Run migrations in ECS task
aws ecs run-task \
  --cluster adaptix-insight-prod \
  --task-definition adaptix-insight-migrations \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}"
```

## Rollback Procedure

1. **Identify previous task definition**:
   ```bash
   aws ecs list-task-definitions --family-prefix adaptix-insight
   ```

2. **Update service to previous version**:
   ```bash
   aws ecs update-service \
     --cluster adaptix-insight-prod \
     --service adaptix-insight \
     --task-definition adaptix-insight:<previous-version>
   ```

3. **Monitor rollback**:
   ```bash
   aws ecs describe-services \
     --cluster adaptix-insight-prod \
     --services adaptix-insight
   ```

## Troubleshooting

### Service Won't Start

1. Check CloudWatch Logs for errors
2. Verify database connectivity from ECS tasks
3. Verify secrets are accessible
4. Check security group rules

### High CPU/Memory

1. Check CloudWatch metrics
2. Investigate slow queries (enable RDS Performance Insights)
3. Review application logs for errors
4. Consider scaling up task resources

### Failed Health Checks

1. Verify `/health` endpoint is accessible
2. Check database connection
3. Review health check configuration (timeout, interval)
4. Check application logs for startup errors

## Production Checklist

- [ ] RDS Multi-AZ enabled
- [ ] RDS automated backups enabled (7+ days)
- [ ] ECS service running in at least 2 AZs
- [ ] Auto-scaling configured
- [ ] ALB health checks configured
- [ ] CloudWatch alarms configured
- [ ] Secrets stored in Secrets Manager
- [ ] IAM roles follow least privilege
- [ ] Security groups restrict access
- [ ] Application logs flowing to CloudWatch
- [ ] Monitoring dashboards created
- [ ] Runbooks documented
- [ ] On-call rotation established
