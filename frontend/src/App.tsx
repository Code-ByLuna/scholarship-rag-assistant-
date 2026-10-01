import { useEffect, useState } from "react";
import { api } from "./api";
import Assistant from "./Assistant";
import ProfileForm from "./ProfileForm";
import Workspace from "./Workspace";
import Dashboard from "./Dashboard";
import ScholarshipDetail from "./ScholarshipDetail";
import ScholarshipList from "./ScholarshipList";
import { navigate } from "./navigation";
import type { Citation, Profile, Result, Scheme } from "./types";

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
    <Workspace route={route} title={title}>
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

      {route === "/" && <Dashboard schemes={schemes} results={results} />}
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
        <ScholarshipDetail
          detail={detail}
          profile={profile}
          schemeId={schemeId}
          result={selectedResult}
        />
      )}
      {(route === "/" || route === "/scholarships") && (
        <ScholarshipList
          route={route}
          schemes={schemes}
          results={results}
          search={search}
          setSearch={setSearch}
          filter={filter}
          setFilter={setFilter}
          busy={busy}
          error={error}
          missing={missing}
          discover={discover}
        />
      )}
    </Workspace>
  );
}
