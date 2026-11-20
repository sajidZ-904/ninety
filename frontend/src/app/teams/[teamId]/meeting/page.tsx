"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Header } from "@/components/Header";
import { MeetingRoom } from "@/components/MeetingRoom";
import {
  MeetingState, Measurable, Issue, User, apiFetch
} from "@/lib/api";
import { Video, ArrowLeft } from "lucide-react";

export default function MeetingPage() {
  const params = useParams();
  const router = useRouter();
  const teamId = params.teamId as string;
  const { currentUser, isLoading: authLoading } = useAuth();

  const [meeting, setMeeting] = useState<MeetingState | null>(null);
  const [measurables, setMeasurables] = useState<Measurable[]>([]);
  const [unsolvedIssues, setUnsolvedIssues] = useState<Issue[]>([]);
  const [solvedIssues, setSolvedIssues] = useState<Issue[]>([]);
  const [teamMembers, setTeamMembers] = useState<User[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [noMeetingYet, setNoMeetingYet] = useState(false);

  const loadMeetingAndData = useCallback(async () => {
    if (!currentUser || !teamId) return;

    try {
      // 1. Get current meeting; fall back to the most recent ended meeting so
      //    a refreshed or late-joining browser still sees the final summary.
      let meetingData = await apiFetch<MeetingState | null>(
        `/api/teams/${teamId}/meetings/current`,
        {},
        currentUser.id
      );

      if (!meetingData) {
        meetingData = await apiFetch<MeetingState | null>(
          `/api/teams/${teamId}/meetings/latest-ended`,
          {},
          currentUser.id
        );
      }

      if (!meetingData) {
        // The room may have been opened before a meeting started; keep watching
        // so the page swaps into the room as soon as one exists.
        setNoMeetingYet(true);
        setError("No active Level 10 Meeting for this team.");
        setIsLoading(false);
        return;
      }

      setNoMeetingYet(false);
      setError(null);
      setMeeting(meetingData);

      // 2. Fetch measurables, issues, members
      const [mRes, issuesRes, membersRes] = await Promise.all([
        apiFetch<Measurable[]>(`/api/teams/${teamId}/measurables`, {}, currentUser.id),
        apiFetch<{ unsolved: Issue[]; solved: Issue[] }>(`/api/teams/${teamId}/issues`, {}, currentUser.id),
        apiFetch<User[]>(`/api/teams/${teamId}/members`, {}, currentUser.id),
      ]);

      setMeasurables(mRes);
      setUnsolvedIssues(issuesRes.unsolved);
      setSolvedIssues(issuesRes.solved);
      setTeamMembers(membersRes);
    } catch (e: any) {
      console.error("Meeting page load error:", e);
      setError(e.message || "Failed to load meeting room.");
    } finally {
      setIsLoading(false);
    }
  }, [currentUser, teamId]);

  useEffect(() => {
    if (!authLoading) {
      loadMeetingAndData();
    }
  }, [authLoading, loadMeetingAndData]);

  useEffect(() => {
    if (authLoading || !noMeetingYet) return;
    const interval = setInterval(loadMeetingAndData, 5000);
    return () => clearInterval(interval);
  }, [authLoading, noMeetingYet, loadMeetingAndData]);

  if (authLoading || isLoading) {
    return (
      <div>
        <Header currentTeamId={teamId} />
        <div className="max-w-7xl mx-auto px-4 py-16 text-center text-gray-400 text-sm">
          Connecting to Level 10 Meeting Room...
        </div>
      </div>
    );
  }

  if (error || !meeting) {
    return (
      <div>
        <Header currentTeamId={teamId} />
        <div className="max-w-md mx-auto my-16 p-6 bg-white rounded-xl shadow-sm border border-gray-200 text-center space-y-4">
          <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mx-auto">
            <Video className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-gray-900">Meeting Room</h2>
          <p className="text-sm text-gray-500">{error || "No active meeting"}</p>
          <button
            onClick={() => router.push(`/teams/${teamId}`)}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm"
          >
            <ArrowLeft className="w-4 h-4" /> Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-20">
      <Header currentTeamId={teamId} />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <MeetingRoom
          teamId={teamId}
          initialMeeting={meeting}
          measurables={measurables}
          unsolvedIssues={unsolvedIssues}
          solvedIssues={solvedIssues}
          teamMembers={teamMembers}
          onRefreshData={loadMeetingAndData}
        />
      </main>
    </div>
  );
}

