import type { AuthUser, MemberRole, TeamMember } from "../../lib/types";

export const teamRoles: MemberRole[] = [
  "analyst",
  "agent",
  "marketer",
  "admin",
  "owner",
];

export function canManageTeam(role: MemberRole | undefined): boolean {
  return role === "admin" || role === "owner";
}

export function assignableTeamRoles(
  role: MemberRole | undefined,
): MemberRole[] {
  if (role === "owner") return teamRoles;
  if (role === "admin") return teamRoles.filter((item) => item !== "owner");
  return [];
}

export function canChangeTeamMember(
  actor: AuthUser | null,
  member: TeamMember,
): boolean {
  if (!actor || !canManageTeam(actor.role)) return false;
  return member.role !== "owner" || actor.role === "owner";
}

export function canRevokeTeamMember(
  actor: AuthUser | null,
  member: TeamMember,
): boolean {
  return (
    canChangeTeamMember(actor, member) && member.user_id !== actor?.user_id
  );
}

const copy = {
  ar: {
    title: "الفريق والصلاحيات",
    description:
      "أدوار متدرجة يعاد التحقق منها في كل طلب، مع حماية صلاحيات المالك.",
    membersTitle: "أعضاء الفريق",
    membersDescription: "الأعضاء النشطون داخل مساحة المتجر الحالية.",
    memberCount: (count: number) => `${count} عضو`,
    loading: "جارٍ تحميل أعضاء الفريق…",
    emptyTitle: "لا يوجد أعضاء بعد",
    emptyBody: "ستظهر عضويات مساحة العمل هنا بعد قبول الدعوات.",
    retry: "إعادة المحاولة",
    noName: "بدون اسم",
    currentUser: "أنت",
    joined: "انضم",
    ownerProtected: "مالك محمي",
    roleFor: (email: string) => `الدور الخاص بـ ${email}`,
    revoke: "إلغاء الوصول",
    revokeConfirm: (email: string) => `إلغاء وصول ${email}؟`,
    inviteTitle: "دعوة عضو",
    inviteDescription:
      "تُرسل دعوة آمنة تنتهي خلال 7 أيام، ولا تُنشأ كلمة مرور داخل اللوحة.",
    name: "الاسم",
    email: "البريد الإلكتروني",
    role: "الدور",
    createInvite: "إنشاء الدعوة",
    creatingInvite: "جارٍ إنشاء الدعوة…",
    inviteSent: (email: string) =>
      `أُرسلت دعوة آمنة إلى ${email} وتنتهي خلال 7 أيام.`,
    readOnlyTitle: "عرض فقط",
    readOnlyBody:
      "يمكنك مراجعة أعضاء الفريق. إدارة الدعوات والأدوار متاحة للمشرف والمالك فقط.",
    roleLabels: {
      analyst: "محلل",
      agent: "وكيل محادثات",
      marketer: "مسوّق",
      admin: "مشرف",
      owner: "مالك",
    },
  },
  en: {
    title: "Team & permissions",
    description:
      "Server-checked roles on every request, with protected owner privileges.",
    membersTitle: "Team members",
    membersDescription: "Active members in the current merchant workspace.",
    memberCount: (count: number) =>
      `${count} ${count === 1 ? "member" : "members"}`,
    loading: "Loading team members…",
    emptyTitle: "No members yet",
    emptyBody:
      "Workspace memberships will appear here after invitations are accepted.",
    retry: "Try again",
    noName: "No name",
    currentUser: "You",
    joined: "Joined",
    ownerProtected: "Protected owner",
    roleFor: (email: string) => `Role for ${email}`,
    revoke: "Revoke access",
    revokeConfirm: (email: string) => `Revoke access for ${email}?`,
    inviteTitle: "Invite a member",
    inviteDescription:
      "Send a secure invitation that expires in 7 days. No password is created in the dashboard.",
    name: "Name",
    email: "Email address",
    role: "Role",
    createInvite: "Create invitation",
    creatingInvite: "Creating invitation…",
    inviteSent: (email: string) =>
      `A secure invitation was sent to ${email} and expires in 7 days.`,
    readOnlyTitle: "Read-only access",
    readOnlyBody:
      "You can review the team. Invitations and role management require an admin or owner.",
    roleLabels: {
      analyst: "Analyst",
      agent: "Conversation agent",
      marketer: "Marketer",
      admin: "Admin",
      owner: "Owner",
    },
  },
} as const;

export function teamCopy(language: "ar" | "en") {
  return copy[language];
}
