// FILE: src/App.jsx
import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./components/Dashboard";
import NewDiagnosis from "./components/NewDiagnosis";
import CattleRecords from "./components/CattleRecords";
import DiagnosisHistory from "./components/DiagnosisHistory";
import Login from "./components/Login";
import Register from "./components/Register";
import RequireAuth from "./components/RequireAuth";
import DiagnosisDetail from "./pages/DiagnosisDetail";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
        <Route path="/diagnosis/new" element={<RequireAuth><NewDiagnosis /></RequireAuth>} />
        {/* New route: diagnosis detail */}
        <Route path="/diagnosis/:id" element={<RequireAuth><DiagnosisDetail /></RequireAuth>} />
        <Route path="/cattle" element={<RequireAuth><CattleRecords /></RequireAuth>} />
        <Route path="/history" element={<RequireAuth><DiagnosisHistory /></RequireAuth>} />

        <Route path="*" element={<div className="p-8">Page not found</div>} />
      </Routes>
    </Layout>
  );
}
