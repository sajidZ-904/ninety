"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Team, MeetingState, apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Users, Video, ShieldAlert, Award, Eye, ChevronDown } from "lucide-react";

interface HeaderProps {
  currentTeamId?: string;
}

export const Header: React.FC<HeaderProps> = ({ currentTeamId }) => {
  const router = useRouter();
  const { currentUser, users, switchUser } = useAuth();
  const [teams, setTeams] = useState<Team[]>([]);
  const [activeMeeting, setActiveMeeting] = useState<MeetingState | null>(null);
  const [isStartingMeeting, setIsStartingMeeting] = useState(false);

  useEffect(() => {
    if (!currentUser) return;
    async function loadTeamsAndMeeting() {
      try {
        const teamsData = await apiFetch<Team[]>("/api/teams", {}, currentUser!.id);
        setTeams(teamsData);

        if (currentTeamId) {
          try {
            const meetingData = await apiFetch<MeetingState | null>(
              `/api/teams/${currentTeamId}/meetings/current`,
              {},
              currentUser!.id
            );
            setActiveMeeting(meetingData);
          } catch {
            setActiveMeeting(null);
          }
        }
      } catch (e) {
        console.error("Error loading header data:", e);
      }
    }
    loadTeamsAndMeeting();
    const interval = setInterval(loadTeamsAndMeeting, 5000);
    return () => clearInterval(interval);
  }, [currentUser, currentTeamId]);

  const handleStartOrJoinMeeting = async () => {
    if (!currentTeamId || !currentUser) return;
    const meetingPath = `/teams/${currentTeamId}/meeting`;
    if (activeMeeting) {
      // Pushing the current route is a no-op in the App Router, which reads as
      // "the button does nothing" if the room page was opened before the meeting
      // started. Reload so the room always fetches the live meeting state.
      if (window.location.pathname === meetingPath) {
        window.location.reload();
      } else {
        router.push(meetingPath);
      }
      return;
    }
    if (currentUser.role === "observer") {
      alert("Observers cannot start meetings.");
      return;
    }

    setIsStartingMeeting(true);
    try {
      await apiFetch<MeetingState>(
        `/api/teams/${currentTeamId}/meetings/start`,
        { method: "POST" },
        currentUser.id
      );
      router.push(meetingPath);
    } catch (e: any) {
      alert(e.message || "Failed to start meeting");
    } finally {
      setIsStartingMeeting(false);
    }
  };

  const getRoleBadge = (role?: string) => {
    if (role === "admin") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-purple-100 text-purple-800 border border-purple-200">
          <Award className="w-3 h-3" /> Admin
        </span>
      );
    }
    if (role === "observer") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-700 border border-gray-300">
          <Eye className="w-3 h-3" /> Observer
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
        <Users className="w-3 h-3" /> Member
      </span>
    );
  };

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Brand & Team Switcher */}
        <div className="flex items-center space-x-6">
          <div
            onClick={() => router.push(currentTeamId ? `/teams/${currentTeamId}` : "/")}
            className="cursor-pointer flex items-center space-x-2"
          >
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white font-black text-xl shadow">
              90
            </div>
            <div>
              <span className="font-bold text-gray-900 text-base tracking-tight block">Ninety EOS</span>
              <span className="text-xs text-gray-500 font-medium block -mt-1">Level 10 Meeting</span>
            </div>
          </div>

          {/* Team Switcher */}
          <div className="relative">
            <select
              value={currentTeamId || ""}
              onChange={(e) => router.push(`/teams/${e.target.value}`)}
              className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-44 p-2 font-medium"
            >
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Right: Meeting Button & User Switcher */}
        <div className="flex items-center space-x-4">
          {/* L10 Meeting Action Button */}
          {currentTeamId && (
            <Button
              onClick={handleStartOrJoinMeeting}
              disabled={isStartingMeeting || (!activeMeeting && currentUser?.role === "observer")}
              variant={activeMeeting ? "success" : "default"}
              className={
                activeMeeting
                  ? "animate-pulse"
                  : currentUser?.role === "observer"
                  ? "bg-gray-200 text-gray-400"
                  : undefined
              }
            >
              <Video className="w-4 h-4" />
              {activeMeeting ? "Join Live Meeting" : "Start Level 10"}
            </Button>
          )}

          {/* User Switcher */}
          <div className="flex items-center gap-3 pl-3 border-l border-gray-200">
            <div className="text-right">
              <div className="text-sm font-semibold text-gray-800">{currentUser?.name}</div>
              <div>{getRoleBadge(currentUser?.role)}</div>
            </div>

            <select
              value={currentUser?.id || "u1"}
              onChange={(e) => switchUser(e.target.value)}
              className="bg-gray-50 border border-gray-300 text-gray-700 text-xs rounded-lg p-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer"
            >
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name} ({u.role.replace("_", " ")})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </header>
  );
};

