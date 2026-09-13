import type { SalesResponse } from "../../lib/types";

export function SuggestionEvidence({
  suggestion,
  language,
}: {
  suggestion: SalesResponse;
  language: "ar" | "en";
}) {
  if (suggestion.citations.length === 0) return null;

  return (
    <div
      className="citation-row"
      aria-label={
        language === "ar"
          ? "\u0645\u0635\u0627\u062f\u0631 \u0627\u0644\u0627\u0642\u062a\u0631\u0627\u062d"
          : "Grounding citations"
      }
    >
      {[...new Set(suggestion.citations)].map((citation) => (
        <code key={citation}>{citation}</code>
      ))}
    </div>
  );
}
