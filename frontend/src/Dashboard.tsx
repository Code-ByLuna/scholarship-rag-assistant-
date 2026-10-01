import type { Scheme, Result } from "./types";
import { navigate } from "./navigation";
export default function Dashboard({
  schemes,
  results,
}: {
  schemes: Scheme[];
  results: Result[];
}) {
  return (
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
            Start with your profile. Discover scholarship possibilities and
            understand exactly where you stand.
          </p>
          <button className="button light" onClick={() => navigate("/profile")}>
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
            {results.filter((r) => r.status === "NEEDS_VERIFICATION").length}
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
  );
}
