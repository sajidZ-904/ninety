"use client";

import React, { useState } from "react";
import { Rock } from "@/lib/api";
import { ChevronDown, ChevronRight, CheckCircle2, Circle, Mountain, AlertTriangle } from "lucide-react";

interface RocksSectionProps {
  rocks: Rock[];
}

export const RocksSection: React.FC<RocksSectionProps> = ({ rocks }) => {
  const [expandedRockIds, setExpandedRockIds] = useState<Set<string>>(new Set());

  const toggleExpand = (rockId: string) => {
    setExpandedRockIds((prev) => {
      const next = new Set(prev);
      if (next.has(rockId)) next.delete(rockId);
      else next.add(rockId);
      return next;
    });
  };

  const getStatusBadge = (status: string) => {
    if (status === "complete") {
      return (
        <span className="px-2 py-0.5 rounded text-xs font-bold bg-blue-100 text-blue-800 border border-blue-200">
          Complete
        </span>
      );
    }
    if (status === "off_track") {
      return (
        <span className="px-2 py-0.5 rounded text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">
          Off Track
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
        On Track
      </span>
    );
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Rocks (Current Quarter)</h2>
          <p className="text-xs text-gray-500">90-day priorities with milestone progress. (Read-only)</p>
        </div>
      </div>

      {/* List */}
      <div className="divide-y divide-gray-100">
        {rocks.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">No Rocks for this quarter.</div>
        ) : (
          rocks.map((rock) => {
            const isExpanded = expandedRockIds.has(rock.id);
            const totalMs = rock.milestones.length;
            const completedMs = rock.milestones.filter((m) => m.done).length;

            return (
              <div key={rock.id} className="transition">
                <div
                  onClick={() => toggleExpand(rock.id)}
                  className="p-4 hover:bg-gray-50/60 transition cursor-pointer flex items-center justify-between gap-4"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <button className="text-gray-400 hover:text-gray-600 shrink-0">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </button>

                    <div className="space-y-1 flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-gray-900">{rock.title}</span>
                        {getStatusBadge(rock.status)}
                      </div>

                      <div className="text-xs text-gray-500 flex items-center gap-3">
                        <span>Owner: <strong className="text-gray-700">{rock.owner_name || rock.owner_id}</strong></span>
                        <span>•</span>
                        <span>{rock.quarter}</span>
                        {totalMs > 0 && (
                          <>
                            <span>•</span>
                            <span>{completedMs}/{totalMs} Milestones</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="flex items-center gap-3 w-44 shrink-0">
                    <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${
                          rock.status === "complete"
                            ? "bg-blue-600"
                            : rock.status === "off_track"
                            ? "bg-rose-500"
                            : "bg-emerald-500"
                        }`}
                        style={{ width: `${rock.progress_percent}%` }}
                      />
                    </div>
                    <span className="font-mono text-xs font-bold text-gray-700 min-w-[36px] text-right">
                      {rock.progress_percent}%
                    </span>
                  </div>
                </div>

                {/* Expanded Milestones */}
                {isExpanded && (
                  <div className="bg-gray-50/80 px-12 py-3 border-t border-b border-gray-100 space-y-2">
                    <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Milestones
                    </div>

                    {rock.milestones.length === 0 ? (
                      <div className="text-xs text-gray-400 italic">No milestones defined for this rock.</div>
                    ) : (
                      rock.milestones.map((ms) => (
                        <div key={ms.id} className="flex items-center justify-between text-xs py-1">
                          <div className="flex items-center gap-2">
                            {ms.done ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                            ) : (
                              <Circle className="w-4 h-4 text-gray-400" />
                            )}
                            <span className={ms.done ? "line-through text-gray-400" : "text-gray-800 font-medium"}>
                              {ms.title}
                            </span>
                          </div>

                          <span className="text-gray-500 font-mono text-[11px]">Due: {ms.due_date}</span>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

