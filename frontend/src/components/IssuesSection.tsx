"use client";

import React, { useState } from "react";
import { Issue, User, apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  AlertCircle, CheckCircle2, Plus, ListOrdered, Calendar,
  Check, ArrowRight, CornerDownRight, MessageSquare
} from "lucide-react";

interface IssuesSectionProps {
  teamId: string;
  unsolvedIssues: Issue[];
  solvedIssues: Issue[];
  teamMembers: User[];
  onRefresh: () => void;
  isMeetingMode?: boolean;
}

export const IssuesSection: React.FC<IssuesSectionProps> = ({
  teamId,
  unsolvedIssues,
  solvedIssues,
  teamMembers,
  onRefresh,
  isMeetingMode = false,
}) => {
  const { currentUser } = useAuth();
  const [tab, setTab] = useState<"unsolved" | "solved">("unsolved");

  // Create Issue Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newPriority, setNewPriority] = useState<string>("");

  // Solve Issue Modal state
  const [solvingIssue, setSolvingIssue] = useState<Issue | null>(null);
  const [solveNote, setSolveNote] = useState("");

  // Add To-Do Modal state
  const [todoIssue, setTodoIssue] = useState<Issue | null>(null);
  const [todoTitle, setTodoTitle] = useState("");
  const [todoOwnerId, setTodoOwnerId] = useState("");

  const isObserver = currentUser?.role === "observer";

  const handleCreateIssue = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !currentUser || isObserver) return;
    try {
      await apiFetch(
        `/api/teams/${teamId}/issues`,
        {
          method: "POST",
          body: JSON.stringify({
            title: newTitle.trim(),
            priority: newPriority ? parseInt(newPriority, 10) : null,
          }),
        },
        currentUser.id
      );
      setNewTitle("");
      setNewPriority("");
      setShowCreateModal(false);
      onRefresh();
    } catch (e: any) {
      alert(e.message || "Failed to create issue");
    }
  };

  const handleUpdatePriority = async (issueId: string, priorityVal: string) => {
    if (!currentUser || isObserver) return;
    try {
      await apiFetch(
        `/api/issues/${issueId}/priority`,
        {
          method: "PATCH",
          body: JSON.stringify({
            priority: priorityVal ? parseInt(priorityVal, 10) : null,
          }),
        },
        currentUser.id
      );
      onRefresh();
    } catch (e: any) {
      alert(e.message || "Failed to update priority");
    }
  };

  const handleSolveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!solvingIssue || !solveNote.trim() || !currentUser || isObserver) return;
    try {
      await apiFetch(
        `/api/issues/${solvingIssue.id}/solve`,
        {
          method: "POST",
          body: JSON.stringify({ resolution_note: solveNote.trim() }),
        },
        currentUser.id
      );
      setSolvingIssue(null);
      setSolveNote("");
      onRefresh();
    } catch (e: any) {
      alert(e.message || "Failed to solve issue");
    }
  };

  const handleCreateTodoSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!todoIssue || !todoTitle.trim() || !todoOwnerId || !currentUser || isObserver) return;
    try {
      await apiFetch(
        `/api/teams/${teamId}/todos`,
        {
          method: "POST",
          body: JSON.stringify({
            title: todoTitle.trim(),
            owner_id: todoOwnerId,
            source_issue_id: todoIssue.id,
          }),
        },
        currentUser.id
      );
      setTodoIssue(null);
      setTodoTitle("");
      setTodoOwnerId("");
      onRefresh();
    } catch (e: any) {
      alert(e.message || "Failed to create todo");
    }
  };

  const eligibleTodoOwners = teamMembers.filter((m) => m.role !== "observer");

  const getPriorityBadge = (p: number | null) => {
    if (p === 5) return <span className="px-2 py-0.5 rounded text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">P5 (Critical)</span>;
    if (p === 4) return <span className="px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">P4 (High)</span>;
    if (p === 3) return <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">P3 (Medium)</span>;
    if (p === 2) return <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 border border-gray-200">P2 (Low)</span>;
    if (p === 1) return <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200">P1 (Lowest)</span>;
    return <span className="px-2 py-0.5 rounded text-xs text-gray-400 bg-gray-50 border border-gray-200">No Priority</span>;
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
        <div className="flex items-center gap-4">
          <div>
            <h2 className="text-lg font-bold text-gray-900">
              {isMeetingMode ? "IDS (Identify, Discuss, Solve)" : "Issues"}
            </h2>
            <p className="text-xs text-gray-500">
              Sorted by Priority (P5 to P1, oldest first, no priority last).
            </p>
          </div>

          <div className="flex items-center bg-gray-200/80 p-0.5 rounded-lg text-xs font-medium">
            <button
              onClick={() => setTab("unsolved")}
              className={`px-3 py-1 rounded-md transition ${
                tab === "unsolved" ? "bg-white text-gray-900 shadow-xs font-semibold" : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Unsolved ({unsolvedIssues.length})
            </button>
            <button
              onClick={() => setTab("solved")}
              className={`px-3 py-1 rounded-md transition ${
                tab === "solved" ? "bg-white text-gray-900 shadow-xs font-semibold" : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Solved ({solvedIssues.length})
            </button>
          </div>
        </div>

        {!isObserver && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
          >
            <Plus className="w-3.5 h-3.5" /> New Issue
          </button>
        )}
      </div>

      {/* Content */}
      <div className="divide-y divide-gray-100">
        {tab === "unsolved" && (
          <>
            {unsolvedIssues.length === 0 ? (
              <div className="p-8 text-center text-gray-400 text-sm">No unsolved issues! Great job.</div>
            ) : (
              unsolvedIssues.map((issue, idx) => (
                <div key={issue.id} className="p-4 hover:bg-gray-50/60 transition flex items-center justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <div className="w-6 h-6 rounded-full bg-blue-50 text-blue-700 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                      {idx + 1}
                    </div>

                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-sm text-gray-900">{issue.title}</span>
                        {getPriorityBadge(issue.priority)}
                        {issue.source && (
                          <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-purple-50 text-purple-700 border border-purple-200">
                            Source: {issue.source.measurable_id} ({issue.source.week_start})
                          </span>
                        )}
                      </div>

                      <div className="text-xs text-gray-500 flex items-center gap-3">
                        <span>Owner: <strong className="text-gray-700">{issue.owner_name || issue.owner_id}</strong></span>
                        <span>•</span>
                        <span>Created: {new Date(issue.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  {!isObserver && (
                    <div className="flex items-center gap-2 shrink-0">
                      {/* Priority selector */}
                      <select
                        value={issue.priority !== null ? String(issue.priority) : ""}
                        onChange={(e) => handleUpdatePriority(issue.id, e.target.value)}
                        className="text-xs bg-gray-50 border border-gray-300 rounded px-2 py-1 text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        title="Change priority"
                      >
                        <option value="">No Priority</option>
                        <option value="5">P5 (Critical)</option>
                        <option value="4">P4 (High)</option>
                        <option value="3">P3 (Medium)</option>
                        <option value="2">P2 (Low)</option>
                        <option value="1">P1 (Lowest)</option>
                      </select>

                      {/* Add To-Do Button */}
                      <button
                        onClick={() => {
                          setTodoIssue(issue);
                          setTodoTitle(`Follow up: ${issue.title}`);
                          setTodoOwnerId(currentUser?.id || eligibleTodoOwners[0]?.id || "");
                        }}
                        className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-md transition"
                        title="Add follow-up To-Do"
                      >
                        <CornerDownRight className="w-3.5 h-3.5" /> To-Do
                      </button>

                      {/* Solve Button */}
                      <button
                        onClick={() => {
                          setSolvingIssue(issue);
                          setSolveNote("");
                        }}
                        className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-md transition"
                      >
                        <Check className="w-3.5 h-3.5" /> Solve
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
          </>
        )}

        {tab === "solved" && (
          <>
            {solvedIssues.length === 0 ? (
              <div className="p-8 text-center text-gray-400 text-sm">No solved issues recorded yet.</div>
            ) : (
              solvedIssues.map((issue) => (
                <div key={issue.id} className="p-4 hover:bg-gray-50/60 transition space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span className="font-semibold text-sm text-gray-900">{issue.title}</span>
                    </div>
                    <span className="text-xs text-gray-400">
                      Solved {issue.solved_at ? new Date(issue.solved_at).toLocaleString() : ""}
                    </span>
                  </div>

                  {issue.resolution_note && (
                    <div className="text-xs bg-gray-50 p-2.5 rounded-lg border border-gray-200 text-gray-700 flex items-start gap-2">
                      <MessageSquare className="w-3.5 h-3.5 text-gray-400 shrink-0 mt-0.5" />
                      <div>
                        <strong>Resolution:</strong> {issue.resolution_note}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </>
        )}
      </div>

      {/* Modal: Create Issue */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl animate-fadeIn">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Create New Issue</h3>
            <form onSubmit={handleCreateIssue} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Issue Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Server response latency in APAC"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Priority (Optional)</label>
                <select
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value)}
                  className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">No Priority</option>
                  <option value="5">P5 (Critical)</option>
                  <option value="4">P4 (High)</option>
                  <option value="3">P3 (Medium)</option>
                  <option value="2">P2 (Low)</option>
                  <option value="1">P1 (Lowest)</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg"
                >
                  Create Issue
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Solve Issue */}
      {solvingIssue && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl animate-fadeIn">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Solve Issue</h3>
            <p className="text-xs text-gray-500 mb-4 font-medium">"{solvingIssue.title}"</p>

            <form onSubmit={handleSolveSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Resolution Note * (Required)
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="Explain how this issue was resolved..."
                  value={solveNote}
                  onChange={(e) => setSolveNote(e.target.value)}
                  className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSolvingIssue(null)}
                  className="px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!solveNote.trim()}
                  className="px-4 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg disabled:opacity-50"
                >
                  Mark as Solved
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add To-Do from Issue */}
      {todoIssue && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl animate-fadeIn">
            <h3 className="text-lg font-bold text-gray-900 mb-1">Add To-Do for Issue</h3>
            <p className="text-xs text-gray-500 mb-4">Linked to "{todoIssue.title}" (Due in 7 days)</p>

            <form onSubmit={handleCreateTodoSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">To-Do Title *</label>
                <input
                  type="text"
                  required
                  value={todoTitle}
                  onChange={(e) => setTodoTitle(e.target.value)}
                  className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Owner * (Admins & Team Members only)
                </label>
                <select
                  required
                  value={todoOwnerId}
                  onChange={(e) => setTodoOwnerId(e.target.value)}
                  className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-blue-500 focus:border-blue-500"
                >
                  {eligibleTodoOwners.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({m.role.replace("_", " ")})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setTodoIssue(null)}
                  className="px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg"
                >
                  Create To-Do
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

