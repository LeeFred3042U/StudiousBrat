import { t } from "../locale/en";

// Meme-style flashcards: text-only caption/punchline cards, inline.
export default function MemeCards({ memes }) {
  return (
    <div>
      <div className="mb-2 text-xs uppercase tracking-wide text-neutral-500">
        {t.memesTitle}
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {(memes || []).map((m, i) => (
          <div
            key={i}
            className="rounded-xl border border-dashed border-neutral-300 bg-white px-4 py-3"
          >
            <p className="font-semibold">{m.caption}</p>
            <p className="mt-1 text-neutral-600">{m.punchline}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
