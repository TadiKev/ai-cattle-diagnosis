// src/pages/Dashboard.jsx
import React, { useEffect, useState } from "react";
import api from "../lib/api";

// Optional: You can use react-icons for nicer icons
import { FaVirus, FaHeartbeat, FaExclamationTriangle, FaCalendarCheck } from "react-icons/fa";

function StatCard({ title, value, icon, color, hint }) {
  return (
    <div className={`flex items-center p-5 rounded-xl shadow-sm hover:shadow-md transition-all bg-white`}>
      <div className={`p-3 rounded-full text-white mr-4 ${color}`}>
        {icon}
      </div>
      <div>
        <div className="text-gray-500 text-sm">{title}</div>
        <div className="text-2xl font-bold mt-1">{value}</div>
        {hint && <div className="text-xs text-gray-400 mt-1">{hint}</div>}
      </div>
    </div>
  );
}

function DiseaseItem({ disease, count }) {
  return (
    <div className="flex items-center justify-between py-2 border-b last:border-b-0 hover:bg-gray-50 px-2 rounded">
      <div className="text-sm font-medium">{disease}</div>
      <div className="text-xs text-gray-500">{count} case{count > 1 ? "s" : ""}</div>
    </div>
  );
}

function RecentDiagnosisCard({ d }) {
  const date = d.created_at ? new Date(d.created_at) : null;
  return (
    <div className="flex justify-between p-4 bg-white rounded-xl shadow-sm hover:shadow-md transition-all mb-3">
      <div>
        <div className="font-semibold text-lg">{d.cattle?.name || "Unknown"}</div>
        <div className="text-sm text-gray-500">{d.top_prediction?.disease || "No prediction"}</div>
        <div className="text-xs text-gray-400 mt-1">{date ? date.toLocaleString() : "—"}</div>
      </div>
      <div className="text-right flex flex-col justify-between items-end">
        <div className={`px-2 py-1 rounded-full text-xs font-semibold 
          ${d.severity === "high" ? "bg-red-100 text-red-700" :
            d.severity === "medium" ? "bg-yellow-100 text-yellow-700" : 
            "bg-green-100 text-green-700"}`}>
          {d.severity || "unknown"}
        </div>
        <div className="text-xs text-gray-500 mt-1">{d.confidence ? Math.round(d.confidence * 100) + "% confidence" : "—"}</div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [cattle, setCattle] = useState([]);
  const [diagnoses, setDiagnoses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [cRes, dRes] = await Promise.all([api.get("/api/cattle/"), api.get("/api/diagnosis/")]);
        if (cancelled) return;
        setCattle(Array.isArray(cRes.data) ? cRes.data : []);
        setDiagnoses(Array.isArray(dRes.data) ? dRes.data.sort((a,b) => new Date(b.created_at) - new Date(a.created_at)) : []);
      } catch (err) {
        console.error("Failed to load dashboard data", err);
        setCattle([]);
        setDiagnoses([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  // Stats
  const totalCattle = cattle.length;
  const totalDiagnoses = diagnoses.length;
  const criticalCases = diagnoses.filter(d => d.severity === "high").length;
  const avgConfidence = totalDiagnoses > 0 ? Math.round((diagnoses.reduce((s, r) => s + (r.confidence || 0), 0) / totalDiagnoses) * 100) + "%" : "—";

  // Common diseases aggregation (top 6)
  const diseaseCounts = diagnoses.reduce((acc, d) => {
    const name = d.top_prediction?.disease || d.predictions?.[0]?.disease || "Unknown";
    acc[name] = (acc[name] || 0) + 1;
    return acc;
  }, {});
  const commonDiseases = Object.entries(diseaseCounts)
    .map(([disease, count]) => ({ disease, count }))
    .sort((a,b) => b.count - a.count)
    .slice(0, 6);

  // Recent diagnoses (limit 6)
  const recent = diagnoses.slice(0, 6);

  // Health status distribution
  const latestByCattle = {};
  diagnoses.forEach(d => {
    if (!d.cattle) return;
    const cid = d.cattle.id || d.cattle;
    if (!latestByCattle[cid]) latestByCattle[cid] = d;
  });
  let healthy = 0, underTreatment = 0, critical = 0;
  cattle.forEach(c => {
    const latest = latestByCattle[c.id];
    if (!latest) healthy += 1;
    else if (latest.severity === "high") critical += 1;
    else if (latest.severity === "medium") underTreatment += 1;
    else healthy += 1;
  });

  return (
    <div className="space-y-8">
      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
        <StatCard title="Total Cattle" value={loading ? "…" : totalCattle} icon={<FaHeartbeat />} color="bg-green-500" hint="Active in system" />
        <StatCard title="Total Diagnoses" value={loading ? "…" : totalDiagnoses} icon={<FaVirus />} color="bg-blue-500" hint="All-time records" />
        <StatCard title="Critical Cases" value={loading ? "…" : criticalCases} icon={<FaExclamationTriangle />} color="bg-red-500" hint="High severity alerts" />
        <StatCard title="Avg Confidence" value={loading ? "…" : avgConfidence} icon={<FaCalendarCheck />} color="bg-yellow-500" hint="Diagnosis accuracy" />
      </div>

      {/* Common Diseases + Recent Diagnoses */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Common Diseases */}
        <div className="card p-4 bg-white rounded-xl shadow-sm">
          <h3 className="font-semibold mb-3">Common Diseases</h3>
          {commonDiseases.length === 0 ? (
            <div className="text-gray-500">No disease data yet</div>
          ) : (
            commonDiseases.map(d => <DiseaseItem key={d.disease} disease={d.disease} count={d.count} />)
          )}
        </div>

        {/* Recent Diagnoses */}
        <div className="md:col-span-2 card p-4 bg-white rounded-xl shadow-sm">
          <h3 className="font-semibold mb-4">Recent Diagnoses</h3>
          <div className="max-h-96 overflow-y-auto">
            {recent.length === 0 ? (
              <div className="text-gray-500">No diagnoses yet</div>
            ) : (
              recent.map(d => <RecentDiagnosisCard key={d.id} d={d} />)
            )}
          </div>
        </div>
      </div>

      {/* Health Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-4 bg-white rounded-xl shadow-sm">
          <h3 className="font-semibold mb-3">Health Status Overview</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <div className="text-sm font-medium">Healthy</div>
              <div className="font-bold text-lg">{healthy}</div>
            </div>
            <div className="flex justify-between">
              <div className="text-sm font-medium">Under Treatment</div>
              <div className="font-bold text-lg">{underTreatment}</div>
            </div>
            <div className="flex justify-between">
              <div className="text-sm font-medium">Critical</div>
              <div className="font-bold text-lg">{critical}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
