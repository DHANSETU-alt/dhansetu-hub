"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiGet } from "@/lib/api";

// Types
interface Ticket {
  id: string;
  customer_id: string;
  subject: string;
  description: string;
  priority: "high" | "medium" | "low";
  status: "open" | "in-progress" | "resolved";
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  first_response_at: string | null;
}

interface TicketComment {
  id: string;
  ticket_id: string;
  author_type: "customer" | "support";
  author_id: string;
  author_name?: string;
  message: string;
  created_at: string;
}

interface SupportStats {
  total_open: number;
  total_in_progress: number;
  total_resolved: number;
  total_tickets: number;
  avg_resolution_time_hours: number;
  avg_first_response_time_minutes: number;
  sla_breached: number;
  sla_at_risk: number;
  support_agents: Array<{
    id: string;
    name: string;
    email: string;
    availability_status: string;
    assigned_tickets_count: number;
  }>;
}

export default function PeopleDeskPage() {
  const [activeTab, setActiveTab] = useState("tickets");
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [comments, setComments] = useState<TicketComment[]>([]);
  const [stats, setStats] = useState<SupportStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [priorityFilter, setPriorityFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [newTicketDialog, setNewTicketDialog] = useState(false);
  const [newTicketForm, setNewTicketForm] = useState({
    subject: "",
    description: "",
    priority: "medium",
  });
  const [commentForm, setCommentForm] = useState("");

  useEffect(() => {
    loadTickets();
    loadStats();
  }, [statusFilter, priorityFilter]);

  const loadTickets = async () => {
    try {
      setIsLoading(true);
      const params = new URLSearchParams();
      if (statusFilter) params.append("status", statusFilter);
      if (priorityFilter) params.append("priority", priorityFilter);
      const data = await apiGet<any>(`/api/peopledesk/tickets?${params.toString()}`);
      setTickets(data.data || []);
      setError(null);
    } catch (err) {
      setError("Failed to load tickets");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const data = await apiGet<any>(`/api/peopledesk/stats`);
      setStats(data.data || null);
    } catch (err) {
      console.error("Failed to load stats", err);
    }
  };

  const loadTicketDetail = async (ticketId: string) => {
    try {
      const data = await apiGet<any>(`/api/peopledesk/tickets/${ticketId}`);
      setSelectedTicket(data.data.ticket);
      setComments(data.data.comments || []);
    } catch (err) {
      setError("Failed to load ticket details");
      console.error(err);
    }
  };

  const handleCreateTicket = async () => {
    if (!newTicketForm.subject.trim() || !newTicketForm.description.trim()) {
      setError("Please fill in all fields");
      return;
    }
    try {
      const response = await fetch("/api/peopledesk/ticket", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newTicketForm),
      });
      if (!response.ok) throw new Error("Failed to create ticket");
      const data = await response.json();
      setTickets([data.data, ...tickets]);
      setNewTicketDialog(false);
      setNewTicketForm({ subject: "", description: "", priority: "medium" });
      setError(null);
    } catch (err) {
      setError("Failed to create ticket");
      console.error(err);
    }
  };

  const handleAddComment = async () => {
    if (!commentForm.trim() || !selectedTicket) return;
    try {
      const response = await fetch(
        `/api/peopledesk/tickets/${selectedTicket.id}/comment`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: commentForm }),
        }
      );
      if (!response.ok) throw new Error("Failed to add comment");
      const data = await response.json();
      setComments([...comments, data.data]);
      setCommentForm("");
      setError(null);
    } catch (err) {
      setError("Failed to add comment");
      console.error(err);
    }
  };

  const handleUpdateTicketStatus = async (newStatus: string) => {
    if (!selectedTicket) return;
    try {
      const response = await fetch(
        `/api/peopledesk/tickets/${selectedTicket.id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: newStatus }),
        }
      );
      if (!response.ok) throw new Error("Failed to update ticket");
      const data = await response.json();
      setSelectedTicket(data.data);
      loadTickets();
      setError(null);
    } catch (err) {
      setError("Failed to update ticket");
      console.error(err);
    }
  };

  const filteredTickets = tickets.filter((ticket) =>
    ticket.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
    ticket.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "high":
        return "bg-red-100 text-red-800";
      case "medium":
        return "bg-yellow-100 text-yellow-800";
      case "low":
        return "bg-green-100 text-green-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "open":
        return "bg-blue-100 text-blue-800";
      case "in-progress":
        return "bg-purple-100 text-purple-800";
      case "resolved":
        return "bg-green-100 text-green-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="w-full h-full bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900">PeopleDesk</h1>
          <p className="text-slate-600 mt-2">
            Customer support ticket system and team dashboard
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-6">
            <TabsTrigger value="tickets">Tickets</TabsTrigger>
            <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
            <TabsTrigger value="agents">Support Agents</TabsTrigger>
          </TabsList>

          <TabsContent value="tickets" className="space-y-6">
            <div className="flex justify-between items-center gap-4">
              <div className="flex-1 flex gap-4">
                <Input
                  placeholder="Search tickets..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="flex-1"
                />
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Filter by status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All Status</SelectItem>
                    <SelectItem value="open">Open</SelectItem>
                    <SelectItem value="in-progress">In Progress</SelectItem>
                    <SelectItem value="resolved">Resolved</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={priorityFilter} onValueChange={setPriorityFilter}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Filter by priority" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All Priority</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Dialog open={newTicketDialog} onOpenChange={setNewTicketDialog}>
                <DialogTrigger asChild>
                  <Button className="bg-blue-600 hover:bg-blue-700">
                    New Ticket
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create Support Ticket</DialogTitle>
                    <DialogDescription>
                      Describe your issue and we'll help you out
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Subject
                      </label>
                      <Input
                        placeholder="Brief description of your issue"
                        value={newTicketForm.subject}
                        onChange={(e) =>
                          setNewTicketForm({
                            ...newTicketForm,
                            subject: e.target.value,
                          })
                        }
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Description
                      </label>
                      <Textarea
                        placeholder="Provide detailed information..."
                        value={newTicketForm.description}
                        onChange={(e) =>
                          setNewTicketForm({
                            ...newTicketForm,
                            description: e.target.value,
                          })
                        }
                        rows={4}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Priority
                      </label>
                      <Select
                        value={newTicketForm.priority}
                        onValueChange={(value) =>
                          setNewTicketForm({
                            ...newTicketForm,
                            priority: value,
                          })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="low">Low</SelectItem>
                          <SelectItem value="medium">Medium</SelectItem>
                          <SelectItem value="high">High</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <Button
                      onClick={handleCreateTicket}
                      className="w-full bg-blue-600 hover:bg-blue-700"
                    >
                      Create Ticket
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card className="lg:col-span-1">
                <CardHeader>
                  <CardTitle>Tickets</CardTitle>
                  <CardDescription>{filteredTickets.length} total</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {isLoading ? (
                      <p className="text-sm text-slate-500">Loading...</p>
                    ) : filteredTickets.length === 0 ? (
                      <p className="text-sm text-slate-500">No tickets found</p>
                    ) : (
                      filteredTickets.map((ticket) => (
                        <button
                          key={ticket.id}
                          onClick={() => loadTicketDetail(ticket.id)}
                          className={`w-full text-left p-3 rounded-lg border-2 transition ${
                            selectedTicket?.id === ticket.id
                              ? "border-blue-500 bg-blue-50"
                              : "border-slate-200 hover:bg-slate-50"
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-sm truncate">
                                {ticket.subject}
                              </p>
                              <p className="text-xs text-slate-500 mt-1">
                                {formatDate(ticket.created_at)}
                              </p>
                            </div>
                          </div>
                          <div className="flex gap-2 mt-2">
                            <Badge className={`text-xs ${getPriorityColor(ticket.priority)}`}>
                              {ticket.priority}
                            </Badge>
                            <Badge className={`text-xs ${getStatusColor(ticket.status)}`}>
                              {ticket.status}
                            </Badge>
                          </div>
                        </button>
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card className="lg:col-span-2">
                {selectedTicket ? (
                  <>
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div>
                          <CardTitle>{selectedTicket.subject}</CardTitle>
                          <CardDescription>
                            #{selectedTicket.id}
                          </CardDescription>
                        </div>
                        <div className="flex gap-2">
                          <Badge
                            className={`${getPriorityColor(selectedTicket.priority)}`}
                          >
                            {selectedTicket.priority}
                          </Badge>
                          <Select
                            value={selectedTicket.status}
                            onValueChange={handleUpdateTicketStatus}
                          >
                            <SelectTrigger className="w-32 h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="open">Open</SelectItem>
                              <SelectItem value="in-progress">
                                In Progress
                              </SelectItem>
                              <SelectItem value="resolved">Resolved</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div>
                        <h4 className="font-medium text-sm mb-2">Description</h4>
                        <p className="text-sm text-slate-600">
                          {selectedTicket.description}
                        </p>
                      </div>

                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-slate-500">Created</p>
                          <p className="font-medium">
                            {formatDate(selectedTicket.created_at)}
                          </p>
                        </div>
                        {selectedTicket.first_response_at && (
                          <div>
                            <p className="text-slate-500">First Response</p>
                            <p className="font-medium">
                              {formatDate(selectedTicket.first_response_at)}
                            </p>
                          </div>
                        )}
                        {selectedTicket.resolved_at && (
                          <div>
                            <p className="text-slate-500">Resolved</p>
                            <p className="font-medium">
                              {formatDate(selectedTicket.resolved_at)}
                            </p>
                          </div>
                        )}
                      </div>

                      <div>
                        <h4 className="font-medium text-sm mb-3">
                          Comments ({comments.length})
                        </h4>
                        <div className="space-y-3 max-h-64 overflow-y-auto mb-4">
                          {comments.map((comment) => (
                            <div
                              key={comment.id}
                              className={`p-3 rounded-lg ${
                                comment.author_type === "support"
                                  ? "bg-blue-50 border-l-4 border-blue-500"
                                  : "bg-slate-50 border-l-4 border-slate-300"
                              }`}
                            >
                              <div className="flex items-center justify-between mb-1">
                                <p className="font-medium text-sm">
                                  {comment.author_name || comment.author_id}
                                </p>
                                <p className="text-xs text-slate-500">
                                  {formatDate(comment.created_at)}
                                </p>
                              </div>
                              <p className="text-sm text-slate-700">
                                {comment.message}
                              </p>
                            </div>
                          ))}
                        </div>

                        <div className="space-y-2">
                          <Textarea
                            placeholder="Add a comment..."
                            value={commentForm}
                            onChange={(e) => setCommentForm(e.target.value)}
                            rows={2}
                          />
                          <Button
                            onClick={handleAddComment}
                            className="w-full bg-blue-600 hover:bg-blue-700"
                            disabled={!commentForm.trim()}
                          >
                            Post Comment
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </>
                ) : (
                  <CardContent className="py-8">
                    <p className="text-center text-slate-500">
                      Select a ticket to view details
                    </p>
                  </CardContent>
                )}
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="dashboard">
            {stats ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium">
                      Open Tickets
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{stats.total_open}</div>
                    <p className="text-xs text-slate-500 mt-1">Active issues</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium">
                      In Progress
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {stats.total_in_progress}
                    </div>
                    <p className="text-xs text-slate-500 mt-1">Being worked on</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium">
                      Resolved
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{stats.total_resolved}</div>
                    <p className="text-xs text-slate-500 mt-1">This month</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium">
                      Avg Response
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {stats.avg_first_response_time_minutes}m
                    </div>
                    <p className="text-xs text-slate-500 mt-1">First response</p>
                  </CardContent>
                </Card>

                <Card className="md:col-span-2 lg:col-span-4">
                  <CardHeader>
                    <CardTitle>SLA Status</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-slate-600 mb-2">
                          On Track / At Risk / Breached
                        </p>
                        <div className="flex gap-2 items-center">
                          <div className="flex-1 h-2 bg-green-500 rounded"></div>
                          <div className="flex-1 h-2 bg-yellow-500 rounded"></div>
                          <div className="flex-1 h-2 bg-red-500 rounded"></div>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-red-600">
                          {stats.sla_breached}
                        </p>
                        <p className="text-xs text-slate-500">SLA Breached</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            ) : (
              <Card>
                <CardContent className="py-8">
                  <p className="text-center text-slate-500">Loading stats...</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="agents">
            {stats?.support_agents && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {stats.support_agents.map((agent) => (
                  <Card key={agent.id}>
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div>
                          <CardTitle className="text-base">{agent.name}</CardTitle>
                          <CardDescription className="text-xs">
                            {agent.email}
                          </CardDescription>
                        </div>
                        <Badge
                          className={
                            agent.availability_status === "available"
                              ? "bg-green-100 text-green-800"
                              : agent.availability_status === "busy"
                              ? "bg-yellow-100 text-yellow-800"
                              : "bg-gray-100 text-gray-800"
                          }
                        >
                          {agent.availability_status}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div>
                          <p className="text-sm text-slate-600">
                            Assigned Tickets
                          </p>
                          <p className="text-2xl font-bold">
                            {agent.assigned_tickets_count}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
