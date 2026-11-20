"use client";

import React, { useState } from "react";
import { ToDo, User, apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CheckSquare, Square, AlertCircle, Plus, CheckCircle2, TrendingUp, Calendar } from "lucide-react";

interface TodosSectionProps {
  teamId: string;
  todos: ToDo[];
  lastClosedWeekStat: {
    week_start: string;
    due: number;
    done: number;
    rate_percent: number;
    meets_target: boolean;
  } | null;
  teamMembers: User[];
  onRefresh: () => void;
}

export const TodosSection: React.FC<TodosSectionProps> = ({
  teamId,
  todos,
  lastClosedWeekStat,
  teamMembers,
  onRefresh,
}) => {
  const { currentUser } = useAuth();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newOwnerId, setNewOwnerId] = useState("");
  const [newDueDate, setNewDueDate] = useState("");

  const isObserver = currentUser?.role === "observer";

  const handleToggleDone = async (todoId: string) => {
    if (!currentUser || isObserver) return;
    try {
      await apiFetch(
        `/api/todos/${todoId}/toggle`,
        { method: "PATCH" },
        currentUser.id
      );
      onRefresh();
    } catch (e: any) {
      alert(e.message || "Failed to toggle To-Do");
    }
  };

  const handleCreateTodo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newOwnerId || !currentUser || isObserver) return;
    try {
      await apiFetch(
        `/api/teams/${teamId}/todos`,
        {
          method: "POST",
          body: JSON.stringify({
            title: newTitle.trim(),
            owner_id: newOwnerId,
            due_date: newDueDate || undefined,
          }),
        },
        currentUser.id
      );
      setNewTitle("");
      setNewOwnerId("");
      setNewDueDate("");
      setShowCreateModal(false);
      onRefresh();
    } catch (e: any) {
      alert(e.message || "Failed to create To-Do");
    }
  };

  const eligibleOwners = teamMembers.filter((m) => m.role !== "observer");

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
        <div>
          <h2 className="text-lg font-bold text-gray-900">To-Dos</h2>
          <p className="text-xs text-gray-500">7-day action items. Overdue tasks flagged.</p>
        </div>

        {!isObserver && (
          <button
            onClick={() => {
              setNewOwnerId(currentUser?.id || eligibleOwners[0]?.id || "");
              setShowCreateModal(true);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
          >
            <Plus className="w-3.5 h-3.5" /> New To-Do
          </button>
        )}
      </div>

      {/* Completion Banner for Last Closed Week */}
      {lastClosedWeekStat && (
        <div className="px-6 py-3 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-semibold text-blue-900">
              Last Closed Week ({lastClosedWeekStat.week_start}) Completion Rate:
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-blue-800 font-mono">
              Due: <strong>{lastClosedWeekStat.due}</strong> | Done: <strong>{lastClosedWeekStat.done}</strong> (
              <strong>{lastClosedWeekStat.rate_percent}%</strong>)
            </span>

            {lastClosedWeekStat.meets_target ? (
              <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                Target Met (≥90%)
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">
                Below Target (&lt;90%)
              </span>
            )}
          </div>
        </div>
      )}

      {/* List */}
      <div className="divide-y divide-gray-100">
        {todos.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">No To-Dos currently recorded.</div>
        ) : (
          todos.map((todo) => {
            const isDone = todo.done_at !== null;
            return (
              <div
                key={todo.id}
                className={`p-4 flex items-center justify-between gap-4 transition ${
                  isDone ? "bg-gray-50/50 opacity-75" : "hover:bg-gray-50/60"
                }`}
              >
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <button
                    onClick={() => handleToggleDone(todo.id)}
                    disabled={isObserver}
                    className={`mt-0.5 shrink-0 ${
                      isObserver ? "cursor-default text-gray-400" : "text-blue-600 hover:text-blue-700 cursor-pointer"
                    }`}
                  >
                    {isDone ? (
                      <CheckSquare className="w-5 h-5 text-emerald-600" />
                    ) : (
                      <Square className="w-5 h-5 text-gray-400" />
                    )}
                  </button>

                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={`text-sm font-semibold ${
                          isDone ? "line-through text-gray-500 font-normal" : "text-gray-900"
                        }`}
                      >
                        {todo.title}
                      </span>

                      {todo.is_overdue && !isDone && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-rose-100 text-rose-800 border border-rose-300 animate-pulse">
                          <AlertCircle className="w-3 h-3 text-rose-600" /> Overdue
                        </span>
                      )}

                      {todo.source_issue_id && (
                        <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-purple-50 text-purple-700 border border-purple-200">
                          Issue: {todo.source_issue_id}
                        </span>
                      )}
                    </div>

                    <div className="text-xs text-gray-500 flex items-center gap-3">
                      <span>Owner: <strong className="text-gray-700">{todo.owner_name || todo.owner_id}</strong></span>
                      <span>•</span>
                      <span>Due: <strong>{todo.due_date}</strong></span>
                      {isDone && (
                        <>
                          <span>•</span>
                          <span className="text-emerald-700 font-medium">Done: {new Date(todo.done_at!).toLocaleDateString()}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Modal: Create To-Do */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl animate-fadeIn">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Create New To-Do</h3>
            <form onSubmit={handleCreateTodo} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Follow up on Q4 renewal proposals"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Owner * (Admins & Team Members only)
                </label>
                <select
                  required
                  value={newOwnerId}
                  onChange={(e) => setNewOwnerId(e.target.value)}
                  className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-blue-500 focus:border-blue-500"
                >
                  {eligibleOwners.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({m.role.replace("_", " ")})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Due Date (Defaults to 7 days)</label>
                <input
                  type="date"
                  value={newDueDate}
                  onChange={(e) => setNewDueDate(e.target.value)}
                  className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
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

