import React, { useEffect, useState } from "react";
import api from "../lib/api";

function ImagePreview({ file, onRemove }) {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    const reader = new FileReader();
    reader.onload = (e) => setUrl(e.target.result);
    reader.readAsDataURL(file);
    return () => {};
  }, [file]);
  return (
    <div className="relative">
      <img src={url} alt="preview" className="w-36 h-28 object-cover rounded-md" />
      <button onClick={onRemove} className="absolute top-1 right-1 bg-white rounded-full p-1 text-xs">✕</button>
    </div>
  );
}

export default function NewDiagnosis() {
  const [cattleOptions, setCattleOptions] = useState([]);
  const [selectedCattle, setSelectedCattle] = useState("");
  const [symptoms, setSymptoms] = useState("");
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    const loadCattle = async () => {
      try {
        const res = await api.get("/api/cattle/");
        setCattleOptions(res.data);
      } catch (e) {
        console.error(e);
      }
    };
    loadCattle();
  }, []);

  const onFiles = (e) => {
    const selected = Array.from(e.target.files);
    const ok = selected.every(f => f.size <= 10 * 1024 * 1024 && /^image\//.test(f.type));
    if (!ok) {
      alert("Each file must be an image and <= 10MB.");
      return;
    }
    setFiles(prev => [...prev, ...selected].slice(0, 6));
  };

  const removeFile = (idx) => setFiles(files.filter((_, i) => i !== idx));
  const quickFill = () => setSymptoms("Runny nose, Cough, Nasal discharge");

  const submit = async () => {
    if (!selectedCattle) return alert("Select a cattle first.");
    setLoading(true);
    setResult(null);
    try {
      const form = new FormData();
      form.append("cattle_id", selectedCattle);
      form.append("symptom_text", symptoms);
      files.forEach(f => form.append("uploaded_images", f, f.name));
      const res = await api.post("/api/diagnosis/", form, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setResult(res.data);
    } catch (err) {
      console.error(err);
      alert("Failed to submit diagnosis. See console.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">New Diagnosis</h1>

      <div className="card grid grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700">Choose Cattle</label>
          <select value={selectedCattle} onChange={e => setSelectedCattle(e.target.value)} className="mt-1 block w-full rounded-md border px-3 py-2">
            <option value="">-- Select --</option>
            {cattleOptions.map(c => <option value={c.id} key={c.id}>{c.tag_number} — {c.name}</option>)}
          </select>

          <div className="mt-4">
            <label className="block text-sm font-medium">Images (JPG/PNG ≤10MB)</label>
            <input type="file" accept="image/*" multiple onChange={onFiles} className="mt-2" />
            <div className="mt-3 flex gap-3 flex-wrap">
              {files.map((f, i) => <ImagePreview key={i} file={f} onRemove={() => removeFile(i)} />)}
            </div>
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium">Symptoms</label>
            <textarea value={symptoms} onChange={e => setSymptoms(e.target.value)} placeholder="e.g. Runny nose, Loss of appetite" rows={5} className="mt-2 w-full rounded-md border p-2" />
            <div className="flex gap-2 mt-3">
              <button onClick={quickFill} className="btn bg-gray-100">Quick Test</button>
              <button onClick={() => { setSymptoms(""); setFiles([]); setSelectedCattle(""); }} className="btn">Reset</button>
            </div>
          </div>
        </div>

        <div>
          <div className="card">
            <h3 className="font-semibold">Diagnosis Results</h3>
            {!result && <div className="text-gray-500 mt-3">Enter symptoms and click Diagnose to see results.</div>}
            {result && (
              <div className="mt-3">
                <div className="font-bold">{result.top_prediction?.disease || "—"}</div>
                <div className="text-sm text-gray-600">Confidence: {result.confidence ? Math.round(result.confidence * 100) + "%" : "—"}</div>
                <div className="mt-2">{result.recommendation}</div>
                <div className="mt-3">
                  <button className="btn btn-primary">Save to History</button>
                </div>
              </div>
            )}
          </div>

          <div className="mt-4">
            <button disabled={!selectedCattle || loading} onClick={submit} className={`btn btn-primary w-full ${(!selectedCattle || loading) ? "opacity-60 cursor-not-allowed" : ""}`}>
              {loading ? "Diagnosing..." : "Diagnose"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
