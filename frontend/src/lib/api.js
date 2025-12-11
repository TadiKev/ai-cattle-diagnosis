// FILE: src/lib/api.js
import axios from "axios";
import { toast } from "react-hot-toast"; // optional if you have it; otherwise ignore

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 20000,
});

// helper to set/remove auth header
export function setAuthToken(token) {
  if (token) {
    localStorage.setItem("access_token", token);
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    localStorage.removeItem("access_token");
    delete api.defaults.headers.common["Authorization"];
  }
}

// attach token on each request (fallback)
api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("access_token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

// auth helpers
export async function loginUser({ username, password }) {
  const res = await api.post("/api/auth/login/", { username, password });
  const { access } = res.data;
  if (!access) throw new Error("No access token returned from login");
  setAuthToken(access);
  return res.data;
}

export async function registerUser(payload) {
  // payload: { username, email, password, full_name, role, farm_name }
  const res = await api.post("/api/auth/register/", payload);
  return res.data;
}

export async function fetchProfile() {
  const res = await api.get("/api/auth/me/");
  return res.data;
}

export function logout() {
  setAuthToken(null);
}

export default api;











