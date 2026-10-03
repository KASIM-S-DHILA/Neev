import { createElement, type ReactNode } from "react";
import type { EquationPreview } from "./storage/client";

function render(node: EquationPreview, key = 0, depth = 0): ReactNode {
  if (depth > 20 || node.kind === "unsupported") return null;
  if (node.kind === "text") return createElement("mtext", { key }, node.text);
  const tag = {
    row: "mrow",
    fraction: "mfrac",
    sup: "msup",
    sub: "msub",
    subsup: "msubsup",
  }[node.kind];
  return createElement(
    tag,
    { key },
    ...(node.children ?? []).map((child, index) =>
      render(child, index, depth + 1),
    ),
  );
}

export function SourceEquation({ equation }: { equation: EquationPreview }) {
  if (equation.kind === "unsupported")
    return (
      <p className="small-text">
        This equation cannot be previewed reliably. Compare it in the original
        slide or PDF export.
      </p>
    );
  return createElement(
    "math",
    {
      className: "source-equation",
      display: "block",
      "aria-label": "Equation preview from original slide structure",
    },
    render(equation),
  );
}
