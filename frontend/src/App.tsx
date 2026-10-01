import { useEffect, useState } from "react";
import { api } from "./api";
import Assistant from "./Assistant";
import ProfileForm from "./ProfileForm";
import { Explanation, Facts, Source, Status } from "./components";
import type { Citation, Profile, Result, Scheme } from "./types";

function navigate(path: string) {
  window.location.hash = path;
}

export default function App() {
  const [route, setRoute] = useState(window.location.hash.slice(1) || "/");
  const [profile, setProfile] = useState<Profile>(() => {
    try {
      return JSON.parse(sessionStorage.getItem("scholar-profile") || "{}");
    } catch {
      return {};
    }
  });
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [results, setResults] = useState<Result[]>([]);
  const [detail, setDetail] = useState<{
    scholarship: Scheme;
    citation: Citation;
  } | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const onHash = () => setRoute(window.location.hash.slice(1) || "/");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  useEffect(() => {
    let active = true;
    api<{ results: Scheme[] }>("/scholarships/search", { top_k: 16 })
      .then((d) => {
        if (active) setSchemes(d.results);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);
  const schemeId = route.startsWith("/scholarships/")
    ? decodeURIComponent(route.split("/")[2])
    : undefined;
  useEffect(() => {
    if (!schemeId) {
      setDetail(null);
      return;
    }
    let active = true;
    setBusy(true);
    setError("");
    api<{ scholarship: Scheme; citation: Citation }>(
      "/scholarships/" + encodeURIComponent(schemeId),
    )
      .then((d) => {
        if (active) setDetail(d);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, [schemeId]);
  async function match(values: Profile) {
    const data = await api<{ results: Result[] }>("/eligibility/check", {
      profile: values,
    });
    setProfile(values);
    sessionStorage.setItem("scholar-profile", JSON.stringify(values));
    setResults(data.results);
    setFilter("ALL");
    navigate("/scholarships");
  }
  async function discover(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await api<{ results: Scheme[] }>("/scholarships/search", {
        question: search,
        top_k: 16,
      });
      setSchemes(data.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search unavailable.");
    } finally {
      setBusy(false);
    }
  }
  const missing = [
    ...new Set(
      results
        .filter((r) => r.status !== "NOT_ELIGIBLE")
        .flatMap((r) => r.missing_information),
    ),
  ];
  const shownResults = results.filter(
    (r) => filter === "ALL" || r.status === filter,
  );
  const selectedResult = results.find((r) => r.scheme_id === schemeId);
  const title =
    route === "/profile"
      ? "Your student profile"
      : route === "/assistant"
        ? "Let’s find some clarity"
        : route.startsWith("/scholarships")
          ? "Explore your opportunities"
          : "Your next chapter starts here";
  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="#/">
          <span className="brand-icon">S</span>
          <span>
            Scholarship<span className="brand-sub">NAVIGATOR</span>
          </span>
        </a>
        <div className="workspace-label">STUDENT WORKSPACE</div>
        <nav aria-label="Main navigation">
          {[
            ["/", "◫", "Overview"],
            ["/profile", "◎", "My profile"],
            ["/scholarships", "▤", "Scholarships"],
            ["/assistant", "✦", "AI assistant"],
          ].map(([path, icon, label]) => (
            <a
              key={path}
              className={
                (path === "/" ? route === "/" : route.startsWith(path))
                  ? "active"
                  : ""
              }
              href={"#" + path}
            >
              <span>{icon}</span>
              {label}
              {label === "AI assistant" && <small>ASK</small>}
            </a>
          ))}
        </nav>
        <div className="sidebar-note">
          <span>✓</span>
          <strong>Clarity, with evidence.</strong>
          <p>See the rules. Know what’s missing. Take your next step.</p>
        </div>
        <div className="sidebar-footer">
          <span className="avatar">Y</span>
          <div>
            <strong>Your workspace</strong>
            <small>Student navigator</small>
          </div>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <span>Scholarship Eligibility Navigator</span>
          <span className="data-label">
            <i /> Dataset grounded
          </span>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <span className="eyebrow">
                A LITTLE GUIDANCE. MORE POSSIBILITY.
              </span>
              <h1>{title}</h1>
              <p>
                Find support for your education, with the information you need
                to move forward.
              </p>
            </div>
            {route !== "/profile" && (
              <button
                className="button primary"
                onClick={() => navigate("/profile")}
              >
                Update my profile ↗
              </button>
            )}
          </div>
          {error && (
            <div className="error" role="alert">
              {error}{" "}
              <button onClick={() => window.location.reload()}>Retry</button>
            </div>
          )}
          {busy && (
            <p role="status" className="loading">
              Loading scholarship information…
            </p>
          )}
          {route === "/" && (
            <>
              <section className="hero">
                <div>
                  <span className="eyebrow">MAKE YOUR NEXT MOVE</span>
                  <h2>
                    More opportunities.
                    <br />
                    Less guesswork.
                  </h2>
                  <p>
                    Start with your profile. Discover scholarship possibilities
                    and understand exactly where you stand.
                  </p>
                  <button
                    className="button light"
                    onClick={() => navigate("/profile")}
                  >
                    Build my profile <span>→</span>
                  </button>
                </div>
                <div className="hero-art" aria-hidden="true">
                  <div className="orb" />
                  <div className="book">
                    <span>
                      YOUR
                      <br />
                      NEXT
                      <br />
                      CHAPTER
                    </span>
                    <i>↗</i>
                  </div>
                  <span className="floating-tag">✦ A path worth exploring</span>
                </div>
              </section>
              <section className="stats" aria-label="Workspace summary">
                <div>
                  <span className="stat-icon">▤</span>
                  <strong>{schemes.length}</strong>
                  <span>Scholarships in the dataset</span>
                </div>
                <div>
                  <span className="stat-icon">✓</span>
                  <strong>
                    {results.filter((r) => r.status === "ELIGIBLE").length}
                  </strong>
                  <span>Confirmed rule matches</span>
                </div>
                <div>
                  <span className="stat-icon">◷</span>
                  <strong>
                    {
                      results.filter((r) => r.status === "NEEDS_VERIFICATION")
                        .length
                    }
                  </strong>
                  <span>Need more information</span>
                </div>
              </section>
              <div className="section-heading">
                <div>
                  <h2>Start exploring</h2>
                  <p>A few possibilities from the scholarship dataset.</p>
                </div>
                <a href="#/scholarships">View all scholarships →</a>
              </div>
            </>
          )}
          {route === "/profile" && (
            <ProfileForm
              key={JSON.stringify(profile)}
              profile={profile}
              missing={missing}
              onMatch={match}
            />
          )}
          {route === "/assistant" && <Assistant profile={profile} />}
          {schemeId && detail && (
            <section className="panel detail">
              <a href="#/scholarships" className="back">
                ← Back to scholarships
              </a>
              <div className="detail-heading">
                <span className="eyebrow">{detail.scholarship.provider}</span>
                <h2>{detail.scholarship.name}</h2>
                <p>{detail.scholarship.objective}</p>
                {selectedResult && <Status status={selectedResult.status} />}
              </div>
              <div className="detail-grid">
                <div>
                  {selectedResult && <Explanation result={selectedResult} />}
                  <h3>Benefits</h3>
                  <Facts value={detail.scholarship.benefits} />
                  <h3>Required documents</h3>
                  <Facts value={detail.scholarship.documents_required} />
                  <h3>Application procedure</h3>
                  <Facts value={detail.scholarship.application} />
                  <h3>Source notes</h3>
                  <Facts value={detail.scholarship.important_notes} />
                </div>
                <aside>
                  <div className="detail-aside">
                    <h3>Understand your next step</h3>
                    <p>
                      Eligibility depends on the full set of sourced conditions.
                      An award may require official verification.
                    </p>
                    <button
                      className="button primary"
                      onClick={() => navigate("/profile")}
                    >
                      Check my profile →
                    </button>
                    <Source citation={detail.citation} />
                  </div>
                </aside>
              </div>
              <details>
                <summary>All eligibility conditions in the dataset</summary>
                <Facts value={detail.scholarship.eligibility} />
              </details>
              <Assistant profile={profile} schemeId={schemeId} />
            </section>
          )}
          {(route === "/" || route === "/scholarships") && (
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
                      <option value="NEEDS_VERIFICATION">
                        NEEDS VERIFICATION
                      </option>
                      <option value="NOT_ELIGIBLE">NOT ELIGIBLE</option>
                    </select>
                  )}
                </div>
              )}
              {route === "/scholarships" && !!results.length && (
                <div className="notice">
                  Your profile was checked against {results.length}{" "}
                  scholarships. Missing information remains unknown.
                  {!!missing.length && (
                    <a href="#/profile"> Add relevant details →</a>
                  )}
                </div>
              )}
              <div className="cards">
                {(route === "/scholarships" && results.length
                  ? shownResults
                      .filter((r) =>
                        schemes.some((s) => s.scheme_id === r.scheme_id),
                      )
                      .map((r) => ({
                        name: r.scheme_name,
                        scheme_id: r.scheme_id,
                        provider:
                          schemes.find((s) => s.scheme_id === r.scheme_id)
                            ?.provider || "",
                        result: r,
                      }))
                  : (route === "/" ? schemes.slice(0, 4) : schemes).map(
                      (s) => ({ ...s, result: undefined }),
                    )
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
                            ? s.result.failed_rules.length +
                              " condition(s) failed"
                            : "All applicable hard rules passed"}
                      </p>
                    ) : (
                      <p>
                        Explore benefits, required documents, and sourced
                        eligibility conditions.
                      </p>
                    )}
                    <div className="card-footer">
                      <span>
                        {s.result
                          ? "Explainable rule result"
                          : "Source record available"}
                      </span>
                      <a
                        href={
                          "#/scholarships/" + encodeURIComponent(s.scheme_id)
                        }
                      >
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
          )}
          <footer className="page-footer">
            <span>Scholarship Navigator</span>
            <span>Facts from sources. Decisions from rules.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
