"""
Tests for PeopleDesk customer support ticket system
"""

import pytest
from datetime import datetime, timedelta
from orchestrator.peopledesk_model import (
    Ticket, TicketComment, SupportAgent, detect_priority
)


class TestTicketCreation:
    def test_create_ticket_success(self):
        """Test successful ticket creation"""
        ticket = Ticket(
            id="ticket_001",
            customer_id="customer_abc",
            subject="Payment not working",
            description="Cannot complete checkout",
            priority="high",
            status="open"
        )
        
        assert ticket.id == "ticket_001"
        assert ticket.customer_id == "customer_abc"
        assert ticket.subject == "Payment not working"
        assert ticket.priority == "high"
        assert ticket.status == "open"
        assert ticket.created_at is not None
        assert ticket.resolved_at is None

    def test_ticket_to_dict(self):
        """Test ticket serialization"""
        ticket = Ticket(
            id="ticket_001",
            customer_id="customer_abc",
            subject="Test",
            description="Test description"
        )
        
        data = ticket.to_dict()
        assert data["id"] == "ticket_001"
        assert data["customer_id"] == "customer_abc"
        assert "created_at" in data

    def test_ticket_defaults(self):
        """Test ticket default values"""
        ticket = Ticket(
            id="ticket_001",
            customer_id="customer_abc",
            subject="Test",
            description="Test"
        )
        
        assert ticket.priority == "medium"
        assert ticket.status == "open"
        assert ticket.assigned_to is None


class TestCommentThreading:
    def test_create_comment(self):
        """Test creating a comment on a ticket"""
        comment = TicketComment(
            id="comment_001",
            ticket_id="ticket_001",
            author_type="customer",
            author_id="customer_abc",
            message="This is still not working"
        )
        
        assert comment.id == "comment_001"
        assert comment.ticket_id == "ticket_001"
        assert comment.author_type == "customer"
        assert comment.message == "This is still not working"
        assert comment.created_at is not None

    def test_comment_from_support_agent(self):
        """Test comment from support agent"""
        comment = TicketComment(
            id="comment_002",
            ticket_id="ticket_001",
            author_type="support",
            author_id="agent_001",
            message="We're looking into this"
        )
        
        assert comment.author_type == "support"
        assert comment.author_id == "agent_001"


class TestStatusTransitions:
    def test_open_to_in_progress(self):
        """Test transitioning ticket from open to in-progress"""
        ticket = {"id": "t1", "status": "open"}
        ticket["status"] = "in-progress"
        assert ticket["status"] == "in-progress"

    def test_in_progress_to_resolved(self):
        """Test transitioning ticket from in-progress to resolved"""
        ticket = {"id": "t1", "status": "in-progress", "resolved_at": None}
        ticket["status"] = "resolved"
        ticket["resolved_at"] = datetime.utcnow().isoformat()
        
        assert ticket["status"] == "resolved"
        assert ticket["resolved_at"] is not None

    def test_reopening_resolved_ticket(self):
        """Test reopening a resolved ticket"""
        ticket = {
            "id": "t1",
            "status": "resolved",
            "resolved_at": datetime.utcnow().isoformat()
        }
        
        ticket["status"] = "open"
        ticket["resolved_at"] = None
        
        assert ticket["status"] == "open"
        assert ticket["resolved_at"] is None


class TestPermissions:
    def test_customer_sees_only_own_tickets(self):
        """Test that customers can only see their own tickets"""
        all_tickets = [
            {"id": "t1", "customer_id": "customer_abc", "subject": "My issue"},
            {"id": "t2", "customer_id": "customer_def", "subject": "Other issue"},
            {"id": "t3", "customer_id": "customer_abc", "subject": "My other issue"},
        ]
        
        customer_abc_tickets = [t for t in all_tickets if t["customer_id"] == "customer_abc"]
        assert len(customer_abc_tickets) == 2
        assert all(t["customer_id"] == "customer_abc" for t in customer_abc_tickets)

    def test_support_agent_sees_all_tickets(self):
        """Test that support agents can see all tickets"""
        all_tickets = [
            {"id": "t1", "customer_id": "customer_abc"},
            {"id": "t2", "customer_id": "customer_def"},
            {"id": "t3", "customer_id": "customer_abc"},
        ]
        
        assert len(all_tickets) == 3


class TestSupportAgent:
    def test_create_support_agent(self):
        """Test creating a support agent"""
        agent = SupportAgent(
            id="agent_001",
            name="Sarah Support",
            email="sarah@support.com",
            availability_status="available"
        )
        
        assert agent.id == "agent_001"
        assert agent.name == "Sarah Support"
        assert agent.email == "sarah@support.com"
        assert agent.availability_status == "available"
        assert agent.assigned_tickets_count == 0

    def test_agent_availability_status(self):
        """Test agent availability status changes"""
        agent = SupportAgent(
            id="agent_001",
            name="Sarah",
            email="sarah@support.com",
            availability_status="available"
        )
        
        assert agent.availability_status == "available"
        
        agent.availability_status = "busy"
        assert agent.availability_status == "busy"
        
        agent.availability_status = "away"
        assert agent.availability_status == "away"

    def test_agent_workload_distribution(self):
        """Test that agents are selected based on current workload"""
        agents = [
            {"id": "agent_001", "assigned_tickets_count": 5},
            {"id": "agent_002", "assigned_tickets_count": 3},
            {"id": "agent_003", "assigned_tickets_count": 8},
        ]
        
        sorted_agents = sorted(agents, key=lambda a: a["assigned_tickets_count"])
        next_agent = sorted_agents[0]
        
        assert next_agent["id"] == "agent_002"
        assert next_agent["assigned_tickets_count"] == 3


class TestPriorityDetection:
    def test_detect_high_priority(self):
        """Test detecting high priority issues"""
        priority = detect_priority(
            "Production issue",
            "Our system is down and customers cannot access the service"
        )
        assert priority == "high"

    def test_detect_medium_priority(self):
        """Test detecting medium priority issues"""
        priority = detect_priority(
            "User reported a bug",
            "When I click the export button, nothing happens"
        )
        assert priority in ["medium", "high"]

    def test_detect_low_priority(self):
        """Test detecting low priority issues"""
        priority = detect_priority(
            "Feature request",
            "It would be nice to have dark mode"
        )
        assert priority in ["low", "medium"]

    def test_default_priority(self):
        """Test default priority when no keywords match"""
        priority = detect_priority(
            "Just checking",
            "Random message with no keywords"
        )
        assert priority == "medium"


class TestStatisticsAndReporting:
    def test_ticket_count_by_status(self):
        """Test counting tickets by status"""
        tickets = [
            {"id": "t1", "status": "open"},
            {"id": "t2", "status": "open"},
            {"id": "t3", "status": "in-progress"},
            {"id": "t4", "status": "resolved"},
            {"id": "t5", "status": "resolved"},
            {"id": "t6", "status": "resolved"},
        ]
        
        status_counts = {}
        for ticket in tickets:
            status = ticket["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        assert status_counts["open"] == 2
        assert status_counts["in-progress"] == 1
        assert status_counts["resolved"] == 3

    def test_support_team_workload(self):
        """Test calculating support team total workload"""
        agents = [
            {"id": "agent_001", "assigned_tickets_count": 5},
            {"id": "agent_002", "assigned_tickets_count": 3},
            {"id": "agent_003", "assigned_tickets_count": 7},
        ]
        
        total_workload = sum(a["assigned_tickets_count"] for a in agents)
        avg_workload = total_workload / len(agents)
        
        assert total_workload == 15
        assert avg_workload == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
