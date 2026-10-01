import type { Citation } from "./types";

export function human(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function Source({ citation }: { citation: Citation }) {
  let url: string | null = null;
  try {
    const parsed = new URL(citation.source_url || "");
    if (["http:", "https:"].includes(parsed.protocol)) url = parsed.href;
  } catch {
    /* Missing source URLs stay missing. */
  }
  return (
    <div className="source">
      <span className="source-mark">↗</span>
      <div>
        <strong>{citation.scheme_name}</strong>
        {url ? (
          <a href={url} target="_blank" rel="noreferrer">
            View source
          </a>
        ) : (
          <small>Source information unavailable in dataset</small>
        )}
        <small>{citation.source_name || "Scholarship dataset"}</small>
      </div>
    </div>
  );
}

export function Facts({ value }: { value: unknown }) {
  if (value === null || value === undefined)
    return <p>Not specified in the dataset.</p>;
  if (Array.isArray(value))
    return (
      <ul>
        {value.map((v, i) => (
          <li key={i}>
            <Facts value={v} />
          </li>
        ))}
      </ul>
    );
  if (typeof value === "object")
    return (
      <dl className="facts">
        {Object.entries(value).map(([k, v]) => (
          <div key={k}>
            <dt>{human(k)}</dt>
            <dd>
              <Facts value={v} />
            </dd>
          </div>
        ))}
      </dl>
    );
  return (
    <span>
      {typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)}
    </span>
  );
}
