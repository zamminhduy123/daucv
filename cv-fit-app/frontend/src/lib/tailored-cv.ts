import type { TailoredCVVersion } from "@/types";

export function tailoredCVDisplayName(version: TailoredCVVersion) {
  const roleAndCompany = [version.target_role, version.company_name].filter(Boolean).join(" – ");
  return roleAndCompany || `CV ${new Date(version.created_at).toLocaleDateString("vi-VN")}`;
}
