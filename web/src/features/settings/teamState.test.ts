import type { AuthUser, TeamMember } from "../../lib/types";
import {
  assignableTeamRoles,
  canChangeTeamMember,
  canManageTeam,
  canRevokeTeamMember,
  teamCopy,
} from "./teamState";

const actor = (role: AuthUser["role"]): AuthUser => ({
  user_id: "actor",
  email: "actor@example.com",
  full_name: "Actor",
  store_id: "store",
  organization_id: "org",
  role,
  email_verified: true,
  mfa_enabled: false,
});

const member = (role: TeamMember["role"], user_id = "member"): TeamMember => ({
  membership_id: 1,
  user_id,
  email: `${user_id}@example.com`,
  full_name: "Member",
  role,
  created_at: "2026-09-11T00:00:00Z",
});

describe("team permissions", () => {
  it("keeps management limited to admins and owners", () => {
    expect(canManageTeam("analyst")).toBe(false);
    expect(canManageTeam("agent")).toBe(false);
    expect(canManageTeam("marketer")).toBe(false);
    expect(canManageTeam("admin")).toBe(true);
    expect(canManageTeam("owner")).toBe(true);
  });

  it("does not expose owner assignment or owner mutation to admins", () => {
    expect(assignableTeamRoles("admin")).not.toContain("owner");
    expect(assignableTeamRoles("owner")).toContain("owner");
    expect(canChangeTeamMember(actor("admin"), member("owner"))).toBe(false);
    expect(canChangeTeamMember(actor("owner"), member("owner"))).toBe(true);
  });

  it("prevents self-revocation while allowing authorized member removal", () => {
    expect(canRevokeTeamMember(actor("owner"), member("admin", "actor"))).toBe(
      false,
    );
    expect(canRevokeTeamMember(actor("owner"), member("admin"))).toBe(true);
    expect(canRevokeTeamMember(actor("agent"), member("agent"))).toBe(false);
  });
});

describe("team copy", () => {
  it("provides complete localized operational labels", () => {
    expect(teamCopy("en").createInvite).toBe("Create invitation");
    expect(teamCopy("en").roleLabels.owner).toBe("Owner");
    expect(teamCopy("ar").createInvite).toBe("إنشاء الدعوة");
    expect(teamCopy("ar").roleLabels.owner).toBe("مالك");
  });
});
