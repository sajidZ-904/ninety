"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  MeetingState, Measurable, Issue, ToDo, User, MeetingSummary, apiFetch
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ScorecardSection } from "@/components/ScorecardSection";
import { IssuesSection } from "@/components/IssuesSection";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Clock, CheckCircle, ArrowRight, UserCheck, Star, Users,
  AlertTriangle, Shield, Check, Award, VideoOff, Home
} from "lucide-react";

interface MeetingRoomProps {
  teamId: string;
  initialMeeting: MeetingState;
  measurables: Measurable[];
  unsolvedIssues: Issue[];
  solvedIssues: Issue[];
  teamMembers: User[];
  onRefreshData: () => void;
}

export const MeetingRoom: React.FC<MeetingRoomProps> = ({
  teamId,
  initialMeeting,
  measurables,
  unsolvedIssues,
  solvedIssues,
  teamMembers,
  onRefreshData,
}) => {
  const router = useRouter();
  const { currentUser } = useAuth();
  const [meeting, setMeeting] = useState<MeetingState>(initialMeeting);
  const [summary, setSummary] = useState<MeetingSummary | null>(null);
  const [myRating, setMyRating] = useState<number | null>(null);
  const [timerSeconds, setTimerSeconds] = useState<number>(initialMeeting.section_elapsed_seconds);
  const [isAdvancing, setIsAdvancing] = useState(false);
  const [isEnding, setIsEnding] = useState(false);

  // APP_NOW is fixed for deterministic business rules, so the timer is driven
  // by the server's elapsed seconds plus a local stopwatch from receipt time.
  const timerBaseRef = useRef<{ seconds: number; receivedAt: number }>({
    seconds: initialMeeting.section_elapsed_seconds,
    receivedAt: Date.now(),
  });

  const applyMeeting = useCallback((next: MeetingState) => {
    timerBaseRef.current = {
      seconds: next.section_elapsed_seconds,
      receivedAt: Date.now(),
    };
    setMeeting(next);
    setTimerSeconds(next.section_elapsed_seconds);
  }, []);

  const fetchSummary = useCallback(
    async (meetingId: string) => {
      if (!currentUser) return;
      try {
        const data = await apiFetch<MeetingSummary>(
          `/api/meetings/${meetingId}/summary`,
          {},
          currentUser.id
        );
        setSummary(data);
      } catch (e) {
        console.error("Failed to load summary:", e);
      }
    },
    [currentUser]
  );

  // Determine if current user is facilitator
  const isFacilitator = currentUser?.id === meeting.facilitator_id;
  const isObserver = currentUser?.role === "observer";

  // Connect WebSocket for live sync; reconnect if the socket drops.
  useEffect(() => {
    if (!currentUser) return;
    let disposed = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let ws: WebSocket | null = null;

    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      // REST goes through the Next.js /api rewrite, but Next does not proxy
      // WebSocket upgrades. Talk to the backend's published port directly in
      // local setups, and allow an explicit override behind a real proxy.
      const configuredWs = process.env.NEXT_PUBLIC_WS_URL;
      const isLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);
      const origin = configuredWs
        ? configuredWs.replace(/^http/, "ws")
        : `${protocol}//${isLocal ? `${window.location.hostname}:8000` : window.location.host}`;
      const wsUrl = `${origin}/api/meetings/${teamId}/ws?user_id=${encodeURIComponent(currentUser.id)}`;

      try {
        ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (
              msg.type === "meeting_updated" ||
              msg.type === "meeting_started" ||
              msg.type === "meeting_ended"
            ) {
              applyMeeting(msg.meeting);
              if (msg.meeting.status === "ended") {
                fetchSummary(msg.meeting.id);
              }
            }
            if (
              msg.type === "score_updated" ||
              msg.type === "issue_created" ||
              msg.type === "issue_solved" ||
              msg.type === "issue_priority_updated" ||
              msg.type === "todo_created" ||
              msg.type === "todo_updated"
            ) {
              onRefreshData();
            }
          } catch (e) {
            console.error("WS error:", e);
          }
        };

        ws.onclose = () => {
          if (!disposed) retryTimer = setTimeout(connect, 2000);
        };
        ws.onerror = () => ws?.close();
      } catch (e) {
        console.warn("Could not establish WebSocket:", e);
      }
    };

    connect();
    return () => {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      ws?.close();
    };
  }, [teamId, currentUser, applyMeeting, fetchSummary, onRefreshData]);

  // Safety-net polling: the WebSocket normally delivers changes instantly, but
  // a dropped or blocked socket (proxies, reconnects) must not desync an
  // attendee, so reconcile against the server every second.
  useEffect(() => {
    if (!currentUser || meeting.status === "ended") return;
    const interval = setInterval(async () => {
      try {
        const fresh = await apiFetch<MeetingState | null>(
          `/api/teams/${teamId}/meetings/current`,
          {},
          currentUser.id
        );
        if (fresh && fresh.id === meeting.id) {
          applyMeeting(fresh);
          return;
        }
        if (!fresh) {
          const ended = await apiFetch<MeetingState | null>(
            `/api/teams/${teamId}/meetings/latest-ended`,
            {},
            currentUser.id
          );
          if (ended && ended.id === meeting.id) {
            applyMeeting(ended);
            fetchSummary(ended.id);
          }
        }
      } catch {
        // transient network error; the next tick retries
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [currentUser, teamId, meeting.id, meeting.status, applyMeeting, fetchSummary]);

  // Auto-join meeting if user is reading an active meeting
  useEffect(() => {
    if (!currentUser || meeting.status === "ended") return;
    async function autoJoin() {
      try {
        await apiFetch(`/api/meetings/${meeting.id}/join`, { method: "POST" }, currentUser!.id);
      } catch (e) {
        console.warn("Auto join error:", e);
      }
    }
    autoJoin();
  }, [meeting.id, meeting.status, currentUser]);

  // Fetch summary if meeting ended
  useEffect(() => {
    if (meeting.status === "ended") {
      fetchSummary(meeting.id);
    }
  }, [meeting.status, meeting.id, fetchSummary]);

  // Local ticker between server updates; every update re-anchors the base.
  useEffect(() => {
    if (meeting.status === "ended") return;

    const tick = () => {
      const base = timerBaseRef.current;
      setTimerSeconds(base.seconds + Math.floor((Date.now() - base.receivedAt) / 1000));
    };
    tick();
    const interval = setInterval(tick, 1000);

    return () => clearInterval(interval);
  }, [meeting.status]);

  // Read existing rating
  useEffect(() => {
    if (!currentUser) return;
    const found = meeting.ratings.find((r) => r.user_id === currentUser.id);
    if (found) setMyRating(found.rating);
  }, [meeting.ratings, currentUser]);

  const handleAdvance = async () => {
    if (!isFacilitator || !currentUser) return;
    setIsAdvancing(true);
    try {
      const updated = await apiFetch<MeetingState>(
        `/api/meetings/${meeting.id}/advance`,
        { method: "POST" },
        currentUser.id
      );
      applyMeeting(updated);
      if (updated.status === "ended") fetchSummary(updated.id);
    } catch (e: any) {
      alert(e.message || "Failed to advance section");
    } finally {
      setIsAdvancing(false);
    }
  };

  const handleEndMeeting = async () => {
    if (!isFacilitator || !currentUser) return;
    if (!confirm("Are you sure you want to end this Level 10 Meeting?")) return;
    setIsEnding(true);
    try {
      const updated = await apiFetch<MeetingState>(
        `/api/meetings/${meeting.id}/end`,
        { method: "POST" },
        currentUser.id
      );
      applyMeeting(updated);
      fetchSummary(updated.id);
    } catch (e: any) {
      alert(e.message || "Failed to end meeting");
    } finally {
      setIsEnding(false);
    }
  };

  const handleRate = async (rating: number) => {
    if (!currentUser || isObserver) return;
    setMyRating(rating);
    try {
      await apiFetch(
        `/api/meetings/${meeting.id}/rate`,
        {
          method: "POST",
          body: JSON.stringify({ rating }),
        },
        currentUser.id
      );
      // Refresh the shared ratings tally in case the socket is unavailable.
      const fresh = await apiFetch<MeetingState | null>(
        `/api/teams/${teamId}/meetings/current`,
        {},
        currentUser.id
      );
      if (fresh && fresh.id === meeting.id) applyMeeting(fresh);
    } catch (e: any) {
      alert(e.message || "Failed to submit rating");
    }
  };

  // Format timer
  const allocated = meeting.section_allocated_seconds;
  const remaining = allocated - timerSeconds;
  const isOvertime = remaining < 0;

  const formatTime = (secs: number) => {
    const abs = Math.abs(secs);
    const m = Math.floor(abs / 60);
    const s = abs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  // Meeting Ended View
  if (meeting.status === "ended") {
    return (
      <div className="max-w-4xl mx-auto py-10 px-4">
        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
          <div className="p-8 bg-gradient-to-r from-blue-600 to-indigo-700 text-white flex items-center justify-between">
            <div>
              <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/20 rounded-full text-xs font-semibold backdrop-blur-sm mb-3">
                <CheckCircle className="w-3.5 h-3.5" /> Meeting Completed
              </div>
              <h1 className="text-2xl font-bold">Level 10 Meeting Summary</h1>
              <p className="text-blue-100 text-sm mt-1">
                Scorecard Week Reviewed: <strong>{summary?.scorecard_week || meeting.scorecard_week}</strong>
              </p>
            </div>

            <button
              onClick={() => router.push(`/teams/${teamId}`)}
              className="flex items-center gap-2 px-4 py-2 bg-white text-blue-700 font-bold rounded-lg shadow hover:bg-blue-50 transition text-sm"
            >
              <Home className="w-4 h-4" /> Back to Team
            </button>
          </div>

          <div className="p-8 space-y-6">
            {/* Rating Banner */}
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-amber-500 text-white flex items-center justify-center font-black text-xl shadow">
                  ★
                </div>
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider text-amber-800">Average Meeting Rating</div>
                  <div className="text-2xl font-black text-amber-950 font-mono">
                    {summary?.rating !== null ? `${summary?.rating} / 10` : "No ratings"}
                  </div>
                </div>
              </div>

              <div className="text-xs text-amber-800 font-medium">
                {meeting.ratings.length} of {meeting.attendees.length} attendees rated
              </div>
            </div>

            {/* Attendees & Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
                <div className="text-xs font-semibold text-gray-500 uppercase">Attendees ({meeting.attendees.length})</div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {meeting.attendees.map((id) => {
                    const member = teamMembers.find((m) => m.id === id);
                    return (
                      <span key={id} className="px-2.5 py-1 bg-white text-gray-800 rounded-md text-xs font-medium border border-gray-200">
                        {member?.name || id}
                      </span>
                    );
                  })}
                </div>
              </div>

              <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
                <div className="text-xs font-semibold text-gray-500 uppercase">Issues Solved ({summary?.issues_solved.length || 0})</div>
                <div className="mt-2 space-y-1">
                  {summary?.issues_solved.length === 0 ? (
                    <div className="text-xs text-gray-400 italic">No issues solved</div>
                  ) : (
                    summary?.issues_solved.map((id) => {
                      const solved = meeting.solved_issues.find((i) => i.id === id);
                      return (
                        <div key={id} className="text-xs font-medium text-emerald-800 flex items-center gap-1">
                          <Check className="w-3 h-3 text-emerald-600 shrink-0" />
                          <span className="truncate">{solved?.title || id}</span>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
                <div className="text-xs font-semibold text-gray-500 uppercase">To-Dos Created ({summary?.todos_created.length || 0})</div>
                <div className="mt-2 space-y-1">
                  {summary?.todos_created.length === 0 ? (
                    <div className="text-xs text-gray-400 italic">No To-Dos created</div>
                  ) : (
                    summary?.todos_created.map((id) => {
                      const todo = meeting.new_todos.find((t) => t.id === id);
                      return (
                        <div key={id} className="text-xs font-medium text-blue-800 flex items-center gap-1">
                          <Check className="w-3 h-3 text-blue-600 shrink-0" />
                          <span className="truncate">{todo?.title || id}</span>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>

            {/* Scorecard Week Measurable Statuses */}
            {summary?.measurable_status && (
              <div className="border border-gray-200 rounded-xl overflow-hidden">
                <div className="bg-gray-100 px-4 py-2 text-xs font-bold text-gray-700 uppercase tracking-wider">
                  Measurables Status for Reviewed Week ({summary.scorecard_week})
                </div>
                <div className="divide-y divide-gray-100">
                  {Object.entries(summary.measurable_status).map(([mId, stat]) => {
                    const mObj = measurables.find((m) => m.id === mId);
                    return (
                      <div key={mId} className="px-4 py-2.5 flex items-center justify-between text-xs">
                        <span className="font-semibold text-gray-800">{mObj?.name || mId}</span>
                        <Badge
                          variant={stat === "on_track" ? "success" : "destructive"}
                          className="uppercase tracking-wide text-[10px]"
                        >
                          {stat.replace("_", " ")}
                        </Badge>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Active Meeting View
  return (
    <div className="space-y-6">
      {/* Top Meeting Control & Agenda Bar */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Agenda Tabs */}
          <div className="flex items-center gap-2">
            {[
              { id: "scorecard", label: "Scorecard", time: "5 min" },
              { id: "ids", label: "IDS", time: "60 min" },
              { id: "conclude", label: "Conclude", time: "10 min" },
            ].map((sec, idx) => {
              const isCurrent = meeting.current_section === sec.id;
              return (
                <div
                  key={sec.id}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition border ${
                    isCurrent
                      ? "bg-blue-600 text-white border-blue-600 shadow-sm"
                      : "bg-gray-50 text-gray-600 border-gray-200"
                  }`}
                >
                  <span className="w-4 h-4 rounded-full bg-white/20 flex items-center justify-center text-[10px]">
                    {idx + 1}
                  </span>
                  <span>{sec.label}</span>
                  <span className={`text-[10px] font-normal ${isCurrent ? "text-blue-100" : "text-gray-400"}`}>
                    ({sec.time})
                  </span>
                </div>
              );
            })}
          </div>

          {/* Section Timer (Server-Owned) */}
          <div className="flex items-center gap-4">
            <div
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg border font-mono text-sm font-bold shadow-xs ${
                isOvertime
                  ? "bg-rose-50 text-rose-800 border-rose-300 animate-pulse"
                  : "bg-gray-100 text-gray-900 border-gray-300"
              }`}
            >
              <Clock className={`w-4 h-4 ${isOvertime ? "text-rose-600" : "text-gray-500"}`} />
              <span>{isOvertime ? `+${formatTime(timerSeconds - allocated)}` : formatTime(remaining)}</span>
              {isOvertime && (
                <span className="text-[10px] uppercase font-sans tracking-wide bg-rose-200 px-1 rounded text-rose-900">
                  Over Time
                </span>
              )}
            </div>

            {/* Facilitator Controls */}
            {isFacilitator && (
              <div className="flex items-center gap-2">
                <Button onClick={handleAdvance} disabled={isAdvancing} size="sm">
                  {meeting.current_section === "conclude" ? "End Meeting" : "Next Section"}
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>

                <Button
                  onClick={handleEndMeeting}
                  disabled={isEnding}
                  size="sm"
                  variant="outline"
                  className="border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100"
                >
                  End
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Meeting Info & Presence */}
        <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-gray-100">
          <div className="flex items-center gap-2">
            <span>Facilitator: <strong className="text-gray-800">{meeting.facilitator_name || meeting.facilitator_id}</strong></span>
            <span>•</span>
            <span>Reviewing Week: <strong className="text-gray-800">{meeting.scorecard_week}</strong></span>
          </div>

          <div className="flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5 text-gray-400" />
            <span className="font-semibold text-gray-700">In Room:</span>
            <div className="flex gap-1">
              {meeting.attendees.map((id) => {
                const member = teamMembers.find((m) => m.id === id);
                return (
                  <span key={id} className="px-2 py-0.5 bg-gray-100 text-gray-800 rounded font-medium text-[11px]">
                    {member?.name || id}
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Main Agenda Section Body */}
      {meeting.current_section === "scorecard" && (
        <div className="space-y-4">
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900 font-medium">
            <strong>Scorecard Phase (5 min):</strong> Review last closed week's scores. Off-track numbers should be dropped down to the Issues list using <em>"Make it an Issue"</em>.
          </div>
          <ScorecardSection
            teamId={teamId}
            measurables={measurables}
            onRefresh={onRefreshData}
            isMeetingMode={true}
          />
        </div>
      )}

      {meeting.current_section === "ids" && (
        <div className="space-y-4">
          <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg text-xs text-purple-900 font-medium">
            <strong>IDS Phase (60 min):</strong> Identify root causes, Discuss solutions, and Solve issues by assigning 7-day To-Dos to teammates.
          </div>
          <IssuesSection
            teamId={teamId}
            unsolvedIssues={unsolvedIssues}
            solvedIssues={solvedIssues}
            teamMembers={teamMembers}
            onRefresh={onRefreshData}
            isMeetingMode={true}
          />
        </div>
      )}

      {meeting.current_section === "conclude" && (
        <div className="space-y-6">
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-900 font-medium">
            <strong>Conclude Phase (10 min):</strong> Recap newly created To-Dos, and every attendee rates the meeting from 1 to 10.
          </div>

          {/* Newly Created To-Dos recap */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
            <h3 className="text-base font-bold text-gray-900">
              New To-Dos Created During This Meeting ({meeting.new_todos.length})
            </h3>
            {meeting.new_todos.length === 0 ? (
              <div className="text-xs text-gray-400 italic">No To-Dos were created in this meeting.</div>
            ) : (
              <div className="divide-y divide-gray-100">
                {meeting.new_todos.map((todo) => (
                  <div key={todo.id} className="py-2.5 flex items-center justify-between text-xs">
                    <span className="font-semibold text-gray-800">{todo.title}</span>
                    <span className="text-gray-500">
                      Owner: <strong>{todo.owner_name || todo.owner_id}</strong> (Due {todo.due_date})
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Meeting Rating Card */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-gray-900">Rate This Meeting (1 to 10)</h3>
                <p className="text-xs text-gray-500">
                  Aim for an 8+ average. Be honest to help your team improve weekly meetings.
                </p>
              </div>

              {/* Current Average */}
              {meeting.ratings.length > 0 && (
                <div className="text-right">
                  <div className="text-xs text-gray-400">Current Average</div>
                  <div className="text-xl font-black font-mono text-blue-600">
                    {(
                      meeting.ratings.reduce((acc, r) => acc + r.rating, 0) / meeting.ratings.length
                    ).toFixed(1)}
                  </div>
                </div>
              )}
            </div>

            {/* Rating Buttons */}
            {!isObserver ? (
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 flex-wrap">
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                    <button
                      key={num}
                      onClick={() => handleRate(num)}
                      className={`w-10 h-10 rounded-lg text-sm font-bold transition flex items-center justify-center border shadow-xs ${
                        myRating === num
                          ? "bg-amber-500 text-white border-amber-600 scale-105"
                          : "bg-gray-50 text-gray-700 hover:bg-gray-100 border-gray-200"
                      }`}
                    >
                      {num}
                    </button>
                  ))}
                </div>
                {myRating && (
                  <div className="text-xs text-emerald-700 font-medium flex items-center gap-1">
                    <Check className="w-3.5 h-3.5" /> Your submitted rating: <strong>{myRating} / 10</strong> (can be changed until meeting ends)
                  </div>
                )}
              </div>
            ) : (
              <div className="text-xs text-gray-400 italic">Observers cannot submit ratings.</div>
            )}

            {/* Submitted Ratings from attendees */}
            <div className="pt-4 border-t border-gray-100 space-y-2">
              <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Submitted Ratings ({meeting.ratings.length} / {meeting.attendees.length})
              </div>
              <div className="flex flex-wrap gap-2">
                {meeting.attendees.map((id) => {
                  const ratingObj = meeting.ratings.find((r) => r.user_id === id);
                  const member = teamMembers.find((m) => m.id === id);
                  return (
                    <span
                      key={id}
                      className={`px-3 py-1 rounded-md text-xs font-medium border flex items-center gap-1.5 ${
                        ratingObj
                          ? "bg-amber-50 text-amber-900 border-amber-200 font-bold"
                          : "bg-gray-50 text-gray-400 border-gray-200"
                      }`}
                    >
                      {member?.name || id}: {ratingObj ? `${ratingObj.rating} ★` : "Waiting..."}
                    </span>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

