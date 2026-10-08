import { t } from "../locale/en";

const BAND_CLASSES = {
  Strong: "border-green-300 bg-green-100 text-green-800",
  Partial: "border-amber-300 bg-amber-100 text-amber-800",
  "Needs work": "border-red-300 bg-red-100 text-red-700",
};

// Teach-back feedback: a clearly-bordered card showing covered/missing
// sub-concepts above the specific feedback text and the band badge.
export default function TeachBackCard({ evaluation }) {
  const covered = evaluation.covered_labels || evaluation.covered || [];
  const missing = evaluation.missing_labels || evaluation.missing || [];
  return (
    <div className="rounded-2xl border border-neutral-300 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
          {t.teachBackTitle}
        </span>
        <span
          className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
            BAND_CLASSES[evaluation.band] || ""
          }`}
        >
          {evaluation.band}
        </span>
      </div>
      <div className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
        <div>
          <div className="mb-1 text-xs font-medium text-green-700">{t.covered}</div>
          <ul className="space-y-1">
            {covered.length === 0 && <li className="text-neutral-400">—</li>}
            {covered.map((c, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-green-600">✓</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="mb-1 text-xs font-medium text-neutral-500">{t.missing}</div>
          <ul className="space-y-1">
            {missing.length === 0 && <li className="text-neutral-400">—</li>}
            {missing.map((m, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-neutral-400">○</span>
                <span>{m}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <p className="mt-4 border-t border-neutral-100 pt-3 text-sm leading-6">
        {evaluation.feedback}
      </p>
    </div>
  );
}
