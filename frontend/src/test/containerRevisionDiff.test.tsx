import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router";
import ContainerDetailPage from "@/pages/ContainerDetailPage";
import * as apiModule from "@/lib/api";
import * as containersApiModule from "@/api/containers";
import type {
  ContainerRevisionItem,
  RevisionDiffResponse,
} from "@/api/containers";
import type { InformationContainer } from "@/types";

// ─── fixtures ─────────────────────────────────────────────────────────────

const PROJECT_ID = "proj-1";

const CONTAINER: InformationContainer = {
  id: "cont-1",
  project_id: PROJECT_ID,
  identifier: "PROJ-ORG-ZZ-GF-DR-AR-0001",
  title: "橋梁一般図",
  container_type: "drawing",
  current_state: "WIP",
  current_revision: "P02",
  current_branch: null,
  security_level: "limited",
  naming_valid: true,
  naming_issues: null,
  created_by: "user-1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-05T00:00:00Z",
};

const REVISION_1: ContainerRevisionItem = {
  id: "rev-1",
  revision_code: "P01",
  version_code: "P01.01",
  change_reason: "Initial issue",
  change_summary: "First draft",
  created_by: "user-1",
  created_at: "2026-01-01T00:00:00Z",
  file: {
    id: "file-1",
    original_filename: "bridge-v1.pdf",
    file_size_bytes: 1024,
    checksum_sha256: "a".repeat(64),
  },
};

const REVISION_2: ContainerRevisionItem = {
  id: "rev-2",
  revision_code: "P02",
  version_code: "P02.01",
  change_reason: "Client comments addressed",
  change_summary: "Revised layout",
  created_by: "user-1",
  created_at: "2026-01-05T00:00:00Z",
  file: {
    id: "file-2",
    original_filename: "bridge-v2.pdf",
    file_size_bytes: 2048,
    checksum_sha256: "b".repeat(64),
  },
};

const DIFF_RESPONSE: RevisionDiffResponse = {
  container_id: "cont-1",
  from_revision: {
    id: "rev-1",
    revision_code: "P01",
    version_code: "P01.01",
    change_reason: "Initial issue",
    change_summary: "First draft",
    created_by: "user-1",
    created_at: "2026-01-01T00:00:00Z",
    file: {
      id: "file-1",
      original_filename: "bridge-v1.pdf",
      content_type: "application/pdf",
      file_size_bytes: 1024,
      checksum_sha256: "a".repeat(64),
    },
  },
  to_revision: {
    id: "rev-2",
    revision_code: "P02",
    version_code: "P02.01",
    change_reason: "Client comments addressed",
    change_summary: "Revised layout",
    created_by: "user-1",
    created_at: "2026-01-05T00:00:00Z",
    file: {
      id: "file-2",
      original_filename: "bridge-v2.pdf",
      content_type: "application/pdf",
      file_size_bytes: 2048,
      checksum_sha256: "b".repeat(64),
    },
  },
  text_diffs: [
    {
      field: "revision_code",
      from_value: "P01",
      to_value: "P02",
      changed: true,
      diff_lines: ["-P01", "+P02"],
    },
    {
      field: "version_code",
      from_value: "P01.01",
      to_value: "P02.01",
      changed: true,
      diff_lines: ["-P01.01", "+P02.01"],
    },
    {
      field: "change_reason",
      from_value: "Initial issue",
      to_value: "Client comments addressed",
      changed: true,
      diff_lines: ["-Initial issue", "+Client comments addressed"],
    },
    {
      field: "change_summary",
      from_value: "First draft",
      to_value: "Revised layout",
      changed: true,
      diff_lines: ["-First draft", "+Revised layout"],
    },
  ],
  file_diff: {
    from_file: {
      id: "file-1",
      original_filename: "bridge-v1.pdf",
      content_type: "application/pdf",
      file_size_bytes: 1024,
      checksum_sha256: "a".repeat(64),
    },
    to_file: {
      id: "file-2",
      original_filename: "bridge-v2.pdf",
      content_type: "application/pdf",
      file_size_bytes: 2048,
      checksum_sha256: "b".repeat(64),
    },
    original_filename_changed: true,
    content_type_changed: false,
    file_size_bytes_changed: true,
    checksum_sha256_changed: true,
    identical: false,
  },
};

// ─── helpers ──────────────────────────────────────────────────────────────

function wrap() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter
      initialEntries={[`/projects/${PROJECT_ID}/containers/${CONTAINER.id}`]}
    >
      <QueryClientProvider client={qc}>
        <Routes>
          <Route
            path="projects/:projectId/containers/:containerId"
            element={<ContainerDetailPage />}
          />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("ContainerDetailPage - revision diff (Issue #52)", () => {
  it("改訂版比較UIから差分APIが呼ばれ、結果テーブルが表示される", async () => {
    vi.spyOn(apiModule.api, "get").mockImplementation((url: string) => {
      if (url === `/projects/${PROJECT_ID}/containers`) {
        return Promise.resolve({
          data: { items: [CONTAINER], total: 1, page: 1, size: 20 },
        }) as never;
      }
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });
    vi.spyOn(containersApiModule, "listFiles").mockResolvedValue([]);
    vi.spyOn(containersApiModule, "listContainerRevisions").mockResolvedValue([
      REVISION_2,
      REVISION_1,
    ]);
    const diffSpy = vi
      .spyOn(containersApiModule, "getContainerRevisionDiff")
      .mockResolvedValue(DIFF_RESPONSE);

    const user = userEvent.setup();
    wrap();

    // Switch to the revisions tab.
    await user.click(await screen.findByText("改訂履歴"));
    expect(await screen.findByText("改訂版比較（Diff）")).toBeInTheDocument();

    await user.selectOptions(
      screen.getByLabelText("比較元の改訂"),
      REVISION_1.id,
    );
    await user.selectOptions(
      screen.getByLabelText("比較先の改訂"),
      REVISION_2.id,
    );
    await user.click(screen.getByText("比較"));

    await waitFor(() => {
      expect(diffSpy).toHaveBeenCalledWith(
        PROJECT_ID,
        CONTAINER.id,
        REVISION_1.id,
        REVISION_2.id,
      );
    });

    expect((await screen.findAllByText("変更あり")).length).toBeGreaterThan(0);
    expect(
      await screen.findByText("ファイルに差分があります。"),
    ).toBeInTheDocument();
  });
});
