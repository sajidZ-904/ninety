"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Header } from "@/components/Header";
import { ScorecardSection } from "@/components/ScorecardSection";
import { IssuesSection } from "@/components/IssuesSection";
import { TodosSection } from "@/components/TodosSection";
import { RocksSection } from "@/components/RocksSection";
import {
  Measurable, Issue, ToDo, Rock, User, Team, apiFetch
} from "@/lib/api";
import { ShieldAlert, RefreshCw } from "lucide-react";

export default function TeamDashboardPage() {
  const params = useParams();
  const teamId = params.teamId as string;
  const { currentUser, isLoading: authLoading } = useAuth();

  const [team, setTeam] = useState<Team | null>(null);
  const [measurables, setMeasurables] = useState<Measurable[]>([]);
  const [unsolvedIssues, setUnsolvedIssues] = useState<Issue[]>([]);
  const [solvedIssues, setSolvedIssues] = useState<Issue[]>([]);
  const [todos, setTodos] = useState<ToDo[]>([]);
  const [lastClosedWeekStat, setLastClosedWeekStat] = useState<any>(null);
  const [rocks, setRocks] = useState<Rock[]>([]);
  const [teamMembers, setTeamMembers] = useState<User[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = useCallback(async () => {
    if (!currentUser || !teamId) return;
    setError(null);

    try {
      // 1. Team Info & Access Check
      const teamData = await apiFetch<Team>(`/api/teams/${teamId}`, {}, currentUser.id);
      setTeam(teamData);

      // 2. Fetch all team sections in parallel
      const [mRes, issuesRes, todosRes, rocksRes, membersRes] = await Promise.all([
        apiFetch<Measurable[]>(`/api/teams/${teamId}/measurables`, {}, currentUser.id),
        apiFetch<{ unsolved: Issue[]; solved: Issue[] }>(`/api/teams/${teamId}/issues`, {}, currentUser.id),
        apiFetch<{ todos: ToDo[]; last_closed_week_completion: any }>(`/api/teams/${teamId}/todos`, {}, currentUser.id),
        apiFetch<Rock[]>(`/api/teams/${teamId}/rocks`, {}, currentUser.id),
        apiFetch<User[]>(`/api/teams/${teamId}/members`, {}, currentUser.id),
      ]);

      setMeasurables(mRes);
      setUnsolvedIssues(issuesRes.unsolved);
      setSolvedIssues(issuesRes.solved);
      setTodos(todosRes.todos);
      setLastClosedWeekStat(todosRes.last_closed_week_completion);
      setRocks(rocksRes);
      setTeamMembers(membersRes);
    } catch (e: any) {
      console.error("Failed to load team data:", e);
      setError(e.message || "Access denied or failed to load team data.");
    } finally {
      setIsLoading(false);
    }
  }, [currentUser, teamId]);

  useEffect(() => {
    if (!authLoading) {
      loadData();
    }
  }, [authLoading, loadData]);

  if (authLoading || isLoading) {
    return (
      <div>
        <Header currentTeamId={teamId} />
        <div className="max-w-7xl mx-auto px-4 py-16 text-center text-gray-400 text-sm">
          Loading team workspace...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <Header currentTeamId={teamId} />
        <div className="max-w-xl mx-auto my-16 p-6 bg-white rounded-xl shadow-sm border border-rose-200 text-center space-y-4">
          <div className="w-12 h-12 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center mx-auto">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-gray-900">Access Restricted</h2>
          <p className="text-sm text-gray-600">{error}</p>
          <div className="text-xs text-gray-400">
            Current user: <strong>{currentUser?.name}</strong> ({currentUser?.role})
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-20">
      <Header currentTeamId={teamId} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Team Sub-Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-black text-gray-900 tracking-tight">{team?.name}</h1>
            <p className="text-xs text-gray-500 font-medium mt-0.5">
              Weekly numbers, quarterly rocks, tasks and issue resolution loop.
            </p>
          </div>

          <button
            onClick={loadData}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-600 hover:text-gray-900 bg-white hover:bg-gray-50 border border-gray-200 rounded-lg shadow-2xs font-semibold transition"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>

        {/* 1. Scorecard Section */}
        <ScorecardSection
          teamId={teamId}
          measurables={measurables}
          onRefresh={loadData}
        />

        {/* 2. Issues Section */}
        <IssuesSection
          teamId={teamId}
          unsolvedIssues={unsolvedIssues}
          solvedIssues={solvedIssues}
          teamMembers={teamMembers}
          onRefresh={loadData}
        />

        {/* 3. Grid: To-Dos & Rocks */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <TodosSection
            teamId={teamId}
            todos={todos}
            lastClosedWeekStat={lastClosedWeekStat}
            teamMembers={teamMembers}
            onRefresh={loadData}
          />

          <RocksSection rocks={rocks} />
        </div>
      </main>
    </div>
  );
}

