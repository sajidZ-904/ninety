"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { User, apiFetch } from "./api";

interface AuthContextType {
  currentUser: User | null;
  users: User[];
  switchUser: (userId: string) => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  currentUser: null,
  users: [],
  switchUser: () => {},
  isLoading: true,
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [users, setUsers] = useState<User[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadUsers() {
      try {
        const data = await apiFetch<User[]>("/api/users", {}, "u1");
        setUsers(data);
        const savedId = localStorage.getItem("ninety_user_id") || "u1";
        const found = data.find((u) => u.id === savedId) || data[0];
        setCurrentUser(found);
      } catch (e) {
        console.error("Failed to load users:", e);
      } finally {
        setIsLoading(false);
      }
    }
    loadUsers();
  }, []);

  const switchUser = (userId: string) => {
    const found = users.find((u) => u.id === userId);
    if (found) {
      setCurrentUser(found);
      localStorage.setItem("ninety_user_id", userId);
    }
  };

  return (
    <AuthContext.Provider value={{ currentUser, users, switchUser, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

