/** Flask LDW backend — Next.js dev server runs on a different port. */
export const LDW_API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_LDW_API) ||
  "http://127.0.0.1:5000"

export function ldwApi(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`
  return `${LDW_API_BASE}${normalized}`
}
