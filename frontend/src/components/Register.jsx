// FILE: src/components/Register.jsx
import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const [form, setForm] = useState({ username: "", email: "", password: "", full_name: "", role: "farmer", farm_name: "" });
  const [submitting, setSubmitting] = useState(false);
  const auth = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await auth.register(form);
      // optionally auto-login
      await auth.login({ username: form.username, password: form.password });
      navigate("/dashboard");
    } catch (err) {
      console.error(err);
      alert(err?.response?.data || err.message || "Registration failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-md mx-auto mt-12">
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Create an account</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input placeholder="Full name" value={form.full_name} onChange={(e)=>setForm({...form, full_name: e.target.value})} className="w-full rounded border px-3 py-2" />
          <input placeholder="Farm name" value={form.farm_name} onChange={(e)=>setForm({...form, farm_name: e.target.value})} className="w-full rounded border px-3 py-2" />
          <input placeholder="Email" value={form.email} onChange={(e)=>setForm({...form, email: e.target.value})} type="email" className="w-full rounded border px-3 py-2" />
          <input placeholder="Username" value={form.username} onChange={(e)=>setForm({...form, username: e.target.value})} className="w-full rounded border px-3 py-2" required />
          <input placeholder="Password" value={form.password} onChange={(e)=>setForm({...form, password: e.target.value})} type="password" className="w-full rounded border px-3 py-2" required />

          <div className="flex items-center justify-between">
            <button disabled={submitting} className="btn btn-primary">{submitting ? "Creating..." : "Create account"}</button>
            <Link to="/login" className="text-sm text-gray-600">Already have an account?</Link>
          </div>
        </form>
      </div>
    </div>
  );
}