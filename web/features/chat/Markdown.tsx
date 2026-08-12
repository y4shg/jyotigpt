"use client";

// Markdown — product chat renderer: react-markdown + GFM (tables) + highlight.js
// with a copy button on code blocks. A streaming cursor is appended inline when
// the message is still being generated.

import { useState, type ReactElement, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Check, Copy } from "lucide-react";

function CodeBlock({ children }: { children?: ReactNode }) {
  const [copied, setCopied] = useState(false);
  const codeEl = (Array.isArray(children) ? children[0] : children) as
    | ReactElement<{ className?: string; children?: ReactNode }>
    | undefined;
  const className = codeEl?.props?.className ?? "";
  const language = /language-([\w-]+)/.exec(className)?.[1] ?? "text";
  const code = String(codeEl?.props?.children ?? "").replace(/\n$/, "");

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable — nothing to do
    }
  };

  return (
    <div className="w-full rounded-lg overflow-hidden border border-gray-100 dark:border-gray-800 bg-gray-100/50 dark:bg-gray-800/40 my-0">
      <div className="flex items-center justify-between pl-3 pr-1 py-1 text-xs text-gray-500 dark:text-gray-400">
        <span className="uppercase tracking-wide font-mona">{language}</span>
        <button
          type="button"
          onClick={copy}
          aria-label="Copy code"
          className="flex items-center gap-1 rounded-md px-2 py-1 hover:bg-gray-200/70 dark:hover:bg-gray-700/60 transition text-gray-600 dark:text-gray-300"
        >
          {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
          <span>{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      <div className="overflow-x-auto">
        <pre className="!my-0 !bg-transparent p-3">
          <code className={className}>{code}</code>
        </pre>
      </div>
    </div>
  );
}

export function Markdown({
  content,
  streaming = false,
}: {
  content: string;
  streaming?: boolean;
}) {
  const rendered = streaming && content.trim().length > 0 ? `${content} ▍` : content;

  return (
    <div className="markdown-prose w-full min-w-full">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
          code: ({ className, children }) => {
            if (className && /language-/.test(className)) {
              // block code handled by CodeBlock
              return <code className={className}>{children}</code>;
            }
            return <code className="codespan">{children}</code>;
          },
          table: ({ children }) => (
            <div className="overflow-x-auto my-0">
              <table className="!my-0">{children}</table>
            </div>
          ),
        }}
      >
        {rendered}
      </ReactMarkdown>
      {streaming && content.trim().length === 0 && (
        <div className="text-sm text-gray-500 dark:text-gray-400 animate-pulse">
          Thinking…
        </div>
      )}
    </div>
  );
}
