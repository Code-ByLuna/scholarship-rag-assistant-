import type { Citation, Result } from "./types";

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
        <strong>{citation.source_name || "Dataset source"}</strong>
        {url ? (
          <a href={url} target="_blank" rel="noreferrer">
            View source
          </a>
        ) : (
          <small>Source information unavailable in dataset</small>
        )}
        <small>{citation.original_record_key || citation.scheme_id}</small>
      </div>
    </div>
  );
}

export function Status({ status }: { status: Result["status"] }) {
  return (
    <span className={"badge " + status.toLowerCase()}>
      <span>●</span> {status.replaceAll("_", " ")}
    </span>
  );
}

export function Explanation({ result }: { result: Result }) {
  return (
    <section className="explanation">
      <Status status={result.status} />
      <h3>What we know</h3>
      {result.matched_rules.length ? (
        <ul>
          {result.matched_rules.map((r, i) => (
            <li key={i}>{human(r.field)}: condition passed</li>
          ))}
        </ul>
      ) : (
        <p>No supplied values establish a passing condition yet.</p>
      )}
      {!!result.failed_rules.length && (
        <>
          <h3>Conditions that failed</h3>
          <ul>
            {result.failed_rules.map((r, i) => (
              <li key={i}>
                {human(r.field)} — {r.description}
              </li>
            ))}
          </ul>
        </>
      )}
      <h3>What is missing</h3>
      <p>
        {result.missing_information.length
          ? result.missing_information.map(human).join(", ")
          : "No missing mapped profile fields."}
      </p>
      <h3>What you need to verify</h3>
      {result.verification_required.length ? (
        <ul>
          {result.verification_required.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      ) : (
        <p>No external conditions identified.</p>
      )}
      <details>
        <summary>View every rule and its source</summary>
        {result.rule_trace.map((r, i) => (
          <div className="trace" key={i}>
            <strong>
              {human(r.field)} · {r.status.replaceAll("_", " ")}
            </strong>
            <p>{r.description}</p>
            <small>
              {r.explanation} Source: {r.source_path}
            </small>
          </div>
        ))}
      </details>
    </section>
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
