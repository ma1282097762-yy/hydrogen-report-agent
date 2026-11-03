import { describe, expect, it } from "vitest";

import { REPORT_STATUS_META } from "./status";

describe("REPORT_STATUS_META", () => {
  it("覆盖全部四种状态", () => {
    expect(Object.keys(REPORT_STATUS_META).sort()).toEqual(["done", "draft", "paused", "writing"]);
  });

  it("各状态有中文标签", () => {
    expect(REPORT_STATUS_META.draft.label).toBe("待确认大纲");
    expect(REPORT_STATUS_META.writing.label).toBe("写作中");
    expect(REPORT_STATUS_META.paused.label).toBe("已暂停");
    expect(REPORT_STATUS_META.done.label).toBe("已完成");
  });
});
