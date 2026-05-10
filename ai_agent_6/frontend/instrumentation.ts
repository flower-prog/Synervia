import { registerOTel } from "@vercel/otel";

export function register() {
  registerOTel({
    serviceName: "ai_agent_6-frontend",
  });
}
