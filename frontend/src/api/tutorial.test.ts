import { describe, expect, it } from "vitest";
import type { TutorialStep } from "../types";
import { stepToRequestDetail } from "./tutorial";

const baseStep: TutorialStep = {
  title: "GraphQL step",
  instructions: "",
  method: "POST",
  url: "http://localhost:8000/mock/wikidata/graphql",
  params: {},
  headers: {},
  body: "",
  pre_script: "",
  post_script: "",
  variable_overrides: {},
  graphql: { query: '{ entity(id: "Q42") { label } }', variables: {} },
};

describe("stepToRequestDetail", () => {
  it("carries the graphql config into the frontmatter", () => {
    const detail = stepToRequestDetail(baseStep);
    expect(detail.frontmatter.graphql).toEqual(baseStep.graphql);
    expect(detail.frontmatter.method).toBe("POST");
  });

  it("leaves graphql undefined when the step has none", () => {
    const detail = stepToRequestDetail({ ...baseStep, graphql: undefined });
    expect(detail.frontmatter.graphql).toBeUndefined();
  });
});
