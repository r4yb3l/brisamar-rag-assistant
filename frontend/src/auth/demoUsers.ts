import type { BusinessLine } from "../api/types";

export interface DemoUser {
  token: string;
  name: string;
  lines: BusinessLine[];
}

export const BUSINESS_LINE_LABELS: Record<BusinessLine, string> = {
  autos: "Autos",
  hogar: "Hogar",
  vida: "Vida",
};

export const DEMO_USERS: DemoUser[] = [
  { token: "analyst-autos", name: "Analista Autos", lines: ["autos"] },
  { token: "analyst-hogar", name: "Analista Hogar", lines: ["hogar"] },
  { token: "analyst-all", name: "Analista multilínea", lines: ["autos", "hogar", "vida"] },
];

export const DEFAULT_DEMO_USER: DemoUser = DEMO_USERS[0] as DemoUser;

export function findDemoUser(token: string | null): DemoUser {
  return DEMO_USERS.find((user) => user.token === token) ?? DEFAULT_DEMO_USER;
}
