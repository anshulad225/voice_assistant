# Deployment Guide - Phase 1

## AWS Deployment (HIPAA-Eligible)

### Prerequisites
- AWS Account with HIPAA-eligible services enabled
- Signed BAA with AWS
- Domain name for production

### Architecture
- EC2 instance (or ECS/Fargate) in HIPAA-eligible region (us-east-1, us-west-2)
- RDS PostgreSQL with encryption at rest
- Application Load Balancer with SSL/TLS
- CloudWatch for logging and monitoring

### Environment Setup

1. Create RDS PostgreSQL instance:
```bash
# Enable encryption, automated backups, and VPC isolation
# Use db.t3.small or larger for production
```

2. Set environment variables:
```bash
export TWILIO_ACCOUNT_SID=your_sid
export TWILIO_AUTH_TOKEN=your_token
export OPENAI_API_KEY=your_key
export DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/dental_intake
export ENVIRONMENT=production
```

3. Initialize database:
```bash
python -m app.db.init_db
```

4. Run with production server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Security Checklist
- [ ] SSL/TLS enabled for all connections
- [ ] Database encryption at rest enabled
- [ ] VPC with private subnets for database
- [ ] Security groups restrict access
- [ ] CloudWatch logging enabled
- [ ] Secrets stored in AWS Secrets Manager
- [ ] Regular automated backups configured

### Monitoring
- CloudWatch metrics for latency tracking
- Error rate monitoring
- Database connection pool monitoring
- WebSocket connection tracking
