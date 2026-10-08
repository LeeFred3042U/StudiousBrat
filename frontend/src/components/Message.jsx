import Markdown from "./Markdown";
import Flashcards from "./Flashcards";
import MermaidChart from "./MermaidChart";
import MemeCards from "./MemeCards";
import TeachBackCard from "./TeachBackCard";

// Claude.ai-style: student messages right-aligned in a filled bubble;
// assistant messages read as plain formatted text in the content column.
export default function Message({ msg }) {
  if (msg.role === "student") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl bg-accent px-4 py-2.5 text-white shadow-sm">
          {msg.content}
        </div>
      </div>
    );
  }
  return (
    <div className="font-serif text-ink">
      <Markdown>{msg.content}</Markdown>
      {(msg.assets || []).map((a, i) => (
        <div key={i} className="mt-4 font-sans">
          {a.asset_type === "flashcards" && <Flashcards cards={a.content.cards} />}
          {a.asset_type === "mermaid" && <MermaidChart source={a.content.mermaid_source} />}
          {a.asset_type === "memes" && <MemeCards memes={a.content.memes} />}
          {a.asset_type === "evaluation" && <TeachBackCard evaluation={a.content} />}
        </div>
      ))}
    </div>
  );
}
