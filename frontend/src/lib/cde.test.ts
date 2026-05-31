import { describe, it, expect } from "vitest";
import { CDE_TRANSITIONS, nextState, canTransition, stateBadgeClass } from "./cde";

describe("CDE state transitions", () => {
  it("WIP can submit to Shared", () => {
    expect(nextState("WIP", "submit")).toBe("Shared");
  });

  it("Shared can approve to Published", () => {
    expect(nextState("Shared", "approve")).toBe("Published");
  });

  it("Published can archive to Archived", () => {
    expect(nextState("Published", "archive")).toBe("Archived");
  });

  it("returns null for invalid action", () => {
    expect(nextState("WIP", "approve")).toBeNull();
  });

  it("Archived has no further transitions", () => {
    expect(canTransition("Archived")).toBe(false);
  });

  it("WIP, Shared, Published can transition", () => {
    expect(canTransition("WIP")).toBe(true);
    expect(canTransition("Shared")).toBe(true);
    expect(canTransition("Published")).toBe(true);
  });

  it("every transition's next state is consistent", () => {
    for (const [, t] of Object.entries(CDE_TRANSITIONS)) {
      expect(t).toHaveProperty("action");
      expect(t).toHaveProperty("next");
      expect(t).toHaveProperty("label");
    }
  });

  it("badge class is defined for all states", () => {
    for (const s of ["WIP", "Shared", "Published", "Archived"] as const) {
      expect(stateBadgeClass(s)).toMatch(/bg-/);
    }
  });
});
