# System Architecture - Phase 1

## High-Level Architecture

```
┌─────────────┐
│   Caller    │
│  (Patient)  │
└──────┬──────┘
       │ Dials clinic number
       ▼
┌─────────────────────────────────────────────────────────┐
│                    Twilio Platform                      │
│  ┌──────────────┐         ┌──────────────────────────┐ │
│  │ Phone Number │────────▶│   Media Streams          │ │
│  │  (Receives)  │         │   (WebSocket Audio)      │ │
│  └──────────────┘         └───────────┬──────────────┘ │
└────────────────────────────────────────┼────────────────┘
                                         │ μ-law audio
                                         │ (base64)
                                         ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Application (Python)               │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │         WebSocket Endpoint (/voice/stream)         │ │
│  │                                                     │ │
│  │  • Accepts Twilio connection                       │ │
│  │  • Buffers audio chunks (10 chunks)                │ │
│  │  • Manages bidirectional audio flow                │ │
│  └─────────────────┬──────────────────────────────────┘ │
│                    │                                     │
│  ┌─────────────────▼──────────────────────────────────┐ │
│  │           VoiceHandler (voice_handler.py)          │ │
│  │                                                     │ │
│  │  • Initializes Gemini session                      │ │
│  │  • Sends audio to Gemini                           │ │
│  │  • Receives audio responses                        │ │
│  │  • Extracts conversation data                      │ │
│  │  • Tracks: name, reason, patient_id, transcript    │ │
│  └─────────────────┬──────────────────────────────────┘ │
└────────────────────┼────────────────────────────────────┘
                     │
                     │ Audio + System Prompt
                     ▼
┌─────────────────────────────────────────────────────────┐
│           gemini-2.5-flash-native-audio-preview-12-2025
 API                   │
│                                                          │
│  Model: gemini-2.0-flash-exp                            │
│  Voice: Puck (warm, conversational)                     │
│  Format: Native audio (μ-law)                           │
│                                                          │
│  System Instruction:                                    │
│  • Greet caller                                         │
│  • Ask reason for call                                  │
│  • Collect name                                         │
│  • Ask about patient ID                                 │
│  • Acknowledge request                                  │
│  • Promise callback                                     │
│  • End call                                             │
│                                                          │
│  Guardrails:                                            │
│  • NEVER book appointments                              │
│  • NEVER answer clinical questions                      │
│  • NEVER discuss pricing                                │
│  • Deflect: "I'll have someone call you back"          │
└─────────────────────────────────────────────────────────┘
                     │
                     │ Audio response
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Application (Python)               │
│                                                          │
│  On Call End:                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │  1. Extract summary from VoiceHandler              │ │
│  │  2. Create IntakeRecord                            │ │
│  │  3. Save to PostgreSQL                             │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                PostgreSQL Database                      │
│                                                          │
│  Table: intake_records                                  │
│  ┌────────────────────────────────────────────────────┐ │
│  │ id              │ INTEGER (PK)                     │ │
│  │ call_sid        │ VARCHAR(100) UNIQUE              │ │
│  │ caller_name     │ VARCHAR(255)                     │ │
│  │ patient_id      │ VARCHAR(100)                     │ │
│  │ reason          │ TEXT                             │ │
│  │ transcript_snippet │ TEXT (500 chars)              │ │
│  │ created_at      │ TIMESTAMP                        │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                      │
                      │ Query via API
                      ▼
┌─────────────────────────────────────────────────────────┐
│              REST API Endpoints                         │
│                                                          │
│  GET  /health                                           │
│  GET  /intakes                                          │
│  GET  /intakes/{call_sid}                               │
│  POST /voice/incoming (Twilio webhook)                  │
└─────────────────────────────────────────────────────────┘
```

## Data Flow Sequence

### 1. Call Initiation
```
Caller → Twilio Number
Twilio → POST /voice/incoming
FastAPI → Returns TwiML with Stream URL
Twilio → Opens WebSocket to /voice/stream
```

### 2. Audio Streaming
```
Twilio → WebSocket: {"event": "start", "callSid": "CA123..."}
FastAPI → Initialize VoiceHandler
FastAPI → Start Gemini session

Loop (during call):
  Twilio → WebSocket: {"event": "media", "payload": "base64_audio"}
  FastAPI → Buffer audio (10 chunks)
  FastAPI → Send to Gemini
  Gemini → Process with system prompt
  Gemini → Return audio response
  FastAPI → WebSocket: {"event": "media", "payload": "response_audio"}
  Twilio → Play to caller
```

### 3. Call Termination
```
Twilio → WebSocket: {"event": "stop"}
FastAPI → Extract conversation summary
FastAPI → Create IntakeRecord
FastAPI → Save to PostgreSQL
FastAPI → Close WebSocket
```

## Component Details

### FastAPI Application
- **Framework**: FastAPI 0.109.0
- **Server**: Uvicorn with 4 workers
- **WebSocket**: Native FastAPI WebSocket support
- **Database**: SQLAlchemy ORM
- **Async**: Full async/await support

### VoiceHandler
- **Buffering**: 10 audio chunks (~200ms)
- **Format**: μ-law (G.711) at 8kHz
- **Encoding**: Base64 for WebSocket
- **Extraction**: Regex-based name/ID parsing
- **Transcript**: Maintains conversation history

### Gemini Integration
- **Model**: gemini-2.0-flash-exp
- **API**: google-generativeai SDK
- **Audio**: Native audio input/output
- **Voice**: Puck (configurable)
- **Latency**: ~900ms average

### Database
- **Engine**: PostgreSQL 14+
- **ORM**: SQLAlchemy 2.0
- **Connection**: Pool with 5 connections
- **Encryption**: At rest (AWS RDS)
- **Backups**: Automated daily

## Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Security Layers                      │
│                                                          │
│  1. Transport Layer                                     │
│     • TLS 1.3 for all connections                       │
│     • WSS (WebSocket Secure)                            │
│     • HTTPS only                                        │
│                                                          │
│  2. Authentication                                      │
│     • Twilio signature validation                       │
│     • API key authentication (Gemini)                   │
│     • Database credentials in Secrets Manager           │
│                                                          │
│  3. Data Protection                                     │
│     • Minimal PHI collection                            │
│     • Encryption at rest (database)                     │
│     • Encryption in transit (TLS)                       │
│     • No audio recording/storage                        │
│                                                          │
│  4. Access Control                                      │
│     • VPC isolation                                     │
│     • Security groups (least privilege)                 │
│     • IAM roles for AWS services                        │
│     • Database access restricted                        │
│                                                          │
│  5. Audit & Compliance                                  │
│     • CloudWatch logging                                │
│     • Call metadata tracking                            │
│     • Access logs                                       │
│     • HIPAA BAAs with all vendors                       │
└─────────────────────────────────────────────────────────┘
```

## Deployment Architecture (AWS)

```
┌─────────────────────────────────────────────────────────┐
│                      Internet                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Application Load Balancer                  │
│              (SSL/TLS Termination)                      │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────┐          ┌──────────────┐
│   EC2 / ECS  │          │   EC2 / ECS  │
│   Instance 1 │          │   Instance 2 │
│              │          │              │
│  FastAPI App │          │  FastAPI App │
└──────┬───────┘          └──────┬───────┘
       │                         │
       └────────────┬────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   RDS PostgreSQL      │
        │   (Private Subnet)    │
        │   • Encryption        │
        │   • Automated Backups │
        │   • Multi-AZ          │
        └───────────────────────┘
```

## Monitoring Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CloudWatch                           │
│                                                          │
│  Logs:                                                  │
│  • Application logs                                     │
│  • Error logs                                           │
│  • Access logs                                          │
│  • Database logs                                        │
│                                                          │
│  Metrics:                                               │
│  • Call volume                                          │
│  • Success rate                                         │
│  • Latency (p50, p95, p99)                             │
│  • Error rate                                           │
│  • Database connections                                 │
│  • CPU/Memory usage                                     │
│                                                          │
│  Alarms:                                                │
│  • Error rate > 1%                                      │
│  • Latency > 2s                                         │
│  • Database connections > 80%                           │
│  • Disk space < 20%                                     │
└─────────────────────────────────────────────────────────┘
                     │
                     │ Alerts
                     ▼
┌─────────────────────────────────────────────────────────┐
│                    SNS Topic                            │
│                                                          │
│  Subscribers:                                           │
│  • Email (team@example.com)                            │
│  • Slack webhook                                        │
│  • PagerDuty (optional)                                 │
└─────────────────────────────────────────────────────────┘
```

## Scalability Considerations

### Current Capacity
- **Concurrent Calls**: ~10-20 (single instance)
- **Database**: 100+ connections
- **API Quota**: 15 req/min (free tier)

### Scaling Strategy
1. **Horizontal Scaling**: Add more EC2/ECS instances
2. **Database**: Read replicas for reporting
3. **API Quota**: Upgrade Gemini tier
4. **Load Balancing**: ALB distributes traffic
5. **Auto-scaling**: Based on CPU/memory metrics

### Bottlenecks
- Gemini API quota (15 req/min free tier)
- Database connections (configurable pool)
- Network bandwidth (WebSocket)

## Cost Breakdown

### Per 1000 Calls/Month
- **Gemini API**: $50 (2 min avg)
- **Twilio**: $10 (phone + usage)
- **AWS EC2**: $30 (t3.medium)
- **AWS RDS**: $25 (db.t3.small)
- **AWS ALB**: $20
- **Data Transfer**: $5
- **Total**: ~$140/month

### Scaling Costs
- 10,000 calls/month: ~$600
- 100,000 calls/month: ~$5,500

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| First response | < 1.5s | ~1.3s |
| Average latency | < 1.0s | ~0.9s |
| Success rate | > 99% | TBD |
| Uptime | > 99.9% | TBD |
| Error rate | < 1% | TBD |

---

**Architecture Version**: 1.0
**Last Updated**: March 19, 2026
**Status**: Phase 1 Complete
