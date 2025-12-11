// src/components/DiagnosisResult.jsx
import React from "react";

// Simple progress bar component
function ProgressBar({ value }) {
  const pct = Math.round(value * 100);
  return (
    <div className="w-full bg-gray-200 rounded h-3">
      <div style={{ width: `${pct}%` }} className="h-3 rounded bg-green-500" />
    </div>
  );
}

/**
 * DiagnosisResult Component
 * Props:
 * - result: {
 *     predictions_processed, top_processed, confidence_processed,
 *     gradcam_url, recommendation, uncertain
 *   }
 */
export default function DiagnosisResult({ result }) {
  if (!result) return null;

  const preds = result.predictions_processed || result.predictions || [];
  const top = result.top_processed || result.top || (preds[0] || {});
  const gradcam = result.gradcam_url;
  const uncertain = result.uncertain || ((result.confidence_processed || result.confidence || 0) < 0.5);

  return (
    <div className="p-4 bg-white rounded shadow">
      <h3 className="text-lg font-semibold mb-2">Diagnosis Results</h3>

      {uncertain && (
        <div className="my-2 p-2 bg-yellow-100 border-l-4 border-yellow-400">
          <strong>Low confidence</strong> — consider uploading more images or consult a veterinarian.
        </div>
      )}

      <div className="flex gap-6">
        <div className="flex-1">
          <h4 className="font-medium">Top prediction</h4>
          <div className="text-xl font-bold">{top?.disease || "Unknown"}</div>
          <div className="text-sm text-gray-600">
            Confidence: {((result.confidence_processed || result.confidence || 0) * 100).toFixed(0)}%
          </div>

          <div className="mt-4">
            <h5 className="text-sm font-medium">Top candidates</h5>
            <ul className="space-y-2 mt-2">
              {preds.slice(0, 3).map(p => (
                <li key={p.disease} className="flex items-center gap-3">
                  <div className="w-36">
                    <div className="text-sm">{p.disease}</div>
                    <div className="text-xs text-gray-500">{(p.score * 100).toFixed(0)}%</div>
                  </div>
                  <div className="flex-1"><ProgressBar value={p.score} /></div>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-4">
            <h5 className="text-sm font-medium">Recommendation</h5>
            <div className="mt-1 text-sm text-gray-800 whitespace-pre-line">
              {result.recommendation || "No recommendation available."}
            </div>
          </div>
        </div>

        <div className="w-64">
          <h5 className="text-sm font-medium">Grad-CAM</h5>
          {gradcam ? (
            <img src={gradcam} alt="Grad-CAM" className="w-full rounded mt-2 border" />
          ) : (
            <div className="mt-2 text-sm text-gray-500">No gradcam available.</div>
          )}
        </div>
      </div>
    </div>
  );
}
