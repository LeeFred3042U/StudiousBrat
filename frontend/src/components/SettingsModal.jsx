import { useState } from "react";
import { api } from "../api/client";
import { store } from "../store/storage";
import { t } from "../locale/en";
import { inputCls, labelCls } from "../ui";

// The ONLY place grade level and preferred universe change (explicit PATCH;
// never inferred from chat content). Also hosts "Delete my data".
export default function SettingsModal({ profile, onClose, onSave, onDelete }) {
  const [form, setForm] = useState({
    name: profile.name || "",
    grade_level: profile.grade_level || "",
    subjects: (profile.subjects || []).join(", "),
    preferred_universe: profile.preferred_universe || "",
  });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const save = async () => {
    setBusy(true);
    try {
      const updated = await api.patchProfile(profile.id, {
        name: form.name || null,
        grade_level: form.grade_level || null,
        subjects: form.subjects
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        preferred_universe: form.preferred_universe || null,
      });
      store.setProfile(updated);
      onSave(updated);
      onClose();
    } catch (e) {
      window.alert(t.errorGeneric);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="font-serif text-xl font-bold">{t.settings}</h2>
        <div className="mt-4 space-y-4">
          <label className={labelCls}>
            {t.nameLabel}
            <input value={form.name} onChange={set("name")} className={inputCls} />
          </label>
          <label className={labelCls}>
            {t.gradeLabel}
            <select
              value={form.grade_level}
              onChange={set("grade_level")}
              className={inputCls}
            >
              {t.gradeOptions.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </label>
          <label className={labelCls}>
            {t.subjectsLabel}
            <input value={form.subjects} onChange={set("subjects")} className={inputCls} />
          </label>
          <label className={labelCls}>
            {t.universeLabel}
            <input
              value={form.preferred_universe}
              onChange={set("preferred_universe")}
              className={inputCls}
            />
          </label>
        </div>
        <div className="mt-6 flex items-center justify-between">
          <button
            onClick={onDelete}
            className="text-xs text-red-600 hover:underline"
          >
            {t.deleteMyData}
          </button>
          <div className="flex gap-2">
            <button onClick={onClose} className="rounded-lg px-4 py-2 text-sm text-neutral-600">
              {t.cancelButton}
            </button>
            <button
              onClick={save}
              disabled={busy}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
            >
              {t.saveButton}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
