import { useState } from "react";
import { t } from "../locale/en";

// Flashcards render inline in the assistant's message — a small set of
// flippable cards, not a separate modal.
export default function Flashcards({ cards }) {
  const [flipped, setFlipped] = useState(() => (cards || []).map(() => false));
  const toggle = (i) => setFlipped(flipped.map((f, j) => (j === i ? !f : f)));

  return (
    <div>
      <div className="mb-2 text-xs uppercase tracking-wide text-neutral-500">
        {t.flashcardsTitle}
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {(cards || []).map((c, i) => (
          <button
            key={i}
            onClick={() => toggle(i)}
            className={`flashcard h-44 w-full text-left ${flipped[i] ? "flipped" : ""}`}
            aria-label={t.tapToFlip}
          >
            <div className="flashcard-inner">
              <div className="flashcard-face flashcard-front">
                <p className="text-sm font-medium leading-5">{c.question}</p>
                {c.hint && <p className="mt-2 text-xs text-neutral-500">Hint: {c.hint}</p>}
                <span className="mt-auto text-[10px] uppercase tracking-wide text-neutral-400">
                  {t.tapToFlip}
                </span>
              </div>
              <div className="flashcard-face flashcard-back">
                <p className="text-sm leading-5">{c.answer}</p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
