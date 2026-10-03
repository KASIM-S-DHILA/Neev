import type { ContentUnit, VisualTable } from "./storage/client";

type CloudVisual = NonNullable<ContentUnit["metadata"]["cloud_visuals"]>[number];

export function CloudTranscription({ entry, expandedText = false }: { entry: CloudVisual; expandedText?: boolean }) {
  const extraction = entry.extraction;
  if (!extraction) return null;
  return <>
    <p className="small-text">Compare this transcription with the source preview before using it.</p>
    {extraction.is_blank && <p>The model reported an empty image. Check the original.</p>}
    {!!extraction.text_lines.length && (expandedText ? <pre className="extracted-text">{extraction.text_lines.join("\n")}</pre> :
      <details className="content-provenance"><summary>Transcribed text</summary><pre className="extracted-text">{extraction.text_lines.join("\n")}</pre></details>)}
    {extraction.tables.map((table, index) => <SourceTable key={index} table={table} />)}
    {!!extraction.equations.length && <><h4>Equation transcription (LaTeX)</h4><pre className="extracted-text">{extraction.equations.join("\n\n")}</pre></>}
    {!!extraction.diagram_nodes.length && <><h4>Diagram labels and connections</h4><p>{extraction.diagram_nodes.join(" · ")}</p>
      <ul>{extraction.diagram_edges.map((edge, index) => <li key={index}>{edge.from} → {edge.to}{edge.label ? ` (${edge.label})` : ""}</li>)}</ul></>}
    {!!extraction.uncertainties.length && <p className="content-warning">Needs review: {extraction.uncertainties.join(" · ")}</p>}
  </>;
}

export function ExtractedText({ unit }: { unit: ContentUnit }) {
  const cloud = unit.metadata.cloud_visuals?.filter(entry => entry.status === "complete" && entry.extraction) ?? [];
  const local = unit.text ? <pre className="extracted-text">{unit.text}</pre> :
    <p className="content-no-text">No readable local text for this location. The original remains available through Save original.</p>;
  if (!cloud.length) return local;
  return <div className="structured-extraction" data-testid="cloud-extracted-text">
    {cloud.map((entry, index) => <section key={index}>
      <h3>{entry.provider && entry.provider !== "groq" ? "Archived cloud extraction" : "Groq extraction"} · Unverified{cloud.length > 1 ? ` · Visual ${index + 1}` : ""}</h3>
      <CloudTranscription entry={entry} expandedText />
    </section>)}
    <details className="content-provenance"><summary>Local extraction retained</summary>
      {unit.warning && <p className="content-warning">{unit.warning}</p>}{local}
    </details>
  </div>;
}

export function SourceTable({ table }: { table: VisualTable }) {
  return <div className="source-table-wrap">
    <table className="source-table">
      {!!table.headers.length && <thead><tr>{table.headers.map((cell, index) => <th key={index}>{cell}</th>)}</tr></thead>}
      <tbody>{table.rows.map((row, index) => <tr key={index}>{row.map((cell, column) => <td key={column}>{cell}</td>)}</tr>)}</tbody>
    </table>
    {table.notes.map((note, index) => <p className="small-text" key={index}>{note}</p>)}
  </div>;
}

export function VisualExtraction({ unit }: { unit: ContentUnit }) {
  return <div className="structured-extraction">
    {!!unit.metadata.native_tables?.length && <section>
      <h3>Native table cells</h3>
      <p className="small-text">Read directly from the presentation. Compare merged cells with the original.</p>
      {unit.metadata.native_tables.map((table, index) => <SourceTable key={index} table={table} />)}
    </section>}
    {unit.metadata.cloud_visuals?.map((entry, index) => <section key={index}>
      <h3>{entry.status === "local" ? "Retained locally" : entry.provider && entry.provider !== "groq" ? "Archived cloud extraction · Unverified" : "Groq transcription · Unverified"}</h3>
      {entry.status === "local" && <p className="small-text">{entry.routing.reasons.join(" · ")}</p>}
      {entry.error && <p className="content-warning">{entry.error}</p>}
      <CloudTranscription entry={entry} />
      {entry.status !== "local" && <details className="content-provenance"><summary>Processing details</summary>
        <p className="small-text">Model: {entry.model}. {entry.routing.reasons.join(" · ")}</p>
      </details>}
    </section>)}
    {!unit.metadata.native_tables?.length && !unit.metadata.cloud_visuals?.length && <p className="small-text">No structured extraction saved for this location yet.</p>}
  </div>;
}
