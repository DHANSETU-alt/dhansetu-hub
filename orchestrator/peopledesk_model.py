"""
PeopleDesk — Customer Support Ticket System

Database schema and models for managing customer support tickets, comments,
and support team operations. Tickets are the core entity with threaded comments,
priority/status tracking, and support agent assignment.

Entities:
  - tickets: Core support ticket records with status and priority
  - ticket_comments: Threaded discussion (customer + support agent messages)
  - support_agents: Support team members with availability tracking
  - ticket_assignments: Track which agents are assigned to which tickets
  - ticket_metrics: SLA tracking (response time, resolution time)
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from . import db


# ============================================================================
# Data Models
# ============================================================================

class Ticket:
    """Support ticket entity"""
    __slots__ = ("id", "customer_id", "subject", "description", "priority", "status",
                 "assigned_to", "created_at", "updated_at", "resolved_at", "first_response_at")

    def __init__(
        self,
        id: str,
        customer_id: str,
        subject: str,
        description: str,
        priority: str = "medium",
        status: str = "open",
        assigned_to: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        resolved_at: Optional[str] = None,
        first_response_at: Optional[str] = None,
    ):
        self.id = id
        self.customer_id = customer_id
        self.subject = subject
        self.description = description
        self.priority = priority  # high, medium, low
        self.status = status  # open, in-progress, resolved
        self.assigned_to = assigned_to
        self.created_at = created_at or self._now()
        self.updated_at = updated_at or self._now()
        self.resolved_at = resolved_at
        self.first_response_at = first_response_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "subject": self.subject,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
            "first_response_at": self.first_response_at,
        }

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat() + "Z"


class TicketComment:
    """Comment in a ticket thread"""
    __slots__ = ("id", "ticket_id", "author_type", "author_id", "message", "created_at")

    def __init__(
        self,
        id: str,
        ticket_id: str,
        author_type: str,
        author_id: str,
        message: str,
        created_at: Optional[str] = None,
    ):
        self.id = id
        self.ticket_id = ticket_id
        self.author_type = author_type  # customer or support
        self.author_id = author_id
        self.message = message
        self.created_at = created_at or self._now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "author_type": self.author_type,
            "author_id": self.author_id,
            "message": self.message,
            "created_at": self.created_at,
        }

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat() + "Z"


class SupportAgent:
    """Support team member"""
    __slots__ = ("id", "name", "email", "availability_status", "assigned_tickets_count")

    def __init__(
        self,
        id: str,
        name: str,
        email: str,
        availability_status: str = "available",
        assigned_tickets_count: int = 0,
    ):
        self.id = id
        self.name = name
        self.email = email
        self.availability_status = availability_status  # available, busy, away
        self.assigned_tickets_count = assigned_tickets_count

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "availability_status": self.availability_status,
            "assigned_tickets_count": self.assigned_tickets_count,
        }


# ============================================================================
# Database Schema
# ============================================================================

PEOPLEDESK_SCHEMA = """
-- Support tickets table
CREATE TABLE IF NOT EXISTS peopledesk_tickets (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT DEFAULT 'medium' CHECK(priority IN ('high', 'medium', 'low')),
    status TEXT DEFAULT 'open' CHECK(status IN ('open', 'in-progress', 'resolved')),
    assigned_to TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    first_response_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(id),
    FOREIGN KEY (assigned_to) REFERENCES peopledesk_agents(id)
);

CREATE INDEX IF NOT EXISTS idx_tickets_customer ON peopledesk_tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON peopledesk_tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON peopledesk_tickets(priority);
CREATE INDEX IF NOT EXISTS idx_tickets_assigned ON peopledesk_tickets(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tickets_created ON peopledesk_tickets(created_at);

-- Ticket comments/thread
CREATE TABLE IF NOT EXISTS peopledesk_comments (
    id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    author_type TEXT NOT NULL CHECK(author_type IN ('customer', 'support')),
    author_id TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES peopledesk_tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_comments_ticket ON peopledesk_comments(ticket_id);
CREATE INDEX IF NOT EXISTS idx_comments_author ON peopledesk_comments(author_id);
CREATE INDEX IF NOT EXISTS idx_comments_created ON peopledesk_comments(created_at);

-- Support agents
CREATE TABLE IF NOT EXISTS peopledesk_agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    availability_status TEXT DEFAULT 'available' CHECK(availability_status IN ('available', 'busy', 'away')),
    assigned_tickets_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_agents_availability ON peopledesk_agents(availability_status);
CREATE INDEX IF NOT EXISTS idx_agents_assigned_count ON peopledesk_agents(assigned_tickets_count);

-- SLA metrics for tickets
CREATE TABLE IF NOT EXISTS peopledesk_metrics (
    id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    response_time_minutes INTEGER,
    resolution_time_minutes INTEGER,
    first_response_at TIMESTAMP,
    resolved_at TIMESTAMP,
    sla_status TEXT DEFAULT 'in-progress' CHECK(sla_status IN ('on-track', 'at-risk', 'breached')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES peopledesk_tickets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_metrics_ticket ON peopledesk_metrics(ticket_id);
CREATE INDEX IF NOT EXISTS idx_metrics_sla_status ON peopledesk_metrics(sla_status);
"""


# ============================================================================
# Database Operations
# ============================================================================

def create_ticket(
    customer_id: str,
    subject: str,
    description: str,
    priority: str = "medium",
) -> Ticket:
    """Create a new support ticket"""
    ticket_id = f"ticket_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{customer_id[:8]}"
    ticket = Ticket(
        id=ticket_id,
        customer_id=customer_id,
        subject=subject,
        description=description,
        priority=priority,
        status="open",
    )

    with db.get_conn() as conn:
        conn.execute(
            """
            INSERT INTO peopledesk_tickets
            (id, customer_id, subject, description, priority, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket.id,
                ticket.customer_id,
                ticket.subject,
                ticket.description,
                ticket.priority,
                ticket.status,
                ticket.created_at,
                ticket.updated_at,
            ),
        )
        conn.commit()

    return ticket


def get_ticket(ticket_id: str) -> Optional[dict]:
    """Get ticket by ID"""
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM peopledesk_tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
    return dict(row) if row else None


def list_customer_tickets(customer_id: str, status: Optional[str] = None, limit: int = 50) -> List[dict]:
    """List tickets for a customer"""
    with db.get_conn() as conn:
        query = "SELECT * FROM peopledesk_tickets WHERE customer_id = ?"
        params = [customer_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def list_all_tickets(status: Optional[str] = None, priority: Optional[str] = None, limit: int = 100) -> List[dict]:
    """List all tickets (for support team dashboard)"""
    with db.get_conn() as conn:
        query = "SELECT * FROM peopledesk_tickets WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if priority:
            query += " AND priority = ?"
            params.append(priority)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def update_ticket_status(ticket_id: str, status: str, assigned_to: Optional[str] = None) -> bool:
    """Update ticket status and optionally assign"""
    with db.get_conn() as conn:
        if assigned_to:
            conn.execute(
                """
                UPDATE peopledesk_tickets
                SET status = ?, assigned_to = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, assigned_to, ticket_id),
            )
        else:
            conn.execute(
                """
                UPDATE peopledesk_tickets
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, ticket_id),
            )

        if status == "resolved":
            conn.execute(
                "UPDATE peopledesk_tickets SET resolved_at = CURRENT_TIMESTAMP WHERE id = ?",
                (ticket_id,),
            )

        conn.commit()
    return True


def add_comment(ticket_id: str, author_type: str, author_id: str, message: str) -> TicketComment:
    """Add a comment to a ticket"""
    comment_id = f"comment_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{ticket_id[:8]}"
    comment = TicketComment(
        id=comment_id,
        ticket_id=ticket_id,
        author_type=author_type,
        author_id=author_id,
        message=message,
    )

    with db.get_conn() as conn:
        conn.execute(
            """
            INSERT INTO peopledesk_comments
            (id, ticket_id, author_type, author_id, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                comment.id,
                comment.ticket_id,
                comment.author_type,
                comment.author_id,
                comment.message,
                comment.created_at,
            ),
        )

        # Update ticket's updated_at timestamp
        conn.execute(
            "UPDATE peopledesk_tickets SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (ticket_id,),
        )

        # Mark first response if from support
        if author_type == "support":
            ticket = conn.execute(
                "SELECT first_response_at FROM peopledesk_tickets WHERE id = ?",
                (ticket_id,),
            ).fetchone()
            if ticket and not ticket["first_response_at"]:
                conn.execute(
                    "UPDATE peopledesk_tickets SET first_response_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (ticket_id,),
                )

        conn.commit()

    return comment


def get_ticket_comments(ticket_id: str) -> List[dict]:
    """Get all comments for a ticket"""
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM peopledesk_comments WHERE ticket_id = ? ORDER BY created_at ASC",
            (ticket_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def create_support_agent(user_id: str, name: str, email: str) -> SupportAgent:
    """Register a support agent"""
    agent = SupportAgent(id=user_id, name=name, email=email)

    with db.get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO peopledesk_agents
            (id, name, email, availability_status, assigned_tickets_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (agent.id, agent.name, agent.email, agent.availability_status, agent.assigned_tickets_count),
        )
        conn.commit()

    return agent


def list_support_agents(availability_status: Optional[str] = None) -> List[dict]:
    """List support agents"""
    with db.get_conn() as conn:
        if availability_status:
            rows = conn.execute(
                "SELECT * FROM peopledesk_agents WHERE availability_status = ? ORDER BY assigned_tickets_count ASC",
                (availability_status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM peopledesk_agents ORDER BY availability_status DESC, assigned_tickets_count ASC"
            ).fetchall()
    return [dict(row) for row in rows]


def get_support_agent(agent_id: str) -> Optional[dict]:
    """Get support agent by ID"""
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM peopledesk_agents WHERE id = ?",
            (agent_id,),
        ).fetchone()
    return dict(row) if row else None


def update_agent_availability(agent_id: str, status: str) -> bool:
    """Update agent availability status"""
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE peopledesk_agents SET availability_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, agent_id),
        )
        conn.commit()
    return True


# ============================================================================
# Statistics & SLA Tracking
# ============================================================================

def compute_support_stats() -> dict:
    """Compute support team dashboard statistics"""
    with db.get_conn() as conn:
        # Count by status
        open_count = conn.execute(
            "SELECT COUNT(*) as count FROM peopledesk_tickets WHERE status = 'open'"
        ).fetchone()["count"]

        in_progress = conn.execute(
            "SELECT COUNT(*) as count FROM peopledesk_tickets WHERE status = 'in-progress'"
        ).fetchone()["count"]

        resolved = conn.execute(
            "SELECT COUNT(*) as count FROM peopledesk_tickets WHERE status = 'resolved'"
        ).fetchone()["count"]

        # Average resolution time
        avg_resolution = conn.execute(
            """
            SELECT AVG(
                CAST((julianday(resolved_at) - julianday(created_at)) * 24 AS INTEGER)
            ) as avg_hours
            FROM peopledesk_tickets WHERE resolved_at IS NOT NULL
            """
        ).fetchone()["avg_hours"]

        # Average first response time
        avg_response = conn.execute(
            """
            SELECT AVG(
                CAST((julianday(first_response_at) - julianday(created_at)) * 60 AS INTEGER)
            ) as avg_minutes
            FROM peopledesk_tickets WHERE first_response_at IS NOT NULL
            """
        ).fetchone()["avg_minutes"]

    return {
        "total_open": open_count,
        "total_in_progress": in_progress,
        "total_resolved": resolved,
        "avg_resolution_time_hours": round(avg_resolution or 0, 1),
        "avg_first_response_time_minutes": round(avg_response or 0, 1),
        "total_tickets": open_count + in_progress + resolved,
    }


def compute_ticket_sla_status(ticket_id: str) -> dict:
    """Check ticket against SLA targets"""
    ticket = get_ticket(ticket_id)
    if not ticket:
        return {"status": "error", "message": "Ticket not found"}

    created = datetime.fromisoformat(ticket["created_at"].replace("Z", "+00:00"))
    now = datetime.utcnow()
    age_hours = (now - created.replace(tzinfo=None)).total_seconds() / 3600

    # SLA targets
    response_sla_minutes = 60  # 1 hour
    resolution_sla_hours = 24  # 24 hours

    sla_status = "on-track"
    if ticket["first_response_at"] is None and age_hours > response_sla_minutes / 60:
        sla_status = "breached"
    elif ticket["status"] != "resolved" and age_hours > resolution_sla_hours:
        sla_status = "at-risk"

    return {
        "ticket_id": ticket_id,
        "status": ticket["status"],
        "priority": ticket["priority"],
        "sla_status": sla_status,
        "age_hours": round(age_hours, 1),
        "response_sla_minutes": response_sla_minutes,
        "resolution_sla_hours": resolution_sla_hours,
    }


# ============================================================================
# Priority Auto-Assignment
# ============================================================================

PRIORITY_KEYWORDS = {
    "high": ["urgent", "critical", "emergency", "down", "broken", "blocked", "production issue"],
    "medium": ["issue", "problem", "bug", "question", "help", "need"],
    "low": ["inquiry", "question", "feedback", "enhancement", "suggestion"],
}


def detect_priority(subject: str, description: str) -> str:
    """Auto-detect priority from subject and description"""
    text = f"{subject} {description}".lower()

    for priority, keywords in PRIORITY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return priority

    return "medium"
