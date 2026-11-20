"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Team, apiFetch } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const { currentUser, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading || !currentUser) return;
    async function redirect() {
      try {
        const teams = await apiFetch<Team[]>("/api/teams", {}, currentUser!.id);
        if (teams.length > 0) {
          router.replace(`/teams/${teams[0].id}`);
        }
      } catch (e) {
        console.error(e);
      }
    }
    redirect();
  }, [currentUser, isLoading, router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-gray-400 text-sm">Loading workspace...</div>
    </div>
  );
}

