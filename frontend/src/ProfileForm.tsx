import { useState } from "react";
import { api } from "./api";
import { human } from "./components";
import type { Profile } from "./types";

const initialFields = [
  "state",
  "category",
  "annual_family_income",
  "course_level",
  "year_of_study",
  "study_mode",
];
const options: Record<string, string[]> = {
  category: ["General", "OBC", "EBC", "DNT", "SC", "ST", "SEBC"],
  course_level: [
    "school",
    "undergraduate",
    "postgraduate",
    "diploma",
    "certificate",
    "mphil",
    "phd",
  ],
  study_mode: ["regular", "distance", "correspondence", "part_time"],
  gender: ["female", "male", "other"],
  course_type: ["professional", "non_professional"],
};
const booleanFields = new Set([
  "receiving_other_scholarship",
  "institution_approved",
  "single_girl_child",
  "lateral_entry",
  "valid_gate_score",
  "valid_ceed_score",
]);
const numberFields = new Set([
  "annual_family_income",
  "year_of_study",
  "age",
  "disability_percentage",
  "class12_percentile",
  "university_rank",
  "family_scholarship_holders",
  "school_class",
  "class7_marks",
  "undergraduate_marks",
]);
const supported = new Set([
  ...initialFields,
  ...Object.keys(options),
  ...booleanFields,
  ...numberFields,
  "citizenship",
  "institution_type",
  "sports_achievement",
  "sports_event_level",
]);

export default function ProfileForm({
  profile,
  onMatch,
  missing = [],
}: {
  profile: Profile;
  onMatch: (p: Profile) => Promise<void>;
  missing?: string[];
}) {
  const [values, setValues] = useState<Profile>(profile);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const additional = [...new Set(missing)].filter(
    (f) => supported.has(f) && !initialFields.includes(f),
  );
  function update(field: string, value: string) {
    setValues((p) => ({
      ...p,
      [field]:
        value === ""
          ? null
          : booleanFields.has(field)
            ? value === "true"
            : numberFields.has(field)
              ? Number(value)
              : value,
    }));
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/profile/validate", values);
      await onMatch(values);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile.");
    } finally {
      setBusy(false);
    }
  }
  function field(name: string, required = false) {
    const choices = booleanFields.has(name) ? ["true", "false"] : options[name];
    const id = "profile-" + name;
    return (
      <label key={name} htmlFor={id}>
        {name === "family_scholarship_holders"
          ? "Existing family scholarship recipients (excluding you)"
          : human(name)}{" "}
        {required && <span className="required">*</span>}
        {choices ? (
          <select
            id={id}
            value={
              values[name] === null || values[name] === undefined
                ? ""
                : String(values[name])
            }
            required={required}
            onChange={(e) => update(name, e.target.value)}
          >
            <option value="">
              {required ? "Select an option" : "Unknown / not provided"}
            </option>
            {choices.map((c) => (
              <option key={c} value={c}>
                {booleanFields.has(name)
                  ? c === "true"
                    ? "Yes"
                    : "No"
                  : human(c)}
              </option>
            ))}
          </select>
        ) : (
          <input
            id={id}
            type={numberFields.has(name) ? "number" : "text"}
            min={name === "year_of_study" ? 1 : 0}
            step={
              [
                "annual_family_income",
                "disability_percentage",
                "class12_percentile",
              ].includes(name)
                ? "any"
                : 1
            }
            value={
              values[name] === null || values[name] === undefined
                ? ""
                : String(values[name])
            }
            onChange={(e) => update(name, e.target.value)}
            required={required}
            placeholder={
              name === "annual_family_income"
                ? "Annual amount in INR"
                : "Enter " + human(name).toLowerCase()
            }
          />
        )}
      </label>
    );
  }
  return (
    <form className="panel profile-form" onSubmit={submit}>
      <div className="panel-heading">
        <div>
          <span className="eyebrow">YOUR STARTING POINT</span>
          <h2>A few details. A clearer path.</h2>
          <p>
            Enter what you know. We’ll ask for more only when a scholarship
            needs it.
          </p>
        </div>
      </div>
      <div className="form-grid">
        {initialFields.map((f) => field(f, true))}
      </div>
      {!!additional.length && (
        <div className="follow-up">
          <h3>Details needed by candidate scholarships</h3>
          <p>
            These are optional. Leaving a field unknown keeps its condition
            unverified.
          </p>
          <div className="form-grid">{additional.map((f) => field(f))}</div>
        </div>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="form-footer">
        <small>Your profile is used only for the rules you can see.</small>
        <button className="button primary" disabled={busy}>
          {busy ? "Checking rules…" : "Find my scholarships →"}
        </button>
      </div>
    </form>
  );
}
