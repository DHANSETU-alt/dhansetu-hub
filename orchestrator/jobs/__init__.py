"""
Research automation and content publishing pipeline jobs (Tasks #8+10).

Jobs:
- research_daily: Fetch news/trends, generate 3-5 insights (08:00 IST daily)
- publish_content: Convert insights to social posts, emails, KB articles

Integration points:
- SmartBudget alerts → personal finance insights
- Tax estimator changes → educational content
- Daily digest → Telegram to founder
"""

from . import logger, publish_content, research_daily

__all__ = ["research_daily", "publish_content", "logger"]
