import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Explanation, Source } from "./components";
import ProfileForm from "./ProfileForm";
import type { Result } from "./types";

const result: Result = {
  scheme_id: "sample",
  scheme_name: "sample",
  status: "NEEDS_VERIFICATION",
  matched_rules: [],
  failed_rules: [],
  missing_information: ["gender"],
  verification_required: ["Institution must be notified"],
  rule_trace: [],
};

describe("uncertainty and provenance", () => {
  it("makes missing information and verification explicit", () => {
    render(<Explanation result={result} />);
    expect(screen.getByText("NEEDS VERIFICATION")).toBeInTheDocument();
    expect(screen.getByText("What we know")).toBeInTheDocument();
    expect(screen.getByText("What is missing")).toBeInTheDocument();
    expect(screen.getByText("What you need to verify")).toBeInTheDocument();
  });
  it("never invents a missing source URL", () => {
    render(
      <Source
        citation={{
          scheme_id: "sample",
          scheme_name: "sample",
          source_name: null,
          source_url: null,
          retrieved_from: "sample:record",
        }}
      />,
    );
    expect(
      screen.getByText("Source information unavailable in dataset"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
  it("rejects unsafe source link protocols", () => {
    render(
      <Source
        citation={{
          scheme_id: "sample",
          scheme_name: "sample",
          source_name: null,
          source_url: "javascript:alert(1)",
          retrieved_from: "sample:record",
        }}
      />,
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
  it("does not require optional fields at initial creation", () => {
    render(<ProfileForm profile={{}} onMatch={vi.fn()} />);
    expect(screen.getAllByRole("combobox")).toHaveLength(3);
    expect(screen.queryByLabelText("Gender")).not.toBeInTheDocument();
  });
  it("asks candidate-specific optional fields without requiring answers", () => {
    render(<ProfileForm profile={{}} missing={["gender"]} onMatch={vi.fn()} />);
    expect(screen.getByLabelText("Gender")).not.toBeRequired();
  });
});
