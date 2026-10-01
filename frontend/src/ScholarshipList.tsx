import { Status } from "./components";
import type { Result, Scheme } from "./types";
type Props = {
  route: string;
  schemes: Scheme[];
  results: Result[];
  search: string;
  setSearch: (v: string) => void;
  filter: string;
  setFilter: (v: string) => void;
  busy: boolean;
  error: string;
  missing: string[];
  discover: (event: React.FormEvent) => Promise<void>;
};
export default function ScholarshipList({
  route,
  schemes,
  results,
  search,
  setSearch,
  filter,
  setFilter,
  busy,
  error,
  missing,
  discover,
}: Props) {
  const shownResults = results.filter(
    (r) => filter === "ALL" || r.status === filter,
  );
  return (
    <>
      {route === "/scholarships" && (
        <div className="search-row">
          <form onSubmit={discover}>
            <label className="sr-only" htmlFor="search">
              Search scholarships
            </label>
            <input
              id="search"
              placeholder="Search a scholarship, category, or keyword…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button className="button primary" disabled={busy}>
              Search
            </button>
          </form>
          {!!results.length && (
            <select
              aria-label="Filter eligibility results"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="ALL">All results</option>
              <option value="ELIGIBLE">ELIGIBLE</option>
              <option value="NEEDS_VERIFICATION">NEEDS VERIFICATION</option>
              <option value="NOT_ELIGIBLE">NOT ELIGIBLE</option>
            </select>
          )}
        </div>
      )}
      {route === "/scholarships" && !!results.length && (
        <div className="notice">
          Your profile was checked against {results.length} scholarships.
          Missing information remains unknown.
          {!!missing.length && <a href="#/profile"> Add relevant details →</a>}
        </div>
      )}
      <div className="cards">
        {(route === "/scholarships" && results.length
          ? shownResults
              .filter((r) => schemes.some((s) => s.scheme_id === r.scheme_id))
              .map((r) => ({
                name: r.scheme_name,
                scheme_id: r.scheme_id,
                provider:
                  schemes.find((s) => s.scheme_id === r.scheme_id)?.provider ||
                  "",
                result: r,
              }))
          : (route === "/" ? schemes.slice(0, 4) : schemes).map((s) => ({
              ...s,
              result: undefined,
            }))
        ).map((s) => (
          <article className="scholar-card" key={s.scheme_id}>
            <div className="card-top">
              <span className="scheme-icon">▤</span>
              {s.result ? (
                <Status status={s.result.status} />
              ) : (
                <span className="badge explore">EXPLORE</span>
              )}
            </div>
            <span className="provider">{s.provider}</span>
            <h3>{s.name}</h3>
            {s.result ? (
              <p>
                {s.result.status === "NEEDS_VERIFICATION"
                  ? s.result.missing_information.length +
                    " missing details · external conditions to verify"
                  : s.result.status === "NOT_ELIGIBLE"
                    ? s.result.failed_rules.length + " condition(s) failed"
                    : "All applicable hard rules passed"}
              </p>
            ) : (
              <p>
                Explore benefits, required documents, and sourced eligibility
                conditions.
              </p>
            )}
            <div className="card-footer">
              <span>
                {s.result
                  ? "Explainable rule result"
                  : "Source record available"}
              </span>
              <a href={"#/scholarships/" + encodeURIComponent(s.scheme_id)}>
                View details ↗
              </a>
            </div>
          </article>
        ))}
      </div>
      {!schemes.length && !busy && !error && (
        <div className="panel empty">
          No scholarships found. Try another search.
        </div>
      )}
    </>
  );
}
