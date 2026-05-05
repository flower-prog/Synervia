/**
 * Application constants.
 */

export const APP_NAME = "{{ cookiecutter.project_name }}";
export const APP_DESCRIPTION = "{{ cookiecutter.project_description }}";

// API Routes (Next.js internal routes)
export const API_ROUTES = {
  // Auth
  LOGIN: "/auth/login",
  REGISTER: "/auth/register",
  LOGOUT: "/auth/logout",
  REFRESH: "/auth/refresh",
  ME: "/auth/me",

  // Health
  HEALTH: "/health",

  // Users
  USERS: "/users",

  // Chat (AI Agent)
  CHAT: "/chat",
} as const;

// Navigation routes
export const ROUTES = {
  HOME: "/",
  LOGIN: "/login",
  REGISTER: "/register",
  DASHBOARD: "/dashboard",
  CHAT: "/chat",
  PROFILE: "/profile",
  SETTINGS: "/settings",
{%- if cookiecutter.enable_rag %}
  RAG: "/rag",
{%- endif %}
{%- if cookiecutter.use_jwt %}
  ADMIN_RATINGS: "/admin/ratings",
  ADMIN_CONVERSATIONS: "/admin/conversations",
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
  ORGS: "/orgs",
  ORG_MEMBERS: (id: string) => `/orgs/${id}/members`,
  ORG_SETTINGS: (id: string) => `/orgs/${id}/settings`,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
  KB: "/kb",
  KB_DETAIL: (id: string) => `/kb/${id}`,
{%- endif %}
{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
  BILLING: "/billing",
{%- endif %}
} as const;

// WebSocket URL (for chat - direct to backend, use wss:// in production)
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:{{ cookiecutter.backend_port }}";

// Backend API URL (public, for direct links like API docs)
export const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:{{ cookiecutter.backend_port }}";
