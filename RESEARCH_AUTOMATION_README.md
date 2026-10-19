# Research Automation & Content Publishing Pipeline (Tasks #8+10)

## Overview

Daily automation system that fetches news/trends from multiple sources, generates finance/tech/startup insights, and publishes to social platforms, email, and internal knowledge base.

**Key Components:**
- `orchestrator/jobs/research_daily.py` - Daily research job (fetch news, generate insights)
- `orchestrator/jobs/publish_content.py` - Publishing cascade (convert to Twitter, LinkedIn, email, KB)
- Database tables: `research_insights`, `published_content`, `research_job_log`
- API routes: `/api/research/*` for manual triggers and monitoring

## Database Schema

### research_insights
Stores generated insights from daily research.

```sql
id              - Primary key
business_id     - Reference to business
source_type     - hackernews | rss | tax_estimator | smartbudget
source_title    - Original article/source title
source_url      - Link to original source
insight_title   - 2-5 word summary
insight_content - 150-200 word detailed insight
category        - finance | tech | startup | tax | security | seo
confidence_score- 0.0-1.0 (importance/relevance)
status          - generated | reviewed | published | archived
reviewed_by     - User who reviewed (if applicable)
reviewed_at     - Review timestamp
published_at    - Publication timestamp
created_at      - Creation timestamp
```

### published_content
Tracks where and when insights were published.

```sql
id              - Primary key
business_id     - Reference to business
research_insight_id - Which insight was published
content_type    - twitter_post | linkedin_post | email | knowledge_base
platform        - twitter | linkedin | telegram | email | internal_kb
content         - Adapted copy for that platform
status          - queued | published | failed | archived
external_url    - Link to published content (if applicable)
error_message   - Error details (if status=failed)
published_at    - When it was published
```

### research_job_log
Execution history for monitoring and debugging.

```sql
id              - Primary key
run_date        - ISO-8601 date of run
status          - success | partial | failed
insights_fetched- Count of news items fetched
insights_generated - Count of insights generated
content_published - Count of content pieces published
error_summary   - Brief error description
started_at      - Job start timestamp
completed_at    - Job completion timestamp
```

## API Routes

### Fetch & Generate Insights
```bash
GET /api/research/fetch?business_id=1

Response:
{
  "status": "success|partial|failed",
  "insights_fetched": 13,
  "insights_generated": 5,
  "errors": []
}
```

### Preview Content (Dry Run)
```bash
GET /api/research/preview?business_id=1

Response:
{
  "status": "success",
  "insights_published": 5,
  "platforms": {
    "twitter": {"status": "preview", "tweet_count": 12},
    "linkedin": {"status": "preview", "char_count": 1847},
    "telegram": {"status": "preview", "insight_count": 5},
    "knowledge_base": {"status": "published"}
  }
}
```

### List Recent Insights
```bash
GET /api/research/insights?limit=10&status=generated

Response:
{
  "insights": [
    {
      "id": 5,
      "insight_title": "Title...",
      "category": "tech",
      "status": "generated",
      "confidence_score": 0.85,
      "created_at": "2026-10-01T09:56:45Z"
    }
  ],
  "total": 5
}
```

### Publish to Platforms
```bash
GET /api/research/publish?business_id=1

Response:
{
  "status": "success",
  "insights_published": 5,
  "platforms": {
    "twitter": {"status": "queued"},
    "linkedin": {"status": "queued"},
    "telegram": {"status": "published"},
    "knowledge_base": {"status": "published"}
  }
}
```

### Job Execution History
```bash
GET /api/research/job-log?limit=30

Response:
{
  "job_logs": [
    {
      "id": 2,
      "run_date": "2026-10-01",
      "status": "success",
      "insights_fetched": 13,
      "insights_generated": 5,
      "content_published": 5,
      "started_at": "2026-10-01T09:56:30Z",
      "completed_at": "2026-10-01T09:56:45Z"
    }
  ],
  "total": 2
}
```

## Cron Setup

Daily jobs run at:
- **08:00 IST (02:30 UTC)** - Research job (fetch news, generate insights)
- **08:30 IST (03:00 UTC)** - Publishing job (publish to platforms)

### Manual Cron Setup

Add to your crontab (`crontab -e`):

```bash
# Research automation job - Daily at 08:00 IST (02:30 UTC)
30 2 * * * cd /Users/apple/shakthi-os && python -c "from orchestrator.jobs import research_daily; research_daily.InsightGenerator().run()" >> logs/research_cron.log 2>&1

# Content publishing job - Daily at 08:30 IST (03:00 UTC)
0 3 * * * cd /Users/apple/shakthi-os && python -c "from orchestrator.jobs import publish_content; publish_content.ContentPublisher().run()" >> logs/research_cron.log 2>&1
```

Or run the setup script:
```bash
bash orchestrator/jobs/cron_setup.sh
```

## News Sources

### Currently Supported

1. **HackerNews API** - Top tech/startup stories
   - Fetches top 10 stories from HackerNews
   - Extracts title, score, discussion count

2. **Tech News (Mock)** - Tech trends and SaaS metrics
   - Curated tech/infrastructure stories
   - Expandable for RSS feeds

3. **Finance Source (Mock)** - SmartBudget and personal finance
   - Can integrate with SmartBudget alert system
   - User expense pattern analysis

### Adding New Sources

Create a class extending `NewsSource`:

```python
class MyNewsSource(NewsSource):
    def fetch(self) -> list[dict]:
        """Return list of dicts: title, description, url, source"""
        return [
            {
                "title": "...",
                "description": "...",
                "url": "...",
                "source": "my_source"
            }
        ]

# Then add to InsightGenerator.sources
```

## Insight Generation

Insights are generated using template-based summarization with:
- Automatic categorization (finance, tech, startup, tax, security, seo)
- Confidence scoring (0.0-1.0)
- 150-200 word detailed summaries
- Expandable for Claude API integration

### Categories

- **finance** - Personal finance, budgeting, investment tips
- **tech** - Software, infrastructure, AI/ML trends
- **startup** - Fundraising, market trends, business strategy
- **tax** - Tax law changes, deduction opportunities
- **security** - Security vulnerabilities, privacy concerns
- **seo** - Search trends, SEO best practices

## Content Adaptation

Insights are automatically adapted for each platform:

### Twitter (280 chars per tweet)
- Thread format for longer insights
- Emoji-enhanced headlines
- CTA with link

### LinkedIn (3000 char limit)
- Professional tone
- Detailed explanation
- Industry-relevant hashtags
- 500-1000 character sweet spot

### WhatsApp/Telegram
- Short, mobile-friendly format
- First 2-3 lines extracted
- Emoji indicators

### Email Newsletter
- HTML + plain text versions
- 3-5 insights per digest
- Styled cards with categories
- Preference link

### Knowledge Base
- Full article format
- Tagging system
- Internal-only flag
- Traceback to original insight

## Integration Points

### SmartBudget Alerts
When SmartBudget detects money leaks or unusual spending patterns:
- Generate "personal finance optimization" insight
- Suggest budget improvements
- Include in daily digest

### Tax Estimator Changes
When tax law updates or new deduction rules emerge:
- Generate "tax & compliance" insights
- Action items for tax planning
- CEO-priority flagged

### Telegram Digest
Daily founder digest includes:
- Top 3 insights from the day
- Categorized by relevance
- Links to full content
- Execution status

## Error Handling

### Retry Logic
- API failures: Automatic retry with exponential backoff
- Network timeouts: 5s per request, 10s per source
- Database errors: Transaction rollback, logged to error_log table

### Monitoring
- All errors logged to `logs/research/` directory
- Research job execution tracked in database
- Failed publishes marked with error_message
- Alert sent to founder on critical failures

## Logging

Logs are written to:
- **Console** - INFO level and above
- **File** - `logs/research/*.log` (10MB rolling, 5 backups)
- **Database** - `research_job_log` table

Log files:
- `logs/research/research_daily.log` - Fetch and generation
- `logs/research/publish_content.log` - Publishing execution
- `logs/research_cron.log` - Cron job output

## Testing

### Run Research Job Manually
```python
from orchestrator.jobs import research_daily
gen = research_daily.InsightGenerator()
result = gen.run(business_id=1)
print(f"Status: {result['status']}")
print(f"Generated: {result['insights_generated']} insights")
```

### Preview Content (Dry Run)
```python
from orchestrator.jobs import publish_content
pub = publish_content.ContentPublisher()
result = pub.run(business_id=1, dry_run=True)
# Shows what would be published without actually publishing
```

### Query Insights
```python
from orchestrator import db
with db.get_conn() as conn:
    insights = conn.execute(
        "SELECT * FROM research_insights WHERE status = ? ORDER BY created_at DESC",
        ["generated"]
    ).fetchall()
    for i in insights:
        print(f"{i['insight_title']}: {i['category']}")
```

## Performance Notes

- HackerNews fetch: ~5-10 seconds (10 stories)
- Insight generation: ~0.1-0.2 seconds per insight
- Content adaptation: ~0.05 seconds per platform
- Total runtime: ~10-15 seconds for full pipeline
- Database I/O: Non-blocking, uses connection pooling

## Future Enhancements

1. **Claude API Integration** - Use Claude for higher quality insight generation
2. **RSS Feed Parser** - feedparser integration for custom feeds
3. **Twitter/LinkedIn API** - Real publishing instead of queuing
4. **SmartBudget Integration** - Automatic expense pattern analysis
5. **A/B Testing** - Test different content formats and measure engagement
6. **Performance Metrics** - Track click-through rates, engagement per platform
7. **User Feedback** - Rate insights, feedback on published content
8. **Scheduling UI** - Dashboard to schedule research topics
9. **Email Delivery** - SMTP integration for newsletter delivery
10. **Analytics** - Trending insights, most shared content, reader engagement

## Troubleshooting

### Foreign Key Errors
**Problem:** "FOREIGN KEY constraint failed"
**Solution:** Ensure business with id=1 exists:
```python
from orchestrator import db
with db.get_conn() as conn:
    conn.execute("INSERT INTO businesses (id, tenant_id, name) VALUES (1, 'founder', 'Main')")
```

### No Insights Generated
**Problem:** `insights_generated: 0`
**Solutions:**
1. Check network connectivity (API calls timing out)
2. Verify requests library is installed
3. Check logs in `logs/research/` directory
4. Run with increased logging: `logging.basicConfig(level=logging.DEBUG)`

### Cron Job Not Running
**Problem:** Job doesn't execute at scheduled time
**Solutions:**
1. Verify crontab entry: `crontab -l`
2. Check cron log: `log stream --predicate 'process == "cron"'`
3. Ensure log directory exists: `mkdir -p logs/research`
4. Test manually: Run the Python command directly
5. Check environment variables are set (TELEGRAM_BOT_TOKEN, etc)

## Files Structure

```
orchestrator/
├── jobs/
│   ├── __init__.py              # Package init
│   ├── research_daily.py        # Fetch news, generate insights
│   ├── publish_content.py       # Convert to platforms
│   ├── logger.py                # Logging configuration
│   └── cron_setup.sh            # Cron setup helper
├── api.py                       # API routes (updated)
└── db.py                        # Database helpers (unchanged)

db/
└── schema.sql                   # Updated with research tables

logs/
└── research/
    ├── research_daily.log       # Daily job logs
    ├── publish_content.log      # Publishing logs
    └── research_cron.log        # Cron output
```

---

**Deployed:** 2026-10-01  
**Status:** ✅ Working - All tests passed  
**Next:** Queue first daily run for 08:00 IST tomorrow
