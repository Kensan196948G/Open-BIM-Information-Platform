import { afterEach, describe, expect, it, vi } from "vitest";

import { DownloadHttpError, downloadFileToWritable } from "@/api/containers";

describe("downloadFileToWritable", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("aborts the destination when the download fails before streaming", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 503 })),
    );
    const abort = vi.fn().mockResolvedValue(undefined);
    const writable = { abort } as unknown as FileSystemWritableFileStream;

    const result = downloadFileToWritable("project", "container", "file", writable);

    await expect(result).rejects.toEqual(expect.objectContaining({ status: 503 }));
    await expect(result).rejects.toBeInstanceOf(DownloadHttpError);
    expect(abort).toHaveBeenCalledOnce();
  });
});
