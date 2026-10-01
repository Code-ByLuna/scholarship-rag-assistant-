import type { Scheme } from "./types";
type Props = {
  route: string;
  schemes: Scheme[];
  search: string;
  setSearch: (v: string) => void;
  busy: boolean;
  error: string;
  discover: (event: React.FormEvent) => Promise<void>;
};
export default function ScholarshipList({
  route,
  schemes,
  search,
  setSearch,
  busy,
  error,
  discover,
}: Props) {
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
        </div>
      )}
      <div className="cards">
        {(route === "/" ? schemes.slice(0, 4) : schemes).map((s) => (
          <article className="scholar-card" key={s.scheme_id}>
            <div className="card-top">
              <span className="scheme-icon">▤</span>
              <span className="badge explore">EXPLORE</span>
            </div>
            <span className="provider">{s.provider}</span>
            <h3>{s.name}</h3>
            <p>
              Explore benefits, required documents, and sourced eligibility
              criteria.
            </p>
            <div className="card-footer">
              <span>Source record available</span>
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
