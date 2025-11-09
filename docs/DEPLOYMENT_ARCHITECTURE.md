# WRData Deployment Architecture
## Cloud Infrastructure Options & Cost Analysis

**Last Updated:** 2025-11-05
**Purpose:** Design production deployment strategy for wrdata freemium service

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌───────────────┐      ┌──────────────┐      ┌─────────────────┐  │
│  │   API Gateway │─────▶│  Load Balancer│─────▶│ API Servers (3+)│  │
│  │   (Kong/Nginx)│      │   (ALB/NLB)   │      │   FastAPI/Flask │  │
│  └───────────────┘      └──────────────┘      └─────────────────┘  │
│         │                                              │             │
│         │                                              ▼             │
│         │                                    ┌──────────────────┐   │
│         │                                    │  TimescaleDB     │   │
│         │                                    │  (PostgreSQL 16) │   │
│         │                                    │  + Hypertables   │   │
│         │                                    └──────────────────┘   │
│         │                                              │             │
│         ▼                                              │             │
│  ┌─────────────┐                                      │             │
│  │   Redis     │◀─────────────────────────────────────┘             │
│  │  (Caching)  │                                                     │
│  └─────────────┘                                                     │
│         │                                                             │
│         ▼                                                             │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │          Background Workers (Celery/RQ)                   │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│       │
│  │  │ Fetcher  │  │ Fetcher  │  │WebSocket │  │Aggregator││       │
│  │  │Worker #1 │  │Worker #2 │  │ Manager  │  │ Worker   ││       │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘│       │
│  └──────────────────────────────────────────────────────────┘       │
│         │                                                             │
│         ▼                                                             │
│  ┌─────────────────────────────────────────────────┐                │
│  │           External Data Providers                │                │
│  │  Polygon │ IEX │ Binance │ FRED │ Coinbase │... │                │
│  └─────────────────────────────────────────────────┘                │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Options Comparison

### Option 1: **AWS (Recommended for Scale)**

#### **Architecture:**
- **Compute:** ECS Fargate (serverless containers) or EKS (Kubernetes)
- **Database:** RDS PostgreSQL with TimescaleDB extension (or self-managed on EC2)
- **Cache:** ElastiCache Redis
- **Load Balancer:** Application Load Balancer (ALB)
- **Storage:** S3 for Parquet archives
- **Monitoring:** CloudWatch + Prometheus + Grafana

#### **Cost Estimate (Monthly):**

**Free Tier (MVP - 100 users):**
```
- t3.medium RDS (TimescaleDB) 2vCPU, 4GB RAM:     $60
- t3.small ElastiCache Redis:                      $25
- 2x t3.medium ECS Fargate (API servers):          $60
- 2x t3.small ECS Fargate (workers):               $30
- ALB:                                             $25
- S3 storage (1TB):                                $23
- Data transfer (500GB/mo):                        $45
- CloudWatch logs:                                 $10
───────────────────────────────────────────────────────
TOTAL:                                            ~$278/mo
```

**Pro Tier (1,000 users):**
```
- db.r6g.xlarge RDS (4vCPU, 32GB RAM):           $280
- cache.r6g.large ElastiCache (2 nodes):         $200
- 4x t3.large ECS Fargate (API servers):         $240
- 4x t3.medium ECS Fargate (workers):            $120
- ALB + Auto Scaling:                             $50
- S3 storage (10TB):                             $230
- Data transfer (5TB/mo):                        $450
- CloudWatch + Prometheus:                        $50
- Data provider licenses (Polygon+IEX):          $350
───────────────────────────────────────────────────────
TOTAL:                                         ~$1,970/mo

Revenue (1000 users @ $99/mo):                $99,000/mo
Margin:                                       ~$97,000/mo (98%)
```

**Enterprise Tier (10,000 users):**
```
- db.r6g.4xlarge RDS (16vCPU, 128GB):          $1,120
- cache.r6g.xlarge ElastiCache (3 nodes):        $900
- 10x c6g.xlarge ECS Fargate (API):            $1,500
- 8x t3.xlarge ECS Fargate (workers):            $960
- ALB + Auto Scaling:                            $100
- S3 storage (100TB):                          $2,300
- Data transfer (50TB/mo):                     $4,500
- CloudWatch + Prometheus + Grafana:             $200
- Data provider licenses:                        $350
───────────────────────────────────────────────────────
TOTAL:                                        ~$11,930/mo

Revenue (10,000 users @ $99/mo):              $990,000/mo
Margin:                                       ~$978,000/mo (99%)
```

#### **Pros:**
- ✅ Best for scaling (ECS/EKS auto-scaling)
- ✅ Managed services reduce ops burden
- ✅ Excellent monitoring (CloudWatch)
- ✅ Global CDN (CloudFront) if needed
- ✅ Strong security (IAM, VPC, encryption)

#### **Cons:**
- ❌ Can get expensive quickly
- ❌ Vendor lock-in
- ❌ Complexity (many services to manage)

---

### Option 2: **DigitalOcean (Recommended for MVP/Startups)**

#### **Architecture:**
- **Compute:** Kubernetes (DOKS) or Droplets
- **Database:** Managed PostgreSQL with TimescaleDB
- **Cache:** Managed Redis
- **Load Balancer:** DigitalOcean Load Balancer
- **Storage:** Spaces (S3-compatible)

#### **Cost Estimate (Monthly):**

**Free Tier MVP (100 users):**
```
- 2x 4GB/2vCPU Droplets (API + workers):        $48
- Managed PostgreSQL (4GB RAM, 2vCPU):          $60
- Managed Redis (2GB RAM):                      $30
- Load Balancer:                                $12
- Spaces storage (500GB):                        $5
───────────────────────────────────────────────────────
TOTAL:                                         ~$155/mo
```

**Pro Tier (1,000 users):**
```
- Kubernetes cluster (3x 8GB/4vCPU nodes):     $240
- Managed PostgreSQL (16GB RAM, 4vCPU):        $240
- Managed Redis (8GB RAM):                     $120
- Load Balancer:                                $12
- Spaces storage (5TB):                        $105
- Data provider licenses:                      $350
───────────────────────────────────────────────────────
TOTAL:                                       ~$1,067/mo

Revenue (1000 users @ $99/mo):                $99,000/mo
Margin:                                       ~$97,933/mo (99%)
```

#### **Pros:**
- ✅ **Best bang for buck** (50% cheaper than AWS)
- ✅ Simpler pricing, no surprise bills
- ✅ Great for startups (easy to understand)
- ✅ Managed database includes TimescaleDB support
- ✅ Excellent support

#### **Cons:**
- ❌ Less global coverage than AWS
- ❌ Fewer advanced features
- ❌ May need to migrate later if scaling past 10k users

---

### Option 3: **Hetzner (Cheapest Option)**

#### **Architecture:**
- **Compute:** Dedicated servers (bare metal)
- **Database:** Self-managed TimescaleDB on dedicated server
- **Cache:** Self-managed Redis
- **Load Balancer:** Self-managed (Nginx/HAProxy)

#### **Cost Estimate (Monthly):**

**Free Tier MVP (100 users):**
```
- 1x CCX23 (4vCPU, 16GB RAM, 160GB NVMe):       €26 (~$28)
- 1x CX21 (2vCPU, 4GB RAM - for Redis):          €5 (~$5)
───────────────────────────────────────────────────────
TOTAL:                                           ~$33/mo
```

**Pro Tier (1,000 users):**
```
- 2x CCX33 (8vCPU, 32GB RAM) - API/Workers:    €110 (~$120)
- 1x CCX53 (16vCPU, 64GB RAM) - Database:      €220 (~$240)
- 1x CX41 (4vCPU, 16GB RAM) - Redis:            €15 (~$16)
- Load balancer (LB11):                          €5 (~$5)
- Object storage (5TB):                         €25 (~$27)
- Data provider licenses:                       $350
───────────────────────────────────────────────────────
TOTAL:                                          ~$758/mo

Revenue (1000 users @ $99/mo):               $99,000/mo
Margin:                                      ~$98,242/mo (99.2%)
```

#### **Pros:**
- ✅ **Extremely cheap** (1/5th the cost of AWS)
- ✅ Bare metal performance
- ✅ No bandwidth charges (20TB+ included)
- ✅ Great for bootstrapping

#### **Cons:**
- ❌ EU-based (may have latency for US users)
- ❌ Less mature managed services
- ❌ More ops burden (self-manage everything)
- ❌ Limited global presence

---

### Option 4: **Hybrid (Best of Both Worlds)**

#### **Architecture:**
- **Hetzner:** Database (TimescaleDB) + Object Storage
- **DigitalOcean or AWS:** API servers + Workers (closer to users)
- **Cloudflare:** CDN + DDoS protection (free tier)

#### **Cost Estimate (Monthly):**

**Pro Tier (1,000 users):**
```
Hetzner:
- 1x CCX53 (Database):                          $240
- Object storage (5TB):                          $27

DigitalOcean:
- 3x 8GB Droplets (API servers):                $144
- 2x 4GB Droplets (Workers):                     $48
- Managed Redis (4GB):                           $60
- Load Balancer:                                 $12

Cloudflare (CDN/DDoS):                            $0 (free tier)
Data provider licenses:                         $350
───────────────────────────────────────────────────────
TOTAL:                                          ~$881/mo

Revenue (1000 users @ $99/mo):               $99,000/mo
Margin:                                      ~$98,119/mo (99.1%)
```

#### **Pros:**
- ✅ Cheap database hosting (Hetzner)
- ✅ Low latency API (multi-region with DO/AWS)
- ✅ Cloudflare CDN (free global edge)
- ✅ Best cost/performance ratio

#### **Cons:**
- ❌ More complex (managing multiple providers)
- ❌ Network egress between Hetzner↔DO can add cost

---

## Recommended Deployment Strategy

### **Phase 1: MVP (Months 1-3)**
- **Platform:** DigitalOcean
- **Why:** Simple, affordable, managed services
- **Cost:** ~$155/mo
- **Users:** 100-500

### **Phase 2: Pro Tier Launch (Months 4-6)**
- **Platform:** DigitalOcean or Hybrid (Hetzner DB + DO API)
- **Why:** Still cost-effective, proven scalability
- **Cost:** ~$750-1,000/mo
- **Users:** 500-2,000

### **Phase 3: Scale (Months 7+)**
- **Platform:** AWS or stay on hybrid
- **Why:** If >10k users, AWS auto-scaling is worth it
- **Cost:** $5,000-15,000/mo (but revenue is $500k-1M/mo)
- **Users:** 10,000+

---

## Infrastructure as Code (IaC)

### **Recommended Tools:**
- **Terraform** - Multi-cloud provisioning
- **Docker Compose** - Local development
- **Kubernetes** - Production orchestration (if needed)
- **GitHub Actions** - CI/CD

### **Terraform Example Structure:**
```
/terraform/
├── modules/
│   ├── timescaledb/
│   ├── redis/
│   ├── api-server/
│   └── workers/
├── environments/
│   ├── dev/
│   ├── staging/
│   └── production/
└── main.tf
```

---

## High Availability & Disaster Recovery

### **Database Backups:**
- **Automated daily snapshots** (TimescaleDB native backups)
- **Point-in-time recovery** (PITR) for last 7 days
- **Cross-region replication** (if on AWS: Multi-AZ)
- **Backup to S3/Spaces** (encrypted)

### **Redis:**
- **AOF (Append-Only File)** persistence enabled
- **Daily snapshots** to object storage
- **Optional: Redis Cluster** (3-node minimum for HA)

### **API Servers:**
- **Auto-scaling:** Min 2, Max 10 instances
- **Health checks:** /health endpoint (liveness/readiness)
- **Rolling deployments:** Zero-downtime updates

### **Workers:**
- **Queue-based architecture** (Celery or RQ)
- **Graceful shutdown** (finish tasks before stopping)
- **Dead letter queue** for failed tasks

---

## Security Best Practices

### **Network Security:**
- ✅ All services in private VPC (no public IPs except load balancer)
- ✅ Security groups: API (443), TimescaleDB (5432 internal only)
- ✅ Firewall rules: Whitelist IP ranges for admin access
- ✅ DDoS protection (Cloudflare or AWS Shield)

### **Data Security:**
- ✅ Encryption at rest (database volumes)
- ✅ Encryption in transit (TLS 1.3 for all connections)
- ✅ API key encryption in database (Fernet or AES-256)
- ✅ Secrets in vault (AWS Secrets Manager or HashiCorp Vault)

### **Application Security:**
- ✅ Rate limiting (per API key: 100 req/min free, 1000 req/min pro)
- ✅ Authentication: JWT tokens
- ✅ Authorization: RBAC (role-based access control)
- ✅ Input validation (Pydantic)
- ✅ OWASP Top 10 compliance

### **Compliance:**
- ✅ GDPR compliance (if serving EU users)
- ✅ SOC 2 Type II (if enterprise customers)
- ✅ Data residency options (US, EU regions)

---

## Monitoring & Observability

### **Metrics:**
- **Prometheus** - Metrics collection
- **Grafana** - Visualization
- **Key metrics:**
  - API latency (p50, p95, p99)
  - Database query time
  - Cache hit rate
  - Worker queue length
  - Data provider API errors
  - Disk usage / IOPS

### **Logging:**
- **Structured logging** (JSON format)
- **Centralized logs:** CloudWatch, Loki, or ELK stack
- **Log retention:** 30 days (hot), 1 year (cold storage)

### **Alerting:**
- **PagerDuty or Opsgenie** for critical alerts
- **Slack/Discord** for non-critical
- **Alerts:**
  - Database CPU >80%
  - API error rate >5%
  - Worker queue >10k tasks
  - Data provider API failures
  - Disk space <20%

### **Application Performance Monitoring (APM):**
- **Options:** Sentry, DataDog, New Relic
- **Track:** Slow queries, N+1 queries, memory leaks

---

## Cost Optimization Strategies

### **1. Reserved Instances**
- AWS: 1-year reserved = 30% discount
- DigitalOcean: Annual billing = 10% discount

### **2. Spot Instances (AWS)**
- Use for non-critical workers (70% discount)
- Not for API servers or database

### **3. Auto-Scaling**
- Scale down during off-hours (nights/weekends)
- Scale up during market hours (9:30am-4pm ET)

### **4. Data Compression**
- TimescaleDB compression (10x reduction)
- S3 Glacier for old data (90% cheaper)

### **5. CDN Caching**
- Cloudflare: Cache static responses (free)
- Reduce API server load by 50%+

### **6. Multi-Tenancy**
- Share database across all users
- Partition by user_id or tenant_id

---

## Scaling Milestones

| Users | Revenue/mo | Infra Cost | Margin | Platform |
|-------|------------|------------|--------|----------|
| 100 | $9,900 | $155 | 98.4% | DigitalOcean |
| 1,000 | $99,000 | $750 | 99.2% | DO or Hybrid |
| 5,000 | $495,000 | $3,000 | 99.4% | Hybrid |
| 10,000 | $990,000 | $12,000 | 98.8% | AWS |
| 50,000 | $4,950,000 | $60,000 | 98.8% | AWS Multi-Region |

**Key Insight:** Even at scale, infrastructure costs stay under 2% of revenue with proper optimization.

---

## CI/CD Pipeline

### **Development Workflow:**
```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│   Dev    │────▶│  GitHub  │────▶│   CI     │────▶│  Deploy  │
│ Local    │     │   PR     │     │  Tests   │     │  Staging │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                         │
                                         ▼
                                  ┌──────────┐
                                  │  Deploy  │
                                  │   Prod   │
                                  └──────────┘
```

### **GitHub Actions Pipeline:**
1. **On PR:** Run tests, linters, type checks
2. **On merge to main:** Deploy to staging
3. **On tag:** Deploy to production

---

## Next Steps

1. ✅ **Set up DigitalOcean account** (start with MVP)
2. ✅ **Create Terraform configs** for reproducible deploys
3. ✅ **Deploy staging environment** (test with free data)
4. ✅ **Set up monitoring** (Prometheus + Grafana)
5. ✅ **Load testing** (before launching Pro tier)
6. ⚠️ **Security audit** (penetration testing)
7. ⚠️ **Legal review** (ToS, privacy policy, data licensing)

---

## Recommended: DigitalOcean for MVP

**Why DigitalOcean?**
- $100/mo cost vs $300/mo on AWS
- Managed TimescaleDB (no ops burden)
- Simple pricing (no surprise bills)
- Easy to migrate to AWS later if needed
- Perfect for validating product-market fit

**Total MVP Cost:** ~$500/mo (infra + data licenses)
**Break-even:** 5-10 paying users
**Time to market:** 2-4 weeks

Let's build on DigitalOcean, then migrate to AWS/hybrid when we hit 5k users!
