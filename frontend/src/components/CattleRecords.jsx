// src/pages/CattleRecords.jsx
import React, { useEffect, useState } from "react";
import api from "../lib/api";

// Reusable row component
function CattleRow({ c, onDelete, onEdit }) {
  return (
    <tr className="border-b hover:bg-gray-50">
      <td className="px-4 py-3">{c.tag_number}</td>
      <td className="px-4 py-3">{c.name}</td>
      <td className="px-4 py-3">{c.breed}</td>
      <td className="px-4 py-3">{c.age_years} yrs</td>
      <td className="px-4 py-3">{c.weight_kg} kg</td>
      <td className="px-4 py-3 flex gap-2">
        <button
          onClick={() => onEdit(c)}
          className="text-sm px-2 py-1 bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200 transition"
        >
          Edit
        </button>
        <button
          onClick={() => onDelete(c.id)}
          className="text-sm px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 transition"
        >
          Delete
        </button>
      </td>
    </tr>
  );
}

export default function CattleRecords() {
  const [list, setList] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [q, setQ] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ id: null, tag_number: "", name: "", breed: "", age_years: "", weight_kg: "" });
  const [page, setPage] = useState(1);
  const [perPage] = useState(10);

  // Load cattle
  const loadCattle = async () => {
    try {
      const res = await api.get("/api/cattle/");
      setList(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadCattle();
  }, []);

  // Filter cattle
  useEffect(() => {
    let f = [...list];
    if (q) {
      const search = q.toLowerCase();
      f = f.filter(
        c =>
          c.tag_number.toLowerCase().includes(search) ||
          c.name.toLowerCase().includes(search) ||
          c.breed.toLowerCase().includes(search)
      );
    }
    setFiltered(f);
    setPage(1);
  }, [q, list]);

  // Pagination
  const totalPages = Math.ceil(filtered.length / perPage);
  const currentData = filtered.slice((page - 1) * perPage, page * perPage);

  // Add or Edit
  const submitForm = async () => {
    try {
      if (form.id) {
        const res = await api.put(`/api/cattle/${form.id}/`, form);
        setList(prev => prev.map(c => (c.id === form.id ? res.data : c)));
      } else {
        const res = await api.post("/api/cattle/", form);
        setList(prev => [res.data, ...prev]);
      }
      closeModal();
    } catch (e) {
      console.error(e);
      alert("Failed to save cattle record");
    }
  };

  const deleteCattle = async id => {
    if (!confirm("Are you sure you want to delete this cattle?")) return;
    try {
      await api.delete(`/api/cattle/${id}/`);
      setList(prev => prev.filter(c => c.id !== id));
    } catch (e) {
      console.error(e);
    }
  };

  const openModal = c => {
    if (c) setForm(c);
    else setForm({ id: null, tag_number: "", name: "", breed: "", age_years: "", weight_kg: "" });
    setShowModal(true);
  };
  const closeModal = () => setShowModal(false);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Cattle Records</h1>
        <button onClick={() => openModal()} className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition">
          Add Cattle
        </button>
      </div>

      {/* Search */}
      <input
        value={q}
        onChange={e => setQ(e.target.value)}
        placeholder="Search by tag, name, or breed..."
        className="w-full md:w-1/3 px-3 py-2 rounded border mb-4"
      />

      {/* Table */}
      <div className="card overflow-x-auto">
        <table className="w-full text-left">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-4 py-2">Tag Number</th>
              <th className="px-4 py-2">Name</th>
              <th className="px-4 py-2">Breed</th>
              <th className="px-4 py-2">Age</th>
              <th className="px-4 py-2">Weight</th>
              <th className="px-4 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {currentData.length
              ? currentData.map(c => <CattleRow key={c.id} c={c} onDelete={deleteCattle} onEdit={openModal} />)
              : <tr><td colSpan={6} className="p-4 text-gray-500">No records found</td></tr>}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center mt-4 space-x-2">
          <button disabled={page === 1} onClick={() => setPage(page - 1)} className="px-3 py-1 border rounded disabled:opacity-50">Prev</button>
          {[...Array(totalPages)].map((_, i) => (
            <button
              key={i}
              onClick={() => setPage(i + 1)}
              className={`px-3 py-1 border rounded ${page === i + 1 ? "bg-blue-600 text-white" : ""}`}
            >
              {i + 1}
            </button>
          ))}
          <button disabled={page === totalPages} onClick={() => setPage(page + 1)} className="px-3 py-1 border rounded disabled:opacity-50">Next</button>
        </div>
      )}

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/30 p-4">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="font-semibold mb-4">{form.id ? "Edit Cattle" : "Add Cattle"}</h3>
            <div className="space-y-2">
              {["tag_number","name","breed"].map(field => (
                <input
                  key={field}
                  placeholder={field.replace("_"," ").toUpperCase()}
                  value={form[field]}
                  onChange={e => setForm({...form, [field]: e.target.value})}
                  className="w-full rounded border px-3 py-2"
                />
              ))}
              {["age_years","weight_kg"].map(field => (
                <input
                  key={field}
                  type="number"
                  placeholder={field.replace("_"," ").toUpperCase()}
                  value={form[field]}
                  onChange={e => setForm({...form, [field]: e.target.value})}
                  className="w-full rounded border px-3 py-2"
                />
              ))}
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={closeModal} className="px-3 py-2 border rounded hover:bg-gray-100">Cancel</button>
              <button onClick={submitForm} className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition">{form.id ? "Update" : "Add"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
