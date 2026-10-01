"""
Daily research automation job (Tasks #8+10).

Runs daily at 08:00 IST via cron. Fetches trends/news from multiple sources
and generates 3-5 finance/tech/startup insights (150-200 words each).

Sources: HackerNews API, RSS feeds, tax estimator changes, SmartBudget alerts.
Output: research_insights table + Telegram digest to founder.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

try:
    import requests
except ImportError:
    requests = None

from .. import config, db
from . import logger as job_logger

log = job_logger.get_logger(__name__)


class NewsSource:
    """Base class for fetching news from different sources."""

    def fetch(self) -> list[dict]:
        """Return list of dicts with: title, description, url, source."""
        raise NotImplementedError


class HackerNewsSource(NewsSource):
    """Fetch top stories from Hacker News API."""

    API_URL = "https://hacker-news.firebaseio.com/v0"
    STORY_LIMIT = 10

    def fetch(self) -> list[dict]:
        """Fetch recent top stories from HackerNews."""
        if not requests:
            log.warning("requests library not available, skipping HackerNews fetch")
            return []

        try:
            # Get top story IDs
            resp = requests.get(
                f"{self.API_URL}/topstories.json",
                timeout=10
            )
            resp.raise_for_status()
            story_ids = resp.json()[:self.STORY_LIMIT]

            stories = []
            for story_id in story_ids:
                try:
                    story_resp = requests.get(
                        f"{self.API_URL}/item/{story_id}.json",
                        timeout=5
                    )
                    story_resp.raise_for_status()
                    story = story_resp.json()

                    if story.get("type") == "story" and story.get("url"):
                        stories.append({
                            "title": story.get("title", ""),
                            "description": f"{story.get('score', 0)} points, {story.get('descendants', 0)} comments",
                            "url": story.get("url", ""),
                            "source": "hackernews"
                        })
                except requests.RequestException as e:
                    log.warning(f"Failed to fetch HN story {story_id}: {e}")
                    continue

            return stories
        except (requests.RequestException, Exception) as e:
            log.error(f"HackerNews fetch failed: {e}")
            return []


class TechNewsSource(NewsSource):
    """Fetch from TechCrunch/Hacker News via RSS (fallback mock)."""

    def fetch(self) -> list[dict]:
        """Return curated tech stories (mock for now)."""
        # In production, use feedparser to parse RSS
        return [
            {
                "title": "AI and Infrastructure Growth Trends",
                "description": "Latest updates on foundation models, deployment costs, and enterprise adoption",
                "url": "https://example.com/ai-trends",
                "source": "tech_news"
            },
            {
                "title": "SaaS Profitability Metrics",
                "description": "Analysis of CAC, LTV, and churn across 500+ SaaS companies in 2024",
                "url": "https://example.com/saas-metrics",
                "source": "tech_news"
            }
        ]


class FinanceSource(NewsSource):
    """Extract insights from SmartBudget leaks and tax estimator changes."""

    def fetch(self) -> list[dict]:
        """Return finance-relevant insights (mock for now)."""
        return [
            {
                "title": "Personal Finance Optimization Insights",
                "description": "Analyzing spending patterns and budget recommendations from SmartBudget users",
                "url": "internal://smartbudget-insights",
                "source": "smartbudget"
            }
        ]


class InsightGenerator:
    """Generate detailed insights from raw news/data."""

    def __init__(self):
        self.sources = [
            HackerNewsSource(),
            TechNewsSource(),
            FinanceSource(),
        ]

    def fetch_all_news(self) -> list[dict]:
        """Fetch from all sources and combine."""
        all_news = []
        for source in self.sources:
            try:
                news = source.fetch()
                all_news.extend(news)
            except Exception as e:
                log.error(f"Error fetching from {source.__class__.__name__}: {e}")
                continue
        return all_news

    def categorize_insight(self, title: str, description: str) -> tuple[str, float]:
        """Classify insight into category and assign confidence score."""
        text = (title + " " + description).lower()

        # Simple keyword-based categorization
        if any(w in text for w in ["tax", "deduction", "irs", "filing"]):
            return "tax", 0.9
        elif any(w in text for w in ["security", "vulnerability", "breach", "hack"]):
            return "security", 0.85
        elif any(w in text for w in ["startup", "founder", "investment", "series"]):
            return "startup", 0.8
        elif any(w in text for w in ["ai", "llm", "model", "training", "inference"]):
            return "tech", 0.85
        elif any(w in text for w in ["finance", "budget", "expense", "income", "money"]):
            return "finance", 0.8
        else:
            return "tech", 0.6

    def generate_insight_content(self, title: str, description: str) -> str:
        """Convert raw news into 150-200 word insight summary."""
        category, _ = self.categorize_insight(title, description)

        # Template-based insight generation (in production, use Claude API)
        templates = {
            "finance": f"""
Finance Insight: {title}

Context: {description}

Key Takeaway: This development impacts personal and business financial planning
strategies. Organizations and individuals should monitor these trends for potential
optimization opportunities.

Action Items:
- Review current budget allocations
- Assess impact on cash flow projections
- Consider timing of planned financial decisions

Relevance Score: High for founders managing multiple businesses and personal finances.
""",
            "tech": f"""
Technology Insight: {title}

Context: {description}

Key Takeaway: This represents a significant shift in technical architecture, best
practices, or tooling within the technology sector. Early awareness enables better
decision-making on technology investments and team skill development.

Action Items:
- Evaluate how this affects current tech stack decisions
- Consider training or hiring implications
- Monitor adoption patterns in your industry

Relevance Score: Medium-High for technology-driven businesses.
""",
            "startup": f"""
Startup Insight: {title}

Context: {description}

Key Takeaway: Market dynamics and funding trends provide signals for business
strategy, market timing, and competitive positioning. Understanding the landscape
helps with business planning and investor conversations.

Action Items:
- Benchmark against similar companies
- Assess market demand signals
- Review pricing and positioning strategy

Relevance Score: High for founders raising capital or planning growth.
""",
            "tax": f"""
Tax & Compliance Insight: {title}

Context: {description}

Key Takeaway: Tax law changes or compliance updates can significantly impact
profitability and planning. Early awareness enables proactive strategy adjustments.

Action Items:
- Consult with tax professional about implications
- Review current tax planning strategy
- Update financial projections if needed

Relevance Score: Critical for business planning and bookkeeping.
""",
            "security": f"""
Security & Privacy Insight: {title}

Context: {description}

Key Takeaway: Security vulnerabilities, privacy concerns, and data protection
standards evolve constantly. Staying informed protects business data and customer
trust.

Action Items:
- Review current security practices
- Audit third-party vendor security
- Update incident response procedures

Relevance Score: Critical for any business handling customer data.
"""
        }

        return templates.get(category, templates["tech"]).strip()

    def generate_insights(self, news_items: list[dict], limit: int = 5) -> list[dict]:
        """Generate 3-5 insights from raw news items."""
        insights = []

        # Deduplicate by title
        seen_titles = set()
        unique_news = []
        for item in news_items:
            if item["title"] not in seen_titles:
                unique_news.append(item)
                seen_titles.add(item["title"])

        # Generate insights from top items
        for news in unique_news[:limit]:
            title = news["title"]
            desc = news.get("description", "")

            category, confidence = self.categorize_insight(title, desc)
            content = self.generate_insight_content(title, desc)

            # Clean up whitespace
            content = "\n".join(line.strip() for line in content.split("\n") if line.strip())

            insights.append({
                "source_type": news["source"],
                "source_title": title,
                "source_url": news.get("url", ""),
                "insight_title": title[:80],  # Truncate if needed
                "insight_content": content,
                "category": category,
                "confidence_score": confidence,
            })

        return insights

    def run(self, business_id: int = 1) -> dict:
        """Execute daily research job."""
        result = {
            "status": "started",
            "insights_fetched": 0,
            "insights_generated": 0,
            "errors": []
        }

        try:
            # Fetch news from all sources
            log.info("Fetching news from sources...")
            news_items = self.fetch_all_news()
            result["insights_fetched"] = len(news_items)

            if not news_items:
                log.warning("No news items fetched from any source")
                result["status"] = "partial"
                result["errors"].append("No news items fetched")
                return result

            # Generate insights
            log.info(f"Generating insights from {len(news_items)} news items...")
            insights = self.generate_insights(news_items, limit=5)
            result["insights_generated"] = len(insights)

            # Store in database
            with db.get_conn() as conn:
                for insight in insights:
                    try:
                        conn.execute(
                            """
                            INSERT INTO research_insights
                            (business_id, source_type, source_title, source_url,
                             insight_title, insight_content, category, confidence_score)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                business_id,
                                insight["source_type"],
                                insight["source_title"],
                                insight["source_url"],
                                insight["insight_title"],
                                insight["insight_content"],
                                insight["category"],
                                insight["confidence_score"],
                            )
                        )
                    except Exception as e:
                        log.error(f"Failed to store insight: {e}")
                        result["errors"].append(f"DB error: {str(e)}")
                        continue

            result["status"] = "success"
            log.info(f"Research job completed: {result['insights_generated']} insights generated")

            # Log job execution
            with db.get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO research_job_log
                    (run_date, status, insights_fetched, insights_generated, completed_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.now(timezone.utc).date().isoformat(),
                        result["status"],
                        result["insights_fetched"],
                        result["insights_generated"],
                        datetime.now(timezone.utc).isoformat()
                    )
                )

        except Exception as e:
            log.error(f"Research job failed: {e}", exc_info=True)
            result["status"] = "failed"
            result["errors"].append(str(e))

        return result
