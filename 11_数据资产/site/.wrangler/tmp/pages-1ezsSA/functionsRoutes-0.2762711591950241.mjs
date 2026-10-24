import { onRequestGet as __api_audit_js_onRequestGet } from "F:\\2026\\24xs\\11_数据资产\\cf-pages\\functions\\api\\audit.js"

export const routes = [
    {
      routePath: "/api/audit",
      mountPath: "/api",
      method: "GET",
      middlewares: [],
      modules: [__api_audit_js_onRequestGet],
    },
  ]