import { describe, expect, it } from "vitest";

import { ApiError, extractApiError } from "./api";

describe("extractApiError", () => {
  it("解析统一错误结构", () => {
    expect(extractApiError({ error: { code: "NOT_FOUND", message: "报告不存在" } }, 404)).toEqual({
      code: "NOT_FOUND",
      message: "报告不存在",
    });
  });

  it("无 error 结构时回退到 HTTP 状态", () => {
    expect(extractApiError(null, 500)).toEqual({ code: "HTTP_500", message: "请求失败（500）" });
  });
});

describe("ApiError", () => {
  it("携带 code 和 message", () => {
    const e = new ApiError("X", "Y");
    expect(e.code).toBe("X");
    expect(e.message).toBe("Y");
  });
});
