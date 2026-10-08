import { t } from "../locale/en";

// The in-app "what we store" privacy page.
export default function PrivacyModal({ onClose }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="font-serif text-xl font-bold">{t.whatWeStore}</h2>
        <p className="mt-3 whitespace-pre-line text-sm leading-6 text-neutral-700">
          {t.privacyBody}
        </p>
        <button
          onClick={onClose}
          className="mt-5 w-full rounded-lg bg-accent py-2 text-sm font-medium text-white"
        >
          {t.gotItButton}
        </button>
      </div>
    </div>
  );
}
