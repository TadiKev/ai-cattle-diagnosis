// FILE: src/components/Login.jsx
import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const auth = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await auth.login({ username, password });
      navigate("/dashboard");
    } catch (err) {
      console.error(err);
      alert(err?.response?.data?.detail || err.message || "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-md mx-auto mt-12">
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Sign in</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium">Username</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} className="mt-1 block w-full rounded border px-3 py-2" required />
          </div>
          <div>
            <label className="block text-sm font-medium">Password</label>
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" className="mt-1 block w-full rounded border px-3 py-2" required />
          </div>
          <div className="flex items-center justify-between">
            <button disabled={submitting} className="btn btn-primary">{submitting ? "Signing in..." : "Sign in"}</button>
            <Link to="/register" className="text-sm text-gray-600">Create account</Link>
          </div>
        </form>
      </div>
    </div>
  );
}