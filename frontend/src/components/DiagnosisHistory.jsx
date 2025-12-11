// src/pages/DiagnosisHistory.jsx
import React, { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import api from "../lib/api";

/**
 * DiagnosisHistory
 * - Search, filter by severity, sort, pagination (no external deps)
 * - Export filtered results to CSV
 * - Shows reviewer and review_status when present
 */

function Badge({ children, variant = "gray" }) {
  const base = "px-3 py-1 rounded-full text-xs font-medium";
  const variants = {
    high: "bg-red-100 text-red-700",
    medium: "bg-yellow-100 text-yellow-700",
    low: "bg-green-100 text-green-700",
    unknown: "bg-gray-100 text-gray-700",
    approved: "bg-blue-100 text-blue-700",
    edited: "bg-indigo-100 text-indigo-700",
    rejected: "bg-gray-100 text-gray-700",
  };
  return <span className={`${base} ${variants[variant] || variants.unknown}`}>{children}</span>;
}

function ConfidenceBar({ value = 0 }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <div className="w-full bg-gray-100 rounded h-2 overflow-hidden">
      <div style={{ width: `${pct}%` }} className="h-2 rounded bg-green-500 transition-all" />
    </div>
  );
}

export default function DiagnosisHistory() {
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [sortBy, setSortBy] = useState("newest"); // newest | oldest | confidence_desc | confidence_asc
  const [page, setPage] = useState(0);
  const [itemsPerPage, setItemsPerPage] = useState(8);

  const navigate = useNavigate();

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      try {
        const res = await api.get("/api/diagnosis/");
        if (!mounted) return;
        setList(Array.isArray(res.data) ? res.data : []);
      } catch (e) {
        console.error("Failed to load diagnoses", e);
        if (mounted) setList([]);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => { mounted = false; };
  }, []);

  // Helpers to display cattle and top disease robustly
  const getCattleName = (item) => {
    if (!item) return "Unknown";
    if (item.cattle && typeof item.cattle === "object") return item.cattle.name || item.cattle.tag_number || "Unknown";
    if (item.cattle_name) return item.cattle_name;
    if (item.cattle && typeof item.cattle === "number") return `Cattle #${item.cattle}`;
    return "Unknown";
  };

  const getTopDisease = (item) => {
    if (!item) return "No prediction";
    // prefer processed top if attached
    const topProcessed = item._ml?.top_processed || item.top_processed;
    if (topProcessed && (topProcessed.disease || topProcessed)) return topProcessed.disease || topProcessed;
    const top = item.top_prediction || (item.predictions && item.predictions[0]);
    if (top && (top.disease || top)) return top.disease || top;
    return "No prediction";
  };

  // Filtering & searching
  const filtered = useMemo(() => {
    const q = (search || "").trim().toLowerCase();
    return list.filter((item) => {
      const cattleName = getCattleName(item).toLowerCase();
      const disease = (getTopDisease(item) || "").toLowerCase();
      const matchesSearch = !q || cattleName.includes(q) || disease.includes(q);
      const matchesSeverity = severityFilter === "all" ? true : (item.severity || "").toLowerCase() === severityFilter;
      return matchesSearch && matchesSeverity;
    });
  }, [list, search, severityFilter]);

  // Sorting
  const sorted = useMemo(() => {
    const arr = [...filtered];
    if (sortBy === "newest") {
      arr.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    } else if (sortBy === "oldest") {
      arr.sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
    } else if (sortBy === "confidence_desc") {
      arr.sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
    } else if (sortBy === "confidence_asc") {
      arr.sort((a, b) => (a.confidence || 0) - (b.confidence || 0));
    }
    return arr;
  }, [filtered, sortBy]);

  // Pagination
  const pageCount = Math.max(1, Math.ceil(sorted.length / itemsPerPage));
  useEffect(() => {
    // clamp page if list shrinks
    if (page >= pageCount) setPage(Math.max(0, pageCount - 1));
  }, [pageCount, page]);

  const start = page * itemsPerPage;
  const visible = sorted.slice(start, start + itemsPerPage);

  // Export CSV of currently filtered (not just visible)
  const exportCsv = () => {
    const rows = sorted.map((d) => {
      return {
        id: d.id,
        cattle: getCattleName(d),
        disease: getTopDisease(d),
        confidence: d.confidence ? Math.round(d.confidence * 100) + "%" : "",
        severity: d.severity || "",
        submitted_by: d.submitted_by || "",
        created_at: d.created_at || "",
        review_status: d.review_status || d._ml?.review_status || "",
        reviewed_by: (d.reviewed_by && d.reviewed_by.username) || d.reviewed_by || "",
      };
    });
    if (!rows.length) {
      alert("No rows to export");
      return;
    }
    const keys = Object.keys(rows[0]);
    const csv = [
      keys.join(","),
      ...rows.map((r) => keys.map((k) => `"${String(r[k] || "").replace(/"/g, '""')}"`).join(",")),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `diagnosis_history_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Diagnosis History</h1>
          <p className="text-sm text-gray-500 mt-1">Review past AI diagnoses, filter by severity, and export results.</p>
        </div>

        <div className="flex items-center gap-3 w-full lg:w-auto">
          <input
            type="search"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            placeholder="Search by cattle, tag or disease..."
            className="flex-1 lg:flex-none px-4 py-2 rounded-lg border border-gray-200 shadow-sm focus:outline-none focus:ring-2 focus:ring-green-400"
          />

          <select
            value={severityFilter}
            onChange={(e) => { setSeverityFilter(e.target.value); setPage(0); }}
            className="px-3 py-2 rounded-lg border border-gray-200"
            aria-label="Filter by severity"
          >
            <option value="all">All Severities</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>

          <select
            value={sortBy}
            onChange={(e) => { setSortBy(e.target.value); setPage(0); }}
            className="px-3 py-2 rounded-lg border border-gray-200"
            aria-label="Sort"
          >
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
            <option value="confidence_desc">Confidence (High → Low)</option>
            <option value="confidence_asc">Confidence (Low → High)</option>
          </select>

          <button
            onClick={exportCsv}
            className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 transition"
            title="Export filtered results to CSV"
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* Cards */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading diagnoses…</div>
      ) : visible.length === 0 ? (
        <div className="text-center py-12 text-gray-500">No diagnoses found for this filter.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {visible.map((item) => {
            const top = getTopDisease(item);
            const cattleName = getCattleName(item);
            const date = item.created_at ? new Date(item.created_at).toLocaleString() : "—";
            const conf = item.confidence || (item._ml?.confidence_processed ?? null);
            const reviewStatus = item.review_status || item._ml?.review_status || null;
            const reviewedBy = item.reviewed_by?.username || item.reviewed_by || null; // flexible
            const reviewerText = reviewedBy ? `by ${reviewedBy}` : "";

            return (
              <div key={item.id} className="bg-white p-5 rounded-xl shadow hover:shadow-lg transition flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-lg font-semibold text-gray-800">{cattleName}</div>
                      <div className="text-sm text-gray-500 mt-0.5">{item.cattle?.tag_number ? `Tag: ${item.cattle.tag_number}` : ""}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-400">{date}</div>
                      {reviewStatus && <div className="mt-2"><Badge variant={reviewStatus === "approved" ? "approved" : reviewStatus === "edited" ? "edited" : "rejected"}>{reviewStatus}</Badge></div>}
                    </div>
                  </div>

                  <div className="mt-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-600">Top prediction</div>
                        <div className="text-base font-medium text-gray-800">{top}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-gray-500">{conf ? `${Math.round(conf * 100)}%` : "—"}</div>
                        <div className="mt-2">
                          <Badge variant={item.severity || "unknown"}>{(item.severity || "unknown").toLowerCase()}</Badge>
                        </div>
                      </div>
                    </div>

                    <div className="mt-3">
                      <ConfidenceBar value={conf || 0} />
                    </div>

                    <div className="mt-3 text-sm text-gray-600">
                      {item.recommendation ? (
                        <div className="line-clamp-3 whitespace-pre-line">{item.recommendation}</div>
                      ) : (
                        <div className="italic text-gray-400">No recommendation saved.</div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between gap-3">
                  <div className="text-xs text-gray-500">{reviewStatus ? `${reviewStatus}${reviewerText ? ` ${reviewerText}` : ""}` : "AI-generated"}</div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => navigate(`/diagnosis/${item.id}`)}
                      className="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition"
                    >
                      View
                    </button>
                    <button
                      onClick={() => {
                        // quick copy link
                        const url = `${window.location.origin}/diagnosis/${item.id}`;
                        navigator.clipboard?.writeText(url).then(() => {
                          // small inline feedback could be added
                        });
                      }}
                      className="px-3 py-1.5 border rounded text-sm hover:shadow-sm"
                      title="Copy link"
                    >
                      Share
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination controls */}
      <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <div>Showing</div>
          <div className="font-medium">{Math.min(sorted.length, start + 1)}–{Math.min(sorted.length, start + visible.length)}</div>
          <div>of</div>
          <div className="font-medium">{sorted.length}</div>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={itemsPerPage}
            onChange={(e) => { setItemsPerPage(Number(e.target.value)); setPage(0); }}
            className="px-3 py-2 border rounded"
            aria-label="Items per page"
          >
            <option value={6}>6 / page</option>
            <option value={8}>8 / page</option>
            <option value={12}>12 / page</option>
            <option value={24}>24 / page</option>
          </select>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page <= 0}
              className={`px-3 py-1 rounded ${page <= 0 ? "bg-gray-100 text-gray-400" : "bg-white border hover:shadow-sm"}`}
            >
              Prev
            </button>

            {/* Numeric pages (compact) */}
            <div className="flex items-center gap-1 px-2">
              {Array.from({ length: pageCount }, (_, i) => i).slice(
                Math.max(0, page - 3),
                Math.min(pageCount, page + 4)
              ).map((p) => (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`px-3 py-1 rounded ${p === page ? "bg-green-600 text-white" : "bg-white border hover:shadow-sm"}`}
                >
                  {p + 1}
                </button>
              ))}
            </div>

            <button
              onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
              disabled={page >= pageCount - 1}
              className={`px-3 py-1 rounded ${page >= pageCount - 1 ? "bg-gray-100 text-gray-400" : "bg-white border hover:shadow-sm"}`}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
