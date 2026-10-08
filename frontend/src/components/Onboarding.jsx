import { useState } from "react";
import { api } from "../api/client";
import { store } from "../store/storage";
import { t } from "../locale/en";
import { inputCls, labelCls } from "../ui";

export default function Onboarding({ onDone }) {
  const [form, setForm] = useState({
    name: "",
    grade_level: "",
    subjects: "",
    preferred_universe: "",
  });
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (!form.grade_level || !form.preferred_universe || busy) return;
    setBusy(true);
    try {
      const profile = await api.createProfile({
        name: form.name || null,
        grade_level: form.grade_level,
        subjects: form.subjects
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        preferred_universe: form.preferred_universe,
      });
      store.setProfile(profile);
      onDone(profile);
    } catch (err) {
      window.alert(t.errorGeneric);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-cream px-4">
      <form
        onSubmit={submit}
        className="w-full max-w-md space-y-5 rounded-2xl border border-neutral-200 bg-white p-8 shadow-sm"
      >
        <div>
          <h1 className="font-serif text-2xl font-bold">{t.onboardingTitle}</h1>
          <p className="mt-1 text-sm text-neutral-500">{t.onboardingBody}</p>
        </div>
        <label className={labelCls}>
          {t.nameLabel}
          <input value={form.name} onChange={set("name")} className={inputCls} />
        </label>
        <label className={labelCls}>
          {t.gradeLabel}
          <select value={form.grade_level} onChange={set("grade_level")} className={inputCls}>
            <option value="">{t.selectPlaceholder}</option>
            {t.gradeOptions.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </label>
        <label className={labelCls}>
          {t.subjectsLabel}
          <input
            value={form.subjects}
            onChange={set("subjects")}
            placeholder={t.subjectsHint}
            className={inputCls}
          />
        </label>
        <label className={labelCls}>
          {t.universeLabel}
          <input
            value={form.preferred_universe}
            onChange={set("preferred_universe")}
            placeholder={t.universeHint}
            className={inputCls}
          />
        </label>
        <button
          type="submit"
          disabled={busy || !form.grade_level || !form.preferred_universe}
          className="w-full rounded-lg bg-accent py-2.5 font-medium text-white disabled:opacity-40"
        >
          {t.startButton}
        </button>
      </form>
    </div>
  );
}
