// src/components/ReviewModal.jsx
import React, { useState } from "react";
import api from "../lib/api";

export default function ReviewModal({ diagnosis, onClose, onSaved }) {
  const [status, setStatus] = useState("approved");
  const [notes, setNotes] = useState("");
  const [recommendation, setRecommendation] = useState(diagnosis.recommendation || "");
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    setSaving(true);
    try {
      const payload = {
        review_status: status,
        review_notes: notes,
        recommendation,
      };
      const res = await api.post(`/api/diagnosis/${diagnosis.id}/review/`, payload);
      // onSaved gets updated serialized diagnosis
      onSaved(res.data);
      alert("Review saved.");
      onClose();
    } catch (err) {
      console.error(err);
      alert("Failed to save review. See console for details.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-lg w-full max-w-2xl p-6 shadow-lg">
        <h3 className="text-lg font-semibold">Review Diagnosis #{diagnosis.id}</h3>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium">Decision</label>
            <select value={status} onChange={e => setStatus(e.target.value)} className="w-full border rounded px-3 py-2">
              <option value="approved">Approve</option>
              <option value="edited">Edit (save corrected result)</option>
              <option value="rejected">Reject</option>
            </select>
          </div>

          <div>
            <label className="text-sm font-medium">AI Confidence</label>
            <input type="text" value={diagnosis.confidence ? Math.round(diagnosis.confidence * 100) + "%" : "—"} readOnly className="w-full border rounded px-3 py-2 bg-gray-100" />
          </div>
        </div>

        <div className="mt-4">
          <label className="text-sm font-medium">Recommendation (editable)</label>
          <textarea rows={5} value={recommendation} onChange={e => setRecommendation(e.target.value)} className="w-full border rounded p-2" />
        </div>

        <div className="mt-3">
          <label className="text-sm font-medium">Review Notes (internal)</label>
          <textarea rows={3} value={notes} onChange={e => setNotes(e.target.value)} className="w-full border rounded p-2" placeholder="Notes for audit or communication with farmer" />
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} disabled={saving} className="px-3 py-2 border rounded">Cancel</button>
          <button onClick={submit} disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded">
            {saving ? "Saving…" : (status === "approved" ? "Approve" : status === "rejected" ? "Reject" : "Save edit")}
          </button>
        </div>
      </div>
    </div>
  );
}
