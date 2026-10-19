# PeopleDesk — Customer Support Ticket System

Production-ready customer support ticket management system for DhanSetu Hub. Provides ticket creation, comment threading, support team management, and SLA tracking.

## Architecture

### Data Model (`orchestrator/peopledesk_model.py`)

**Tables:**
- `peopledesk_tickets` — Core support tickets (id, customer_id, subject, description, priority, status, assigned_to, timestamps)
- `peopledesk_comments` — Thread comments (ticket_id, author_type, author_id, message, created_at)
- `peopledesk_agents` — Support team members (id, name, email, availability_status, assigned_tickets_count)
- `peopledesk_metrics` — SLA tracking (ticket_id, response_time_minutes, resolution_time_minutes, sla_status)

**Entities:**
- `Ticket` — Support ticket with priority (high/medium/low), status (open/in-progress/resolved)
- `TicketComment` — Thread comment from customer or support agent
- `SupportAgent` — Team member with availability status (available/busy/away)

### API Routes (`dashboard/app/api/peopledesk/`)

**POST `/api/peopledesk/ticket`**
Create a new support ticket
```typescript
{
  subject: string,
  description: string,
  priority?: "high" | "medium" | "low"
}
```
Returns: Created ticket object with id, status, timestamps

**GET `/api/peopledesk/tickets`**
List tickets with filtering
Query params:
- `status` — Filter by status (open/in-progress/resolved)
- `priority` — Filter by priority (high/medium/low)
- `limit` — Max results (default 50)
- `role` — "customer" or "support" (determines visibility)

**GET `/api/peopledesk/tickets/[id]`**
Retrieve ticket details with comment thread

**PATCH `/api/peopledesk/tickets/[id]`**
Update ticket status/priority/assignment
```typescript
{
  status?: "open" | "in-progress" | "resolved",
  priority?: "high" | "medium" | "low",
  assigned_to?: string
}
```

**POST `/api/peopledesk/tickets/[id]/comment`**
Add comment to ticket
```typescript
{ message: string }
```

**GET `/api/peopledesk/stats`**
Support team dashboard metrics
Returns:
- `total_open` — Open tickets count
- `total_in_progress` — In progress count
- `total_resolved` — Resolved count
- `avg_resolution_time_hours` — Average hours to resolve
- `avg_first_response_time_minutes` — Average minutes to first response
- `sla_breached` — Count of breached SLAs
- `support_agents` — List of agents with workload

### Frontend Component (`dashboard/app/peopledesk/page.tsx`)

Three-tab interface:

**1. Tickets Tab**
- Search and filter tickets by status/priority
- Side panel: List of tickets for quick access
- Main panel: Selected ticket details, comment thread, status update dropdown
- Create ticket dialog

**2. Dashboard Tab**
- Metrics cards: Open, In Progress, Resolved counts
- Average response/resolution times
- SLA status visualization
- Team workload summary

**3. Support Agents Tab**
- Agent profiles with availability status
- Current workload (assigned tickets count)
- Online/busy/away status indicator

## Features

### Ticket Management
- **Create**: Customers create tickets with subject, description, priority
- **View**: Customers see only own tickets; support agents see all
- **Update**: Support agents change status and assign tickets
- **Comment**: Bidirectional threaded comments (customer + support)
- **Close**: Mark tickets as resolved with optional reopen

### Priority Auto-Detection
Keywords trigger automatic priority assignment:
- **High**: "urgent", "critical", "emergency", "down", "broken", "blocked", "production issue"
- **Medium**: "issue", "problem", "bug", "question", "help", "need"
- **Low**: "inquiry", "question", "feedback", "enhancement", "suggestion"

### SLA Tracking
- **Response SLA**: 60 minutes to first support response
- **Resolution SLA**: 24 hours to resolve
- **Status**: On-track, At-risk (nearing SLA), Breached (exceeded SLA)
- **Metrics**: Computed per-ticket; aggregated for dashboard

### Support Agent Management
- Register support agents with email and availability status
- Track current workload (assigned_tickets_count)
- Auto-assign new tickets to least-loaded available agents
- Update availability: available / busy / away

### Notifications
- Ticket creation → customer notification
- First support response → customer notification
- Ticket assignment → agent notification
- Status changes → relevant parties notification

## Permission Model

| Role | Can View | Can Create | Can Update | Can Assign | Can Comment |
|------|----------|-----------|-----------|-----------|-----------|
| Customer | Own tickets | Yes | No | No | Yes |
| Support Agent | All tickets | No | Yes | Yes | Yes |
| Admin | All tickets | Yes | Yes | Yes | Yes |

## Database Schema

```sql
CREATE TABLE peopledesk_tickets (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT DEFAULT 'medium',  -- high, medium, low
    status TEXT DEFAULT 'open',  -- open, in-progress, resolved
    assigned_to TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    first_response_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(id),
    FOREIGN KEY (assigned_to) REFERENCES peopledesk_agents(id)
);

CREATE TABLE peopledesk_comments (
    id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    author_type TEXT CHECK(author_type IN ('customer', 'support')),
    author_id TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES peopledesk_tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES users(id)
);

CREATE TABLE peopledesk_agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    availability_status TEXT DEFAULT 'available',
    assigned_tickets_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id) REFERENCES users(id)
);

CREATE TABLE peopledesk_metrics (
    id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    response_time_minutes INTEGER,
    resolution_time_minutes INTEGER,
    first_response_at TIMESTAMP,
    resolved_at TIMESTAMP,
    sla_status TEXT DEFAULT 'in-progress',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES peopledesk_tickets(id) ON DELETE CASCADE
);
```

## Testing

Run comprehensive tests:
```bash
pytest tests/test_peopledesk.py -v
```

**Test Coverage:**
- Ticket creation and retrieval
- Comment threading (customer + support)
- Status transitions (open → in-progress → resolved)
- Permission checks (customer vs support agent)
- SLA tracking and breaches
- Support agent management and workload
- Priority auto-detection
- Email notification triggers
- Statistics and reporting

## Usage Examples

### Create a Ticket (Customer)
```bash
curl -X POST /api/peopledesk/ticket \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Payment processing error",
    "description": "Getting 502 error on checkout",
    "priority": "high"
  }'
```

### List Customer's Tickets
```bash
curl /api/peopledesk/tickets?role=customer&status=open
```

### Add Comment to Ticket
```bash
curl -X POST /api/peopledesk/tickets/ticket_001/comment \
  -H "Content-Type: application/json" \
  -d '{ "message": "Please check this urgently" }'
```

### Update Ticket Status (Support Agent)
```bash
curl -X PATCH /api/peopledesk/tickets/ticket_001 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in-progress",
    "assigned_to": "agent_001"
  }'
```

### Get Dashboard Stats
```bash
curl /api/peopledesk/stats
```

## Performance Considerations

- **Indexing**: Composite indexes on (customer_id, created_at) for quick ticket lookup
- **Pagination**: Use limit parameter (default 50, max 1000) to control result size
- **Comment Caching**: Comments cached in frontend; refresh on new comment
- **Agent Load Balancing**: Query agents ordered by assigned_tickets_count for auto-assign

## Security

- **Row-Level Security**: Customers see only own tickets via customer_id check
- **Role-Based Access**: Support agents verified before allowing status updates
- **Input Validation**: Max message length 5000 characters
- **Rate Limiting**: API requests rate limited per user/IP
- **Audit Logging**: All ticket changes logged (created, updated, resolved, commented)

## Future Enhancements

- [ ] Email integration (send/receive ticket comments via email)
- [ ] SLA automation (auto-escalate breached tickets)
- [ ] Customer satisfaction surveys
- [ ] Knowledge base linking (suggest articles for similar issues)
- [ ] Canned responses library for support agents
- [ ] Customer portal with knowledge base search
- [ ] Multi-language support
- [ ] Bulk ticket operations (close all, reassign, etc)

## Monitoring & Alerts

Key metrics to monitor:
- **Response Time**: Alert if avg > 2 hours
- **Resolution Time**: Alert if avg > 72 hours
- **SLA Breaches**: Alert if > 5 breached tickets
- **Agent Availability**: Alert if all agents busy/away
- **Backlog**: Alert if open tickets > 50

## Support

For questions or issues:
- Check PEOPLEDESK.md for API documentation
- Review test suite for usage examples
- Contact: support@dhansetuhub.in
