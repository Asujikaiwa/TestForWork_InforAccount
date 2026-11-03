/**
 * The brief has no "list users" endpoint and authentication is out of scope,
 * so the user picker offers the seeded users. The backend still validates the
 * X-User header; this list only drives the dropdown.
 */
export const KNOWN_USERS = ["alice", "bob", "carol", "dan"] as const;

/**
 * Browser requests go to the Next.js server under /api, which rewrites them to
 * the FastAPI backend (see next.config.ts). Same origin = no CORS setup.
 */
export const API_BASE = "/api";
