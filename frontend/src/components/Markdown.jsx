import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Standard Markdown rendering for assistant text: headings for the
// "Explanation" / "Analogy" sections, numbered lists for the Feynman steps,
// bold for key terms.
export default function Markdown({ children }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ node, ...p }) => <h1 className="mb-2 mt-6 font-serif text-2xl font-bold" {...p} />,
        h2: ({ node, ...p }) => <h2 className="mb-2 mt-5 font-serif text-xl font-bold" {...p} />,
        h3: ({ node, ...p }) => <h3 className="mb-1 mt-4 font-serif text-lg font-bold" {...p} />,
        p: ({ node, ...p }) => <p className="my-3 leading-7" {...p} />,
        ol: ({ node, ...p }) => <ol className="my-3 list-decimal space-y-2 pl-6 leading-7" {...p} />,
        ul: ({ node, ...p }) => <ul className="my-3 list-disc space-y-1 pl-6 leading-7" {...p} />,
        li: ({ node, ...p }) => <li className="pl-1" {...p} />,
        strong: ({ node, ...p }) => <strong className="font-semibold" {...p} />,
        a: ({ node, ...p }) => <a className="text-accent underline" {...p} />,
        blockquote: ({ node, ...p }) => (
          <blockquote className="my-3 border-l-2 border-neutral-300 pl-4 text-neutral-600" {...p} />
        ),
        code: ({ node, className, children, ...p }) => {
          const isBlock = /language-/.test(className || "");
          return isBlock ? (
            <code className="block overflow-x-auto rounded-lg bg-neutral-100 p-3 text-sm" {...p}>
              {children}
            </code>
          ) : (
            <code className="rounded bg-neutral-100 px-1 py-0.5 text-sm" {...p}>
              {children}
            </code>
          );
        },
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
