# Production Deployment Checklist

## Pre-Deployment

### 1. Code Review
- [ ] All tests passing (`pytest tests/ -v`)
- [ ] No hardcoded credentials
- [ ] Error handling implemented
- [ ] Logging configured
- [ ] Code reviewed by team

### 2. Environment Setup
- [ ] Production `.env` file created
- [ ] All environment variables set
- [ ] Secrets stored in AWS Secrets Manager
- [ ] Database connection string verified

### 3. Database
- [ ] PostgreSQL instance created (RDS)
- [ ] Encryption at rest enabled
- [ ] Automated backups configured
- [ ] VPC security groups configured
- [ ] Database initialized (`python -m app.db.init_db`)
- [ ] Connection tested from app server

### 4. API Keys & Credentials
- [ ] Google AI API key obtained
- [ ] Twilio account SID and auth token
- [ ] Production phone number purchased
- [ ] API quotas checked and increased if needed

## Infrastructure Setup (AWS)

### 5. Compute
- [ ] EC2 instance launched (or ECS/Fargate)
- [ ] Instance in HIPAA-eligible region (us-east-1, us-west-2)
- [ ] Security groups configured (port 8000, 443)
- [ ] SSH key pair created and secured
- [ ] IAM roles configured

### 6. Networking
- [ ] VPC created with public/private subnets
- [ ] Application Load Balancer configured
- [ ] SSL/TLS certificate obtained (ACM)
- [ ] Domain name configured
- [ ] Health check endpoint configured

### 7. Security
- [ ] SSL/TLS enabled for all connections
- [ ] Security groups restrict unnecessary access
- [ ] Database in private subnet
- [ ] Secrets Manager for credentials
- [ ] CloudWatch logging enabled
- [ ] VPC Flow Logs enabled

## Application Deployment

### 8. Server Setup
- [ ] Python 3.11+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Application code deployed
- [ ] Environment variables loaded
- [ ] Database migrations run

### 9. Process Management
- [ ] Systemd service created (or supervisor)
- [ ] Auto-restart on failure configured
- [ ] Multiple workers configured (4+)
- [ ] Process monitoring enabled

### 10. Twilio Configuration
- [ ] Production phone number configured
- [ ] Webhook URL set to production domain
- [ ] HTTPS enforced
- [ ] Webhook tested with test call

## Monitoring & Logging

### 11. CloudWatch
- [ ] Application logs streaming to CloudWatch
- [ ] Error rate alarms configured
- [ ] Latency alarms configured
- [ ] Database connection alarms
- [ ] Disk space alarms

### 12. Metrics
- [ ] Call volume tracking
- [ ] Success rate monitoring
- [ ] Average latency tracking
- [ ] Database query performance
- [ ] API quota usage monitoring

### 13. Alerting
- [ ] SNS topic created for alerts
- [ ] Email notifications configured
- [ ] Slack/PagerDuty integration (optional)
- [ ] On-call rotation defined

## HIPAA Compliance

### 14. Legal & Compliance
- [ ] BAA signed with AWS
- [ ] BAA signed with Twilio
- [ ] BAA signed with Google Cloud (if required)
- [ ] Privacy policy updated
- [ ] Terms of service updated
- [ ] HIPAA risk assessment completed

### 15. Data Protection
- [ ] Encryption at rest enabled (database)
- [ ] Encryption in transit enabled (SSL/TLS)
- [ ] PHI minimization implemented
- [ ] Data retention policy defined
- [ ] Backup encryption enabled
- [ ] Access logs enabled

### 16. Access Control
- [ ] MFA enabled for all admin accounts
- [ ] Least privilege access implemented
- [ ] Regular access reviews scheduled
- [ ] Audit trail for all data access
- [ ] Password policy enforced

## Testing in Production

### 17. Smoke Tests
- [ ] Health endpoint responding (`/health`)
- [ ] Database connection working
- [ ] Test call completes successfully
- [ ] Intake record saved correctly
- [ ] API endpoints responding

### 18. Load Testing
- [ ] Concurrent call handling tested
- [ ] Database connection pool sized
- [ ] Memory usage monitored
- [ ] CPU usage monitored
- [ ] Auto-scaling configured (if needed)

### 19. Guardrail Validation
- [ ] Test booking attempt (should deflect)
- [ ] Test clinical question (should deflect)
- [ ] Test pricing question (should deflect)
- [ ] Verify deflection response correct

## Documentation

### 20. Operations
- [ ] Runbook created
- [ ] Incident response plan documented
- [ ] Escalation procedures defined
- [ ] Backup/restore procedures tested
- [ ] Disaster recovery plan documented

### 21. Team Training
- [ ] Team trained on system operation
- [ ] Access credentials distributed securely
- [ ] Monitoring dashboards shared
- [ ] On-call procedures reviewed

## Post-Deployment

### 22. Monitoring
- [ ] Monitor first 24 hours closely
- [ ] Check error rates
- [ ] Verify call quality
- [ ] Review latency metrics
- [ ] Check database performance

### 23. Optimization
- [ ] Review and tune database queries
- [ ] Optimize audio buffer size if needed
- [ ] Adjust worker count based on load
- [ ] Fine-tune Gemini parameters

### 24. Maintenance
- [ ] Schedule regular security updates
- [ ] Plan for dependency updates
- [ ] Schedule backup testing
- [ ] Plan for capacity reviews

## Success Metrics

### Key Performance Indicators
- [ ] Call completion rate > 95%
- [ ] Average latency < 1.5s
- [ ] Error rate < 1%
- [ ] Database uptime > 99.9%
- [ ] API success rate > 99%

### Business Metrics
- [ ] Intake records captured accurately
- [ ] Guardrails working 100%
- [ ] Cost per call within budget
- [ ] Customer satisfaction tracked

## Rollback Plan

### If Issues Arise
- [ ] Previous version tagged in git
- [ ] Rollback procedure documented
- [ ] Database migration rollback tested
- [ ] DNS/load balancer rollback ready
- [ ] Team knows rollback procedure

## Sign-Off

- [ ] Technical lead approval
- [ ] Security team approval
- [ ] Compliance team approval
- [ ] Product owner approval
- [ ] Operations team ready

---

**Deployment Date**: _____________

**Deployed By**: _____________

**Approved By**: _____________

**Notes**: _____________________________________________
