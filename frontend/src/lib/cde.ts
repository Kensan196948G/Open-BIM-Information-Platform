import type { ContainerState } from "@/types";

/**
 * CDE state transition map (mirrors backend VALID_TRANSITIONS).
 * Used by the UI to decide which transition button to show.
 */
export const CDE_TRANSITIONS: Partial<
  Record<ContainerState, { action: string; label: string; next: ContainerState }>
> = {
  WIP: { action: "submit", label: "Shared へ提出", next: "Shared" },
  Shared: { action: "approve", label: "Published へ承認", next: "Published" },
  Published: { action: "archive", label: "Archive へ保管", next: "Archived" },
};

/** Returns the next state for a given (state, action), or null if invalid. */
export function nextState(
  state: ContainerState,
  action: string
): ContainerState | null {
  const t = CDE_TRANSITIONS[state];
  return t && t.action === action ? t.next : null;
}

/** Returns true if a container in the given state can still transition. */
export function canTransition(state: ContainerState): boolean {
  return state in CDE_TRANSITIONS;
}

const STATE_BADGE: Record<ContainerState, string> = {
  WIP: "bg-gray-100 text-gray-700",
  Shared: "bg-blue-100 text-blue-700",
  Published: "bg-green-100 text-green-700",
  Archived: "bg-amber-100 text-amber-700",
};

export function stateBadgeClass(state: ContainerState): string {
  return STATE_BADGE[state];
}
