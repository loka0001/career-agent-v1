import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router";
import {
  IconCheck,
  IconCopy,
  IconKey,
  IconRefresh,
  IconSettings,
  IconShield,
  IconSpark,
  IconUsers,
} from "../../components/icons";
import {
  errorText,
  MotionPage,
  PageHeading,
  ProgressBar,
} from "../../components/operations";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Spinner,
} from "../../components/ui";
import { useAuth } from "../../app/AuthContext";
import { useLanguage } from "../../i18n";
import { api } from "../../lib/api";
import { formatDateTime } from "../../lib/format";
import { profileCopy } from "../profileCopy";
import type {
  ApiKeySummary,
  AuthSession,
  MemberRole,
  OnboardingStatus,
  StoreSettings,
  TeamMember,
} from "../../lib/types";
import { editableStoreSettings, storeSettingsChanged } from "./settingsState";
import {
  assignableTeamRoles,
  canChangeTeamMember,
  canManageTeam,
  canRevokeTeamMember,
  teamCopy,
} from "./teamState";

function useStoreSettings() {
  const [settings, setSettings] = useState<StoreSettings | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api
      .storeSettings()
      .then(setSettings)
      .catch((reason) => setError(errorText(reason)))
      .finally(() => setLoading(false));
  }, []);
  return { settings, setSettings, error, setError, loading };
}

export function StoreSettingsPage() {
  const { language } = useLanguage();
  const copy = profileCopy(language).store;
  const { settings, setSettings, error, setError, loading } =
    useStoreSettings();
  const [savedSettings, setSavedSettings] = useState<StoreSettings | null>(
    null,
  );
  const [notice, setNotice] = useState("");
  const [working, setWorking] = useState(false);
  const dirty = storeSettingsChanged(settings, savedSettings);

  useEffect(() => {
    if (settings && !savedSettings) setSavedSettings(settings);
  }, [savedSettings, settings]);

  useEffect(() => {
    function warnBeforeUnload(event: BeforeUnloadEvent) {
      if (!dirty) return;
      event.preventDefault();
    }
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [dirty]);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!settings) return;
    setWorking(true);
    setError("");
    setNotice("");
    try {
      const saved = await api.saveStoreSettings(
        editableStoreSettings(settings),
      );
      setSettings(saved);
      setSavedSettings(saved);
      setNotice(copy.saved);
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking(false);
    }
  }

  function discard() {
    if (!savedSettings) return;
    setSettings({
      ...savedSettings,
      brand_colors: { ...savedSettings.brand_colors },
    });
    setError("");
    setNotice("");
  }

  return (
    <MotionPage>
      <PageHeading
        title={language === "ar" ? "إعدادات المتجر" : "Store settings"}
        description={
          language === "ar"
            ? "الهوية، نوع النشاط، اللغة وسياسات الشحن والاسترجاع."
            : "Identity, business type, language, shipping, and return policies."
        }
        action={
          <div className="settings-heading-actions">
            <Badge tone={dirty ? "warning" : "success"}>
              {dirty
                ? language === "ar"
                  ? "تغييرات غير محفوظة"
                  : "Unsaved changes"
                : language === "ar"
                  ? "كل التغييرات محفوظة"
                  : "All changes saved"}
            </Badge>
            <Button
              type="button"
              variant="secondary"
              disabled={!dirty || working}
              onClick={discard}
            >
              {language === "ar" ? "تجاهل التغييرات" : "Discard changes"}
            </Button>
            <Button
              type="submit"
              form="store-settings-form"
              disabled={!dirty || working || loading}
            >
              <IconSettings size={17} /> {copy.save}
            </Button>
          </div>
        }
      />
      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {loading || !settings ? (
        <Spinner
          label={
            language === "ar" ? "جارٍ تحميل الإعدادات…" : "Loading settings…"
          }
        />
      ) : (
        <form
          id="store-settings-form"
          onSubmit={save}
          className="store-settings-workspace"
        >
          <Card className="settings-section-card">
            <div className="panel-head">
              <div>
                <h2>{language === "ar" ? "ملف المتجر" : "Store profile"}</h2>
                <p>
                  {language === "ar"
                    ? "المعلومات الافتراضية التي تستخدمها مساحة العمل."
                    : "Defaults used across the merchant workspace."}
                </p>
              </div>
            </div>
            <div className="form-grid">
              <label>
                {copy.storeName}
                <input
                  value={settings.store_name}
                  onChange={(event) =>
                    setSettings({ ...settings, store_name: event.target.value })
                  }
                />
              </label>
              <label>
                {copy.businessType}
                <select
                  value={settings.business_type}
                  onChange={(event) =>
                    setSettings({
                      ...settings,
                      business_type: event.target.value,
                    })
                  }
                >
                  <option value="retail">{copy.businessTypes.retail}</option>
                  <option value="fashion">{copy.businessTypes.fashion}</option>
                  <option value="beauty">{copy.businessTypes.beauty}</option>
                  <option value="electronics">
                    {copy.businessTypes.electronics}
                  </option>
                  <option value="food">{copy.businessTypes.food}</option>
                  <option value="services">
                    {copy.businessTypes.services}
                  </option>
                </select>
              </label>
              <label>
                {copy.defaultLanguage}
                <select
                  value={settings.default_language}
                  onChange={(event) =>
                    setSettings({
                      ...settings,
                      default_language: event.target.value as "ar" | "en",
                    })
                  }
                >
                  <option value="ar">العربية</option>
                  <option value="en">English</option>
                </select>
              </label>
              <label>
                {copy.aiBudget}
                <input
                  type="number"
                  min="0"
                  max="1000000"
                  step="0.01"
                  value={settings.ai_monthly_budget}
                  onChange={(event) =>
                    setSettings({
                      ...settings,
                      ai_monthly_budget: event.target.value,
                    })
                  }
                />
              </label>
            </div>
          </Card>

          <Card className="settings-section-card">
            <div className="panel-head">
              <div>
                <h2>{language === "ar" ? "هوية العلامة" : "Brand identity"}</h2>
                <p>
                  {language === "ar"
                    ? "الشعار والألوان المستخدمة في تجارب المتجر."
                    : "Logo and colors used in merchant experiences."}
                </p>
              </div>
            </div>
            <div className="form-grid">
              <label className="full">
                {copy.logoUrl}
                <input
                  type="url"
                  value={settings.logo_url ?? ""}
                  onChange={(event) =>
                    setSettings({
                      ...settings,
                      logo_url: event.target.value || null,
                    })
                  }
                />
              </label>
              <label className="color-field">
                {copy.primaryColor}
                <input
                  type="color"
                  value={settings.brand_colors.primary ?? "#2563eb"}
                  onChange={(event) =>
                    setSettings({
                      ...settings,
                      brand_colors: {
                        ...settings.brand_colors,
                        primary: event.target.value,
                      },
                    })
                  }
                />
              </label>
              <label className="color-field">
                {copy.accentColor}
                <input
                  type="color"
                  value={settings.brand_colors.accent ?? "#14b8a6"}
                  onChange={(event) =>
                    setSettings({
                      ...settings,
                      brand_colors: {
                        ...settings.brand_colors,
                        accent: event.target.value,
                      },
                    })
                  }
                />
              </label>
            </div>
          </Card>

          <Card className="settings-section-card settings-section-card--wide">
            <div className="panel-head">
              <div>
                <h2>
                  {language === "ar" ? "سياسات المتجر" : "Store policies"}
                </h2>
                <p>
                  {language === "ar"
                    ? "مصدر موثوق لردود الشحن والاسترجاع."
                    : "Authoritative answers for shipping and returns."}
                </p>
              </div>
            </div>
            <div className="form-grid">
              <label>
                {copy.shippingPolicy}
                <textarea
                  value={settings.shipping_policy}
                  onChange={(event) =>
                    setSettings({
                      ...settings,
                      shipping_policy: event.target.value,
                    })
                  }
                />
              </label>
              <label>
                {copy.returnPolicy}
                <textarea
                  value={settings.return_policy}
                  onChange={(event) =>
                    setSettings({
                      ...settings,
                      return_policy: event.target.value,
                    })
                  }
                />
              </label>
            </div>
          </Card>
        </form>
      )}
    </MotionPage>
  );
}

export function AgentSettingsPage() {
  const { language } = useLanguage();
  const copy = profileCopy(language).agent;
  const { settings, setSettings, error, setError, loading } =
    useStoreSettings();
  const [savedSettings, setSavedSettings] = useState<StoreSettings | null>(
    null,
  );
  const [testMessage, setTestMessage] = useState<string>(
    copy.defaultTestMessage,
  );
  const [reply, setReply] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const dirty = storeSettingsChanged(settings, savedSettings);

  useEffect(() => {
    if (settings && !savedSettings) setSavedSettings(settings);
  }, [savedSettings, settings]);

  useEffect(() => {
    function warnBeforeUnload(event: BeforeUnloadEvent) {
      if (!dirty) return;
      event.preventDefault();
    }
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [dirty]);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!settings) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const saved = await api.saveStoreSettings(
        editableStoreSettings(settings),
      );
      setSettings(saved);
      setSavedSettings(saved);
      setNotice(copy.saved);
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setSaving(false);
    }
  }

  function discard() {
    if (!savedSettings) return;
    setSettings({
      ...savedSettings,
      brand_colors: { ...savedSettings.brand_colors },
    });
    setError("");
    setNotice("");
  }

  async function testAgent() {
    setTesting(true);
    setError("");
    setReply("");
    try {
      const result = await api.sales(testMessage);
      setReply(result.reply);
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setTesting(false);
    }
  }

  return (
    <MotionPage>
      <PageHeading
        title={copy.title}
        description={copy.description}
        action={
          <div className="settings-heading-actions">
            <Badge tone={dirty ? "warning" : "success"}>
              {dirty ? copy.unsavedStatus : copy.savedStatus}
            </Badge>
            <Button
              type="button"
              variant="secondary"
              disabled={!dirty || saving}
              onClick={discard}
            >
              {copy.discard}
            </Button>
            <Button
              type="submit"
              form="agent-settings-form"
              disabled={!dirty || saving || loading}
            >
              <IconSettings size={17} /> {copy.save}
            </Button>
          </div>
        }
      />
      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {loading || !settings ? (
        <Spinner label={copy.loading} />
      ) : (
        <div className="operations-grid">
          <Card className="settings-section-card">
            <div className="panel-head">
              <div>
                <h2>{copy.personaTitle}</h2>
                <p>{copy.personaDescription}</p>
              </div>
            </div>
            <form id="agent-settings-form" onSubmit={save}>
              <label>
                {copy.assistantName}
                <input
                  value={settings.assistant_name}
                  onChange={(event) =>
                    setSettings({
                      ...settings,
                      assistant_name: event.target.value,
                    })
                  }
                />
              </label>
              <label>
                {copy.tone}
                <select
                  value={settings.tone}
                  onChange={(event) =>
                    setSettings({ ...settings, tone: event.target.value })
                  }
                >
                  <option value="friendly">{copy.tones.friendly}</option>
                  <option value="professional">
                    {copy.tones.professional}
                  </option>
                  <option value="concise">{copy.tones.concise}</option>
                  <option value="luxury">{copy.tones.luxury}</option>
                </select>
              </label>
              <label>
                {copy.instructions}
                <textarea
                  value={settings.assistant_instructions}
                  onChange={(event) =>
                    setSettings({
                      ...settings,
                      assistant_instructions: event.target.value,
                    })
                  }
                  placeholder={copy.instructionsPlaceholder}
                />
              </label>
            </form>
          </Card>
          <Card className="agent-test settings-section-card">
            <div className="panel-head">
              <div>
                <h2>
                  <IconSpark size={18} /> {copy.testTitle}
                </h2>
                <p>{copy.testDescription}</p>
              </div>
              <Badge>{copy.realCatalogData}</Badge>
            </div>
            <label>
              <span className="sr-only">{copy.testMessage}</span>
              <textarea
                value={testMessage}
                onChange={(event) => setTestMessage(event.target.value)}
              />
            </label>
            <Button
              onClick={testAgent}
              disabled={testing || !testMessage.trim()}
            >
              {testing ? copy.runningTest : copy.runTest}
            </Button>
            {reply && (
              <div className="assistant-reply">
                <span className="avatar">
                  <IconSpark size={16} />
                </span>
                <p>{reply}</p>
              </div>
            )}
          </Card>
        </div>
      )}
    </MotionPage>
  );
}

export function TeamPage() {
  const { language } = useLanguage();
  const { user } = useAuth();
  const copy = teamCopy(language);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    role: "agent" as MemberRole,
  });
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState<number | "invite" | null>(null);
  const canManage = canManageTeam(user?.role);
  const roleOptions = assignableTeamRoles(user?.role);

  async function load(showLoading = false) {
    if (showLoading) setLoading(true);
    setError("");
    try {
      setMembers(await api.team());
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      if (showLoading) setLoading(false);
    }
  }
  useEffect(() => {
    void load(true);
  }, []);

  async function invite(event: FormEvent) {
    event.preventDefault();
    setWorking("invite");
    setError("");
    setNotice("");
    try {
      const result = await api.inviteMember(form);
      setNotice(copy.inviteSent(result.email));
      setForm({ email: "", full_name: "", role: "agent" });
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking(null);
    }
  }

  async function updateRole(member: TeamMember, role: MemberRole) {
    if (role === member.role || !canChangeTeamMember(user, member)) return;
    setWorking(member.membership_id);
    setError("");
    setNotice("");
    try {
      const updated = await api.updateMemberRole(member.membership_id, role);
      setMembers((current) =>
        current.map((item) =>
          item.membership_id === updated.membership_id ? updated : item,
        ),
      );
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking(null);
    }
  }

  async function revoke(member: TeamMember) {
    if (!canRevokeTeamMember(user, member)) return;
    if (!window.confirm(copy.revokeConfirm(member.email))) return;
    setWorking(member.membership_id);
    setError("");
    setNotice("");
    try {
      await api.revokeMember(member.membership_id);
      setMembers((current) =>
        current.filter((item) => item.membership_id !== member.membership_id),
      );
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking(null);
    }
  }

  return (
    <MotionPage>
      <PageHeading title={copy.title} description={copy.description} />
      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {loading ? <Spinner label={copy.loading} /> : null}
      {!loading && error && members.length === 0 ? (
        <EmptyState
          title={copy.emptyTitle}
          body={copy.emptyBody}
          action={
            <Button variant="secondary" onClick={() => void load(true)}>
              <IconRefresh size={16} /> {copy.retry}
            </Button>
          }
        />
      ) : null}
      {!loading && !error ? (
        <div className="operations-grid management-grid team-workspace">
          <Card className="team-panel settings-section-card">
            <div className="panel-head">
              <div>
                <h2>
                  <IconUsers size={18} /> {copy.membersTitle}
                </h2>
                <p>{copy.membersDescription}</p>
              </div>
              <Badge>{copy.memberCount(members.length)}</Badge>
            </div>
            {members.length === 0 ? (
              <EmptyState title={copy.emptyTitle} body={copy.emptyBody} />
            ) : (
              <div className="team-list">
                {members.map((member) => {
                  const editable = canChangeTeamMember(user, member);
                  const revocable = canRevokeTeamMember(user, member);
                  return (
                    <div className="team-row" key={member.membership_id}>
                      <span className="avatar">
                        {(member.full_name || member.email).slice(0, 1)}
                      </span>
                      <span className="grow">
                        <b>
                          {member.full_name || copy.noName}{" "}
                          {member.user_id === user?.user_id ? (
                            <Badge tone="success">{copy.currentUser}</Badge>
                          ) : null}
                        </b>
                        <small>{member.email}</small>
                        <small>
                          {copy.joined}:{" "}
                          {formatDateTime(member.created_at, language)}
                        </small>
                      </span>
                      <div className="team-row__actions">
                        {editable ? (
                          <select
                            aria-label={copy.roleFor(member.email)}
                            value={member.role}
                            disabled={working !== null}
                            onChange={(event) =>
                              void updateRole(
                                member,
                                event.target.value as MemberRole,
                              )
                            }
                          >
                            {roleOptions.map((role) => (
                              <option key={role} value={role}>
                                {copy.roleLabels[role]}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <Badge
                            tone={
                              member.role === "owner" ? "warning" : "neutral"
                            }
                          >
                            {member.role === "owner"
                              ? copy.ownerProtected
                              : copy.roleLabels[member.role]}
                          </Badge>
                        )}
                        {revocable ? (
                          <Button
                            variant="ghost"
                            disabled={working !== null}
                            onClick={() => revoke(member)}
                          >
                            {copy.revoke}
                          </Button>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
          {canManage ? (
            <Card className="team-invite-card settings-section-card">
              <div className="panel-head">
                <div>
                  <h2>{copy.inviteTitle}</h2>
                  <p>{copy.inviteDescription}</p>
                </div>
              </div>
              <form onSubmit={invite}>
                <label>
                  {copy.name}
                  <input
                    value={form.full_name}
                    onChange={(event) =>
                      setForm({ ...form, full_name: event.target.value })
                    }
                  />
                </label>
                <label>
                  {copy.email}
                  <input
                    type="email"
                    required
                    value={form.email}
                    onChange={(event) =>
                      setForm({ ...form, email: event.target.value })
                    }
                  />
                </label>
                <label>
                  {copy.role}
                  <select
                    value={form.role}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        role: event.target.value as MemberRole,
                      })
                    }
                  >
                    {roleOptions.map((role) => (
                      <option key={role} value={role}>
                        {copy.roleLabels[role]}
                      </option>
                    ))}
                  </select>
                </label>
                <Button
                  type="submit"
                  disabled={working !== null || !form.email.trim()}
                >
                  {working === "invite"
                    ? copy.creatingInvite
                    : copy.createInvite}
                </Button>
              </form>
            </Card>
          ) : (
            <Card className="settings-section-card">
              <div className="panel-head">
                <div>
                  <h2>
                    <IconShield size={18} /> {copy.readOnlyTitle}
                  </h2>
                  <p>{copy.readOnlyBody}</p>
                </div>
              </div>
            </Card>
          )}
        </div>
      ) : null}
    </MotionPage>
  );
}

export function SecurityPage() {
  const { language } = useLanguage();
  const { user, refresh } = useAuth();
  const [sessions, setSessions] = useState<AuthSession[]>([]);
  const [setupSecret, setSetupSecret] = useState("");
  const [otp, setOtp] = useState("");
  const [passwords, setPasswords] = useState({ current: "", next: "" });
  const [disablePassword, setDisablePassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [working, setWorking] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const securityCopy =
    language === "ar"
      ? {
          title: "أمان الحساب",
          description:
            "تحكم في كلمة المرور والتحقق بخطوتين والجلسات المفتوحة من مكان واحد.",
          mfa: "التحقق بخطوتين",
          mfaBody: "أضف طبقة حماية إضافية باستخدام تطبيق المصادقة.",
          enabled: "مفعّل",
          disabled: "غير مفعّل",
          start: "بدء الإعداد",
          manualSecret: "مفتاح الإعداد اليدوي",
          appCode: "رمز تطبيق المصادقة",
          confirm: "تأكيد التفعيل",
          password: "كلمة المرور",
          disable: "إلغاء التحقق بخطوتين",
          passwordTitle: "تغيير كلمة المرور",
          passwordBody: "يؤدي التغيير إلى إنهاء كل الجلسات لحماية الحساب.",
          currentPassword: "كلمة المرور الحالية",
          newPassword: "كلمة المرور الجديدة",
          changePassword: "تغيير كلمة المرور",
          sessions: "الجلسات النشطة",
          sessionsBody:
            "راجع الأجهزة التي وصلت إلى حسابك وألغِ أي جلسة غير معروفة.",
          refresh: "تحديث الجلسات",
          loading: "جارٍ تحميل الجلسات…",
          empty: "لا توجد جلسات نشطة.",
          current: "هذه الجلسة",
          other: "جلسة أخرى",
          currentBadge: "الحالية",
          lastSeen: "آخر نشاط",
          expires: "تنتهي",
          revoke: "إلغاء الجلسة",
          unknownBrowser: "متصفح غير معروف",
          setupNotice:
            "أضف المفتاح إلى تطبيق المصادقة، ثم أدخل الرمز الحالي للتأكيد.",
          enabledNotice: "تم تفعيل التحقق بخطوتين.",
        }
      : {
          title: "Account security",
          description:
            "Manage your password, two-factor authentication, and active sessions in one place.",
          mfa: "Two-factor authentication",
          mfaBody: "Add another layer of protection with an authenticator app.",
          enabled: "Enabled",
          disabled: "Not enabled",
          start: "Start setup",
          manualSecret: "Manual setup key",
          appCode: "Authenticator code",
          confirm: "Confirm activation",
          password: "Password",
          disable: "Disable two-factor authentication",
          passwordTitle: "Change password",
          passwordBody:
            "Changing your password signs out every session to protect the account.",
          currentPassword: "Current password",
          newPassword: "New password",
          changePassword: "Change password",
          sessions: "Active sessions",
          sessionsBody:
            "Review devices with account access and revoke anything you do not recognize.",
          refresh: "Refresh sessions",
          loading: "Loading sessions…",
          empty: "No active sessions.",
          current: "This session",
          other: "Another session",
          currentBadge: "Current",
          lastSeen: "Last seen",
          expires: "Expires",
          revoke: "Revoke session",
          unknownBrowser: "Unknown browser",
          setupNotice:
            "Add this key to your authenticator app, then enter the current code to confirm.",
          enabledNotice: "Two-factor authentication is now enabled.",
        };

  async function loadSessions() {
    setLoadingSessions(true);
    try {
      setSessions(await api.sessions());
      setError("");
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setLoadingSessions(false);
    }
  }
  useEffect(() => {
    void loadSessions();
  }, []);

  async function revokeSession(session: AuthSession) {
    setWorking(true);
    try {
      await api.revokeSession(session.session_id);
      if (session.current) {
        window.location.assign("/login");
        return;
      }
      await loadSessions();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorking(false);
    }
  }

  async function changePassword(event: FormEvent) {
    event.preventDefault();
    setWorking(true);
    try {
      await api.changePassword(passwords.current, passwords.next);
      window.location.assign("/login");
    } catch (reason) {
      setError(errorText(reason));
      setWorking(false);
    }
  }

  async function beginMfa() {
    setWorking(true);
    try {
      const result = await api.setupMfa();
      setSetupSecret(result.secret);
      setNotice(securityCopy.setupNotice);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorking(false);
    }
  }

  async function confirmMfa() {
    setWorking(true);
    try {
      await api.confirmMfa(otp);
      setSetupSecret("");
      setOtp("");
      setNotice(securityCopy.enabledNotice);
      await refresh();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorking(false);
    }
  }

  async function disableMfa() {
    setWorking(true);
    try {
      await api.disableMfa(disablePassword, otp);
      window.location.assign("/login");
    } catch (reason) {
      setError(errorText(reason));
      setWorking(false);
    }
  }

  return (
    <MotionPage>
      <PageHeading
        title={securityCopy.title}
        description={securityCopy.description}
      />
      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      <div className="operations-grid management-grid">
        <Card className="settings-section-card security-tool-card">
          <div className="panel-head">
            <div>
              <h2>
                <IconShield size={18} /> {securityCopy.mfa}
              </h2>
              <p>{securityCopy.mfaBody}</p>
            </div>
            <Badge tone={user?.mfa_enabled ? "success" : "neutral"}>
              {user?.mfa_enabled ? securityCopy.enabled : securityCopy.disabled}
            </Badge>
          </div>
          {!user?.mfa_enabled && !setupSecret && (
            <Button onClick={beginMfa} disabled={working}>
              {securityCopy.start}
            </Button>
          )}
          {setupSecret && (
            <>
              <label>
                {securityCopy.manualSecret}
                <input
                  className="secret-key"
                  dir="ltr"
                  readOnly
                  value={setupSecret}
                />
              </label>
              <label>
                {securityCopy.appCode}
                <input
                  className="otp-input"
                  inputMode="numeric"
                  value={otp}
                  onChange={(event) =>
                    setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))
                  }
                />
              </label>
              <Button
                onClick={confirmMfa}
                disabled={working || otp.length !== 6}
              >
                {securityCopy.confirm}
              </Button>
            </>
          )}
          {user?.mfa_enabled && (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void disableMfa();
              }}
            >
              <label>
                {securityCopy.password}
                <input
                  type="password"
                  value={disablePassword}
                  onChange={(event) => setDisablePassword(event.target.value)}
                  required
                />
              </label>
              <label>
                {securityCopy.appCode}
                <input
                  className="otp-input"
                  inputMode="numeric"
                  value={otp}
                  onChange={(event) =>
                    setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))
                  }
                  required
                />
              </label>
              <Button
                variant="danger"
                type="submit"
                disabled={working || otp.length !== 6}
              >
                {securityCopy.disable}
              </Button>
            </form>
          )}
        </Card>
        <Card className="settings-section-card security-tool-card">
          <div className="panel-head">
            <div>
              <h2>
                <IconKey size={18} /> {securityCopy.passwordTitle}
              </h2>
              <p>{securityCopy.passwordBody}</p>
            </div>
          </div>
          <form onSubmit={changePassword}>
            <label>
              {securityCopy.currentPassword}
              <input
                type="password"
                autoComplete="current-password"
                value={passwords.current}
                onChange={(event) =>
                  setPasswords({ ...passwords, current: event.target.value })
                }
                required
              />
            </label>
            <label>
              {securityCopy.newPassword}
              <input
                type="password"
                autoComplete="new-password"
                minLength={10}
                value={passwords.next}
                onChange={(event) =>
                  setPasswords({ ...passwords, next: event.target.value })
                }
                required
              />
            </label>
            <Button type="submit" disabled={working}>
              {securityCopy.changePassword}
            </Button>
          </form>
        </Card>
      </div>
      <Card className="settings-section-card sessions-card">
        <div className="panel-head">
          <div>
            <h2>{securityCopy.sessions}</h2>
            <p>{securityCopy.sessionsBody}</p>
          </div>
          <Button
            variant="ghost"
            onClick={() => void loadSessions()}
            title={securityCopy.refresh}
            aria-label={securityCopy.refresh}
            disabled={loadingSessions || working}
          >
            <IconRefresh size={17} />
          </Button>
        </div>
        {loadingSessions ? <Spinner label={securityCopy.loading} /> : null}
        {!loadingSessions && sessions.length === 0 ? (
          <EmptyState
            title={securityCopy.empty}
            body={securityCopy.sessionsBody}
          />
        ) : null}
        {!loadingSessions && sessions.length > 0 ? (
          <div className="key-list session-list">
            {sessions.map((session) => (
              <div className="key-row" key={session.session_id}>
                <span className="grow">
                  <b>
                    {session.current
                      ? securityCopy.current
                      : securityCopy.other}
                  </b>
                  <small dir="ltr">
                    {session.ip_address} ·{" "}
                    {session.user_agent || securityCopy.unknownBrowser}
                  </small>
                  <small>
                    {securityCopy.lastSeen}:{" "}
                    {formatDateTime(session.last_seen_at, language)} ·{" "}
                    {securityCopy.expires}:{" "}
                    {formatDateTime(session.expires_at, language)}
                  </small>
                </span>
                {session.current && (
                  <Badge tone="success">{securityCopy.currentBadge}</Badge>
                )}
                <Button
                  variant="ghost"
                  disabled={working}
                  onClick={() => void revokeSession(session)}
                >
                  {securityCopy.revoke}
                </Button>
              </div>
            ))}
          </div>
        ) : null}
      </Card>
    </MotionPage>
  );
}

export function ApiKeysPage() {
  const { language } = useLanguage();
  const [keys, setKeys] = useState<ApiKeySummary[]>([]);
  const [name, setName] = useState("Website widget");
  const [origins, setOrigins] = useState("https://example.com");
  const [plaintext, setPlaintext] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const keyCopy =
    language === "ar"
      ? {
          title: "مفاتيح API والموقع",
          description:
            "اربط ويدجت المحادثة بالموقع وحدد النطاقات المسموح لها بدقة.",
          createTitle: "إنشاء مفتاح موقع",
          createBody:
            "أنشئ مفتاحًا مستقلًا لكل موقع حتى يسهل إلغاؤه أو استبداله.",
          name: "اسم المفتاح",
          origins: "النطاقات المسموح بها",
          create: "إنشاء المفتاح",
          creating: "جارٍ الإنشاء…",
          snippet: "كود تثبيت الويدجت",
          keys: "المفاتيح الحالية",
          keysBody:
            "المفاتيح مخزنة بشكل مشفر ولا يظهر السر الكامل بعد الإنشاء.",
          loading: "جارٍ تحميل المفاتيح…",
          empty: "لا توجد مفاتيح بعد",
          emptyBody: "أنشئ مفتاحًا لتوصيل ويدجت المحادثة بموقعك.",
          saveNow: "احفظ المفتاح الآن؛ لن يظهر مرة أخرى.",
          copy: "نسخ المفتاح",
          copied: "تم نسخ المفتاح.",
          active: "نشط",
          revoked: "ملغى",
          neverUsed: "لم يُستخدم بعد",
          lastUsed: "آخر استخدام",
          created: "أُنشئ",
          revoke: "إلغاء",
          revokedNotice: "تم إلغاء المفتاح.",
          noOrigin: "لا توجد نطاقات مسموحة",
        }
      : {
          title: "API keys & website",
          description:
            "Connect the chat widget to your website and tightly control allowed origins.",
          createTitle: "Create a website key",
          createBody:
            "Use a separate key for every site so it can be revoked or rotated independently.",
          name: "Key name",
          origins: "Allowed origins",
          create: "Create key",
          creating: "Creating…",
          snippet: "Widget install code",
          keys: "Current keys",
          keysBody:
            "Keys are stored hashed and the full secret is only shown once.",
          loading: "Loading keys…",
          empty: "No API keys yet",
          emptyBody: "Create a key to connect the chat widget to your website.",
          saveNow: "Save this key now; it will not be shown again.",
          copy: "Copy key",
          copied: "Key copied.",
          active: "Active",
          revoked: "Revoked",
          neverUsed: "Never used",
          lastUsed: "Last used",
          created: "Created",
          revoke: "Revoke",
          revokedNotice: "Key revoked.",
          noOrigin: "No origin allowed",
        };

  async function load() {
    setLoading(true);
    try {
      setKeys(await api.apiKeys());
      setError("");
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setWorking(true);
    setError("");
    setNotice("");
    try {
      const allowedOrigins = origins
        .split(/[\s,]+/)
        .map((item) => item.trim())
        .filter(Boolean);
      const result = await api.createApiKey(name, allowedOrigins);
      setPlaintext(result.key);
      await load();
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking(false);
    }
  }

  async function revoke(key: ApiKeySummary) {
    if (
      !window.confirm(
        language === "ar"
          ? `إلغاء المفتاح ${key.name}؟`
          : `Revoke key ${key.name}?`,
      )
    )
      return;
    try {
      setWorking(true);
      setNotice("");
      await api.revokeApiKey(key.id);
      await load();
      setNotice(keyCopy.revokedNotice);
    } catch (reason) {
      setError(errorText(reason, language));
    } finally {
      setWorking(false);
    }
  }

  return (
    <MotionPage>
      <PageHeading title={keyCopy.title} description={keyCopy.description} />
      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {plaintext && (
        <Alert tone="warning">
          <b>{keyCopy.saveNow}</b>
          <code className="secret-key">{plaintext}</code>
          <Button
            variant="ghost"
            onClick={() => {
              void navigator.clipboard.writeText(plaintext);
              setNotice(keyCopy.copied);
            }}
          >
            <IconCopy size={15} /> {keyCopy.copy}
          </Button>
        </Alert>
      )}
      <div className="operations-grid management-grid">
        <Card className="settings-section-card api-key-create-card">
          <div className="panel-head">
            <div>
              <h2>
                <IconKey size={18} /> {keyCopy.createTitle}
              </h2>
              <p>{keyCopy.createBody}</p>
            </div>
          </div>
          <form onSubmit={create}>
            <label>
              {keyCopy.name}
              <input
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <label>
              {keyCopy.origins}
              <textarea
                required
                dir="ltr"
                value={origins}
                onChange={(event) => setOrigins(event.target.value)}
                placeholder="https://store.example.com"
              />
            </label>
            <Button
              type="submit"
              disabled={working || !name.trim() || !origins.trim()}
            >
              {working ? keyCopy.creating : keyCopy.create}
            </Button>
          </form>
          <div className="widget-snippet">
            <span>{keyCopy.snippet}</span>
            <code>{`<script src="${window.location.origin}/widget.js" data-key="${plaintext || "YOUR_PUBLISHABLE_KEY"}" data-track="off"></script>`}</code>
          </div>
        </Card>
        <Card className="settings-section-card api-key-list-card">
          <div className="panel-head">
            <div>
              <h2>{keyCopy.keys}</h2>
              <p>{keyCopy.keysBody}</p>
            </div>
            <Badge>{keys.length}</Badge>
          </div>
          {loading ? <Spinner label={keyCopy.loading} /> : null}
          {!loading && keys.length === 0 ? (
            <EmptyState title={keyCopy.empty} body={keyCopy.emptyBody} />
          ) : null}
          {!loading && keys.length > 0 ? (
            <div className="key-list">
              {keys.map((key) => (
                <div className="key-row" key={key.id}>
                  <span className="grow">
                    <b>{key.name}</b>
                    <small>
                      {key.key_prefix}•••• · {key.scopes.join(", ")}
                    </small>
                    <small dir="ltr">
                      {key.allowed_origins.join(", ") || keyCopy.noOrigin}
                    </small>
                    <small>
                      {key.last_used_at
                        ? `${keyCopy.lastUsed}: ${formatDateTime(key.last_used_at, language)}`
                        : keyCopy.neverUsed}{" "}
                      · {keyCopy.created}:{" "}
                      {formatDateTime(key.created_at, language)}
                    </small>
                  </span>
                  <Badge tone={key.is_active ? "success" : "error"}>
                    {key.is_active ? keyCopy.active : keyCopy.revoked}
                  </Badge>
                  {key.is_active && (
                    <Button
                      variant="ghost"
                      disabled={working}
                      onClick={() => revoke(key)}
                    >
                      {keyCopy.revoke}
                    </Button>
                  )}
                </div>
              ))}
            </div>
          ) : null}
        </Card>
      </div>
    </MotionPage>
  );
}

export function OnboardingPage() {
  const { language } = useLanguage();
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);
  async function load() {
    setWorking(true);
    try {
      setStatus(await api.onboarding());
      setError("");
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorking(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  async function activate() {
    setWorking(true);
    try {
      setStatus(await api.activateStore());
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setWorking(false);
    }
  }

  return (
    <MotionPage>
      <PageHeading
        title={language === "ar" ? "جاهزية المتجر" : "Store readiness"}
        description={
          language === "ar"
            ? "كل خطوة تعتمد على دليل مسجل في النظام؛ لا توجد علامات إكمال يدوية."
            : "Every step uses recorded system evidence; there are no manual completion flags."
        }
      />
      {error && <Alert tone="error">{error}</Alert>}
      {!status ? (
        <Spinner
          label={language === "ar" ? "جارٍ فحص الأدلة…" : "Checking evidence…"}
        />
      ) : (
        <>
          <Card className="onboarding-progress">
            <div>
              <span>الجاهزية المثبتة</span>
              <b>
                {status.completed_count}/{status.required_count}
              </b>
            </div>
            <ProgressBar
              value={status.completed_count}
              max={status.required_count}
              label="Onboarding"
            />
          </Card>
          <div className="onboarding-list">
            {status.steps.map((step, index) => {
              return (
                <Card
                  className={`onboarding-step ${step.complete ? "done" : ""}`}
                  key={step.key}
                >
                  <span className="step-number">
                    {step.complete ? <IconCheck size={18} /> : index + 1}
                  </span>
                  <span className="grow">
                    <b>{step.title}</b>
                    <small>{step.evidence}</small>
                  </span>
                  <Badge tone={step.complete ? "success" : "warning"}>
                    {step.complete ? "مثبتة" : "ناقصة"}
                  </Badge>
                  <Link className="button button--secondary" to={step.href}>
                    فتح
                  </Link>
                </Card>
              );
            })}
          </div>
          <div className="actions onboarding-actions">
            <Button
              variant="secondary"
              disabled={working}
              onClick={() => void load()}
            >
              <IconRefresh size={17} /> إعادة الفحص
            </Button>
            <Button
              disabled={
                working || !status.ready_to_activate || status.activated
              }
              onClick={() => void activate()}
            >
              <IconCheck size={17} />{" "}
              {status.activated ? "المتجر مفعّل" : "تفعيل المتجر"}
            </Button>
          </div>
        </>
      )}
    </MotionPage>
  );
}
