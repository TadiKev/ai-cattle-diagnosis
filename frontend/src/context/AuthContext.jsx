// FILE: src/context/AuthContext.jsx
import React, { createContext, useContext, useEffect, useState } from "react";
import {
  loginUser,
  registerUser,
  fetchProfile,
  setAuthToken,
  logout as doLogout,
} from "../lib/api";

/**
 * AuthContext
 *
 * Responsibilities:
 * - On app start, read token from localStorage and populate `user` by calling fetchProfile()
 * - Provide login/register/logout helpers that keep token + profile in sync
 * - Expose `user`, `loading`, `isAuthenticated`, and helper methods to update profile
 *
 * Notes:
 * - This file assumes your ../lib/api methods behave as follows (flexible handling included):
 *   - loginUser(credentials) -> may return { access: "<token>" } or { token: "<token>" } or may set token itself
 *   - registerUser(payload) -> returns created user or auth payload depending on your API
 *   - fetchProfile() -> returns user object
 *   - setAuthToken(token) -> sets token for axios / fetch wrapper and persists if desired
 *   - doLogout() -> backend logout (optional)
 *
 * If your api helpers already handle token persistence, this code will still work because it attempts
 * to detect token in login result and fallback to fetchProfile.
 */

const AuthContext = createContext(null);
const TOKEN_KEY = "access_token";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // initial bootstrap loading
  const [authenticating, setAuthenticating] = useState(false); // for login/register flows

  // Bootstrap: read token and fetch profile if present
  useEffect(() => {
    let mounted = true;
    async function init() {
      setLoading(true);
      try {
        const token = localStorage.getItem(TOKEN_KEY);
        if (token) {
          // ensure API wrapper uses the token
          try {
            setAuthToken(token);
          } catch (err) {
            // ignore if setAuthToken not available or fails
            // but we still try to fetch profile
          }

          // attempt to fetch profile
          try {
            const profile = await fetchProfile();
            if (mounted) setUser(profile);
          } catch (err) {
            // token invalid or fetch failed -> clear token
            console.warn("Auth bootstrap: failed to fetch profile, clearing token", err);
            try {
              setAuthToken(null);
            } catch {}
            localStorage.removeItem(TOKEN_KEY);
            if (mounted) setUser(null);
          }
        } else {
          // no token -> ensure API wrapper cleared
          try {
            setAuthToken(null);
          } catch {}
          if (mounted) setUser(null);
        }
      } catch (err) {
        console.error("Auth bootstrap error", err);
        if (mounted) setUser(null);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    init();
    return () => {
      mounted = false;
    };
  }, []);

  // Helper to extract token from login/registration response
  function _tokenFromAuthResult(result) {
    if (!result) return null;
    if (typeof result === "string") return result;
    if (result.access) return result.access;
    if (result.token) return result.token;
    if (result.data && (result.data.access || result.data.token)) return result.data.access || result.data.token;
    return null;
  }

  // Login: call loginUser, set token if provided, fetch profile
  async function login(credentials) {
    setAuthenticating(true);
    try {
      const res = await loginUser(credentials);
      const token = _tokenFromAuthResult(res);
      if (token) {
        try {
          // persist token and tell API wrapper
          localStorage.setItem(TOKEN_KEY, token);
          setAuthToken(token);
        } catch (err) {
          console.warn("Failed to persist token", err);
        }
      }

      // fetch profile (backend should return profile at /api/me/ or similar)
      const profile = await fetchProfile();
      setUser(profile);
      return profile;
    } catch (err) {
      // bubble up error so caller can show message
      throw err;
    } finally {
      setAuthenticating(false);
    }
  }

  // Register: call registerUser. Do NOT auto-login by default (safer).
  // If you want auto-login, detect token in response (similar to login()).
  async function register(payload) {
    setAuthenticating(true);
    try {
      const res = await registerUser(payload);
      // If your register endpoint returns tokens, handle them similarly:
      const token = _tokenFromAuthResult(res);
      if (token) {
        try {
          localStorage.setItem(TOKEN_KEY, token);
          setAuthToken(token);
        } catch {}
        const profile = await fetchProfile();
        setUser(profile);
        return profile;
      }
      return res;
    } catch (err) {
      throw err;
    } finally {
      setAuthenticating(false);
    }
  }

  // Logout: clear token locally and optionally call server logout helper
  function logout() {
    try {
      doLogout(); // optional backend call; keep it best-effort
    } catch (err) {
      // ignore
    }
    try {
      setAuthToken(null);
    } catch (err) {}
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  }

  // Refresh profile explicitly (useful after edits)
  async function refreshProfile() {
    try {
      const profile = await fetchProfile();
      setUser(profile);
      return profile;
    } catch (err) {
      console.error("Failed to refresh profile", err);
      return null;
    }
  }

  // update user locally (small edits without refetching)
  function updateUser(partial) {
    setUser(prev => (prev ? { ...prev, ...partial } : partial));
  }

  const value = {
    user,
    loading,
    authenticating,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    refreshProfile,
    updateUser,
    setUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
