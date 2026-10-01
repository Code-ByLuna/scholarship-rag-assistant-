import Assistant from "./Assistant";
import { Explanation, Facts, Source, Status } from "./components";
import { navigate } from "./navigation";
import type { Citation, Scheme, Profile, Result } from "./types";
export default function ScholarshipDetail({
  detail,
  profile,
  schemeId,
  result,
}: {
  detail: { scholarship: Scheme; citation: Citation };
  profile: Profile;
  schemeId: string;
  result?: Result;
}) {
  return (
    <section className="panel detail">
      <a href="#/scholarships" className="back">
        ← Back to scholarships
      </a>
      <div className="detail-heading">
        <span className="eyebrow">{detail.scholarship.provider}</span>
        <h2>{detail.scholarship.name}</h2>
        <p>{detail.scholarship.objective}</p>
        {result && <Status status={result.status} />}
      </div>
      <div className="detail-grid">
        <div>
          {result && <Explanation result={result} />}
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
              Eligibility depends on the full set of sourced conditions. An
              award may require official verification.
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
  );
}
