"use client";

import React, { useState } from "react";
import { Measurable, apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatWeekLabel } from "@/lib/utils";
import { AlertCircle, PlusCircle, Check, Loader2 } from "lucide-react";

interface ScorecardSectionProps {
  teamId: string;
  measurables: Measurable[];
  onRefresh: () => void;
  isMeetingMode?: boolean;
}

export const ScorecardSection: React.FC<ScorecardSectionProps> = ({
  teamId,
  measurables,
  onRefresh,
  isMeetingMode = false,
}) => {
  const { currentUser } = useAuth();
  const [editingCell, setEditingCell] = useState<{ measurableId: string; weekStart: string } | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [isSaving, setIsSaving] = useState(false);
  const [makingIssueFor, setMakingIssueFor] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const isObserver = currentUser?.role === "observer";

  const handleStartEdit = (mId: string, weekStart: string, currentVal: number | null) => {
    if (isObserver) return;
    setEditingCell({ measurableId: mId, weekStart });
    setEditValue(currentVal !== null ? String(currentVal) : "");
  };

  const handleSaveScore = async () => {
    if (!editingCell || !currentUser) return;
    const val = parseFloat(editValue);
    if (isNaN(val)) {
      setEditingCell(null);
      return;
    }

    setIsSaving(true);
    try {
      await apiFetch(
        `/api/measurables/${editingCell.measurableId}/scores/${editingCell.weekStart}`,
        {
          method: "PUT",
          body: JSON.stringify({ value: val }),
        },
        currentUser.id
      );
      setEditingCell(null);
      onRefresh();
    } catch (e: any) {
      alert(e.message || "Failed to update score");
    } finally {
      setIsSaving(false);
    }
  };

  const handleMakeIssue = async (measurableId: string, weekStart: string) => {
    if (isObserver || !currentUser) return;
    const key = `${measurableId}-${weekStart}`;
    setMakingIssueFor(key);
    try {
      const issue = await apiFetch<any>(
        `/api/teams/${teamId}/issues/make-from-measurable`,
        {
          method: "POST",
          body: JSON.stringify({
            measurable_id: measurableId,
            week_start: weekStart,
          }),
        },
        currentUser.id
      );
      setSuccessMsg(`Issue created/retrieved: "${issue.title}" (ID: ${issue.id})`);
      setTimeout(() => setSuccessMsg(null), 4000);
      onRefresh();
    } catch (e: any) {
      alert(e.message || "Failed to create issue");
    } finally {
      setMakingIssueFor(null);
    }
  };

  if (!measurables.length) {
    return <div className="p-8 text-center text-gray-500">No measurables found for this team.</div>;
  }

  const weeks = measurables[0]?.weeks || [];

  const formatGoal = (goal: any, unit: string) => {
    if (goal.type === "at_least") return `≥ ${goal.value} ${unit}`;
    if (goal.type === "at_most") return `≤ ${goal.value} ${unit}`;
    if (goal.type === "between") return `${goal.min} - ${goal.max} ${unit}`;
    if (goal.type === "exactly") return `= ${goal.value} ${unit}`;
    return unit;
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Scorecard</h2>
          <p className="text-xs text-gray-500">13-week KPI review. Click score to edit inline.</p>
        </div>
        {successMsg && (
          <div className="text-xs bg-emerald-50 text-emerald-800 border border-emerald-200 px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-medium animate-fadeIn">
            <Check className="w-3.5 h-3.5" /> {successMsg}
          </div>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-gray-100/75 text-gray-600 border-b border-gray-200 font-semibold tracking-wide">
              <th className="py-3 px-4 min-w-[180px] sticky left-0 bg-gray-100 z-10 shadow-sm">Measurable</th>
              <th className="py-3 px-3 min-w-[100px]">Owner</th>
              <th className="py-3 px-3 min-w-[90px]">Goal</th>
              {weeks.map((w, idx) => (
                <th
                  key={w.week_start}
                  className={`py-3 px-2 text-center min-w-[70px] ${
                    idx === weeks.length - 1 ? "bg-blue-50/70 text-blue-900 font-bold" : ""
                  }`}
                >
                  <div>{formatWeekLabel(w.week_start)}</div>
                  {idx === weeks.length - 1 && <div className="text-[10px] text-blue-600 font-normal">Current</div>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {measurables.map((m) => (
              <tr key={m.id} className="hover:bg-gray-50/80 transition-colors">
                <td className="py-3 px-4 font-medium text-gray-900 sticky left-0 bg-white group-hover:bg-gray-50 z-10 shadow-sm border-r border-gray-100">
                  <div className="font-semibold text-sm">{m.name}</div>
                  <div className="text-[11px] text-gray-400 font-normal">{m.unit}</div>
                </td>
                <td className="py-3 px-3 text-gray-600 text-xs">{m.owner_name || m.owner_id}</td>
                <td className="py-3 px-3 font-mono text-gray-700 text-xs whitespace-nowrap">
                  {formatGoal(m.goal, m.unit)}
                </td>

                {m.weeks.map((w, idx) => {
                  const isEditing =
                    editingCell?.measurableId === m.id && editingCell?.weekStart === w.week_start;
                  const isOffTrack = w.status === "off_track";
                  const isOnTrack = w.status === "on_track";
                  const isPending = w.status === "pending";
                  const isMaking = makingIssueFor === `${m.id}-${w.week_start}`;

                  let bgClass = "bg-gray-50 text-gray-400";
                  if (isOnTrack) bgClass = "bg-emerald-50 text-emerald-800 border-emerald-200";
                  if (isOffTrack) bgClass = "bg-rose-50 text-rose-800 border-rose-200";
                  if (isPending) bgClass = "bg-amber-50 text-amber-700 border-amber-200";

                  return (
                    <td
                      key={w.week_start}
                      className={`p-1.5 text-center border-l border-gray-100 relative group/cell ${
                        idx === weeks.length - 1 ? "border-l-2 border-l-blue-200" : ""
                      }`}
                    >
                      {isEditing ? (
                        <div className="flex items-center justify-center">
                          <input
                            type="number"
                            step="any"
                            autoFocus
                            disabled={isSaving}
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleSaveScore();
                              if (e.key === "Escape") setEditingCell(null);
                            }}
                            onBlur={handleSaveScore}
                            className="w-16 px-1.5 py-0.5 text-center text-xs font-bold border-2 border-blue-600 rounded bg-white shadow-sm focus:outline-none"
                          />
                        </div>
                      ) : (
                        <div
                          onClick={() => handleStartEdit(m.id, w.week_start, w.value)}
                          className={`min-h-[34px] flex flex-col items-center justify-center rounded border px-1 py-0.5 transition ${bgClass} ${
                            !isObserver ? "cursor-pointer hover:ring-2 hover:ring-blue-400 hover:ring-opacity-50" : ""
                          }`}
                          title={!isObserver ? "Click to edit score" : undefined}
                        >
                          <span className="font-semibold text-xs font-mono">
                            {w.value !== null ? w.value : "—"}
                          </span>

                          {/* Make it an Issue button on off-track cells */}
                          {isOffTrack && !isObserver && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleMakeIssue(m.id, w.week_start);
                              }}
                              disabled={isMaking}
                              className="mt-0.5 inline-flex items-center gap-0.5 text-[10px] text-rose-700 hover:text-rose-900 bg-white/80 hover:bg-white px-1 py-0.5 rounded shadow-xs border border-rose-300 font-medium transition"
                              title="Make it an Issue"
                            >
                              {isMaking ? (
                                <Loader2 className="w-2.5 h-2.5 animate-spin" />
                              ) : (
                                <AlertCircle className="w-2.5 h-2.5 text-rose-600" />
                              )}
                              Issue
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

