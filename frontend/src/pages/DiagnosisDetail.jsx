import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import DiagnosisResults from "../components/DiagnosisResults";
import ReviewModal from "../components/ReviewModal";
import { useAuth } from "../context/AuthContext";
import api from "../lib/api";

export default function DiagnosisDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [diagnosis, setDiagnosis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showReview, setShowReview] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function fetchDiag() {
      setLoading(true);
      try {
        const res = await api.get(`/api/diagnosis/${id}/`);
        if (!mounted) return;
        setDiagnosis(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    fetchDiag();
    return () => { mounted = false; };
  }, [id]);

  if (loading) return <div className="p-8">Loading diagnosis…</div>;
  if (!diagnosis) return <div className="p-8">No diagnosis found.</div>;

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Diagnosis #{diagnosis.id}</h1>

        {/* Veterinarian Review Button — shown only if server says user.role === 'vet' */}
        {user?.role === "vet" && (
          <button
            onClick={() => setShowReview(true)}
            className="px-3 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition"
          >
            Review & Approve
          </button>
        )}
      </header>

      <DiagnosisResults diagnosis={diagnosis} />

      {showReview && (
        <ReviewModal
          diagnosis={diagnosis}
          onClose={() => setShowReview(false)}
          onSaved={(updated) => setDiagnosis(updated)}
        />
      )}
    </div>
  );
}
