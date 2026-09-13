import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { AccessStatus, DemoStatus } from "../components/domain/AccessStatus";
import {
  IconCaretDown,
  IconGlobe,
  IconLock,
  IconLogout,
  IconMoon,
  IconSearch,
  IconSettings,
  IconSidebar,
  IconSun,
  IconSystem,
  IconTarget,
  IconWifiOff,
  IconX,
} from "../components/icons";
import { Brand } from "../components/layout/Brand";
import { Button } from "../components/ui";
import { useLanguage } from "../i18n";
import { useAuth } from "./AuthContext";
import {
  navigationGroups,
  operatorItem,
  type NavigationItem,
} from "./navigation";
import { useTheme } from "./ThemeContext";

function NavigationLink({
  item,
  language,
  locked = false,
  collapsed = false,
  onNavigate,
}: {
  item: NavigationItem;
  language: "ar" | "en";
  locked?: boolean;
  collapsed?: boolean;
  onNavigate?: () => void;
}) {
  const Icon = item.icon;
  const label = language === "ar" ? item.ar : item.en;
  if (locked) {
    const message =
      language === "ar"
        ? `${label} متاح في خطة أعلى`
        : `${label} is available on a higher plan`;
    return (
      <span className="nav-link nav-link--locked" title={message}>
        <Icon size={20} />
        <span>{label}</span>
        <IconLock className="nav-lock" size={14} aria-label={message} />
      </span>
    );
  }
  return (
    <NavLink
      to={item.to}
      onClick={onNavigate}
      title={collapsed ? label : undefined}
    >
      <Icon size={20} />
      <span>{label}</span>
    </NavLink>
  );
}

function CommandPalette({
  open,
  language,
  items,
  onClose,
  onNavigate,
}: {
  open: boolean;
  language: "ar" | "en";
  items: NavigationItem[];
  onClose: () => void;
  onNavigate: (path: string) => void;
}) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const filtered = items.filter((item) =>
    `${item.ar} ${item.en}`.toLowerCase().includes(query.trim().toLowerCase()),
  );

  useEffect(() => {
    if (!open) return;
    setQuery("");
    window.requestAnimationFrame(() => inputRef.current?.focus());
  }, [open]);

  if (!open) return null;
  return (
    <div className="command-layer" role="presentation">
      <button
        className="command-scrim"
        type="button"
        onClick={onClose}
        aria-label={language === "ar" ? "إغلاق البحث" : "Close search"}
      />
      <section
        className="command-palette"
        role="dialog"
        aria-modal="true"
        aria-label={language === "ar" ? "البحث السريع" : "Command palette"}
      >
        <div className="command-input">
          <IconSearch size={20} />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={
              language === "ar"
                ? "ابحث في الصفحات والإجراءات…"
                : "Search pages and actions…"
            }
          />
          <kbd>Esc</kbd>
        </div>
        <div className="command-results" role="listbox">
          <small>{language === "ar" ? "الانتقال إلى" : "Navigate to"}</small>
          {filtered.length ? (
            filtered.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.to}
                  type="button"
                  onClick={() => onNavigate(item.to)}
                  role="option"
                  aria-selected="false"
                >
                  <Icon size={20} />
                  <span>{language === "ar" ? item.ar : item.en}</span>
                  <kbd>↵</kbd>
                </button>
              );
            })
          ) : (
            <p>{language === "ar" ? "لا توجد نتائج" : "No results found"}</p>
          )}
        </div>
      </section>
    </div>
  );
}

export function AppShell() {
  const { messages, language, toggle } = useLanguage();
  const { theme, resolvedTheme, toggleTheme } = useTheme();
  const { user, subscription, freeAccess, demoMode, isOperator, logout } =
    useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => window.localStorage.getItem("commerce-sidebar") === "collapsed",
  );
  const [commandOpen, setCommandOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [online, setOnline] = useState(() => navigator.onLine);
  const [backOnline, setBackOnline] = useState(false);
  const drawerRef = useRef<HTMLElement>(null);

  const visibleGroups = useMemo(
    () =>
      navigationGroups.map((group) => ({
        ...group,
        items: group.items.filter(
          (item) =>
            (!item.operator || isOperator) &&
            !(freeAccess && item.to === "/app/billing"),
        ),
      })),
    [freeAccess, isOperator],
  );
  const allItems = useMemo(
    () => [
      ...visibleGroups.flatMap((group) => group.items),
      ...(isOperator ? [operatorItem] : []),
    ],
    [isOperator, visibleGroups],
  );
  const routeItems = useMemo(
    () => [
      ...navigationGroups.flatMap((group) => group.items),
      ...(isOperator ? [operatorItem] : []),
    ],
    [isOperator],
  );
  const currentItem =
    routeItems.find((item) => location.pathname === item.to) ?? routeItems[0];
  const secondaryRouteActive = visibleGroups
    .slice(1)
    .some((group) => group.items.some((item) => location.pathname === item.to));
  const [secondaryNavOpen, setSecondaryNavOpen] =
    useState(secondaryRouteActive);

  useEffect(() => {
    setSecondaryNavOpen(secondaryRouteActive);
  }, [location.pathname, secondaryRouteActive]);
  const currentLabel = currentItem
    ? language === "ar"
      ? currentItem.ar
      : currentItem.en
    : messages.merchantWorkspace;

  const isLocked = (item: NavigationItem) =>
    Boolean(
      item.feature &&
      subscription &&
      !subscription.plan.features.includes(item.feature),
    );
  const closeMenu = () => setMobileMenuOpen(false);
  const closePopovers = () => {
    setProfileOpen(false);
  };
  const goTo = (path: string) => {
    setCommandOpen(false);
    closePopovers();
    navigate(path);
  };
  const signOut = async () => {
    await logout();
    navigate("/login");
  };
  const toggleSidebar = () => {
    setSidebarCollapsed((current) => {
      const next = !current;
      window.localStorage.setItem(
        "commerce-sidebar",
        next ? "collapsed" : "expanded",
      );
      return next;
    });
  };

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen(true);
      }
      if (event.key === "Escape") {
        setCommandOpen(false);
        closePopovers();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    const onOffline = () => {
      setBackOnline(false);
      setOnline(false);
    };
    const onOnline = () => {
      setOnline(true);
      setBackOnline(true);
      window.setTimeout(() => setBackOnline(false), 3000);
    };
    window.addEventListener("offline", onOffline);
    window.addEventListener("online", onOnline);
    return () => {
      window.removeEventListener("offline", onOffline);
      window.removeEventListener("online", onOnline);
    };
  }, []);

  useEffect(() => {
    if (!mobileMenuOpen) return;
    const drawer = drawerRef.current;
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    drawer?.querySelector<HTMLElement>("[data-drawer-close]")?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileMenuOpen(false);
        return;
      }
      if (event.key !== "Tab" || !drawer) return;
      const focusable = Array.from(
        drawer.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
      const first = focusable.at(0);
      const last = focusable.at(-1);
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, [mobileMenuOpen]);

  return (
    <div
      className={`app-shell ${sidebarCollapsed ? "app-shell--collapsed" : ""}`}
    >
      <aside
        className="sidebar"
        aria-label={language === "ar" ? "الشريط الجانبي" : "Sidebar"}
      >
        <button
          className="workspace-selector"
          type="button"
          title={
            language === "ar" ? "مساحة العمل الحالية" : "Current workspace"
          }
        >
          <Brand compact={sidebarCollapsed} />
          {!sidebarCollapsed ? (
            <span className="workspace-selector__meta">
              <small>{messages.merchantWorkspace}</small>
              <b>{user?.store_id || "Commerce"}</b>
            </span>
          ) : null}
          {!sidebarCollapsed ? <IconCaretDown size={15} /> : null}
        </button>
        {!sidebarCollapsed && freeAccess ? (
          <AccessStatus language={language} />
        ) : null}
        {!sidebarCollapsed && demoMode ? (
          <DemoStatus language={language} />
        ) : null}
        <nav
          aria-label={language === "ar" ? "التنقل الرئيسي" : "Main navigation"}
        >
          <section className="nav-group nav-group--primary">
            <span className="nav-group-label">
              {language === "ar" ? "مساحة العمل" : "Workspace"}
            </span>
            {(visibleGroups[0]?.items ?? []).map((item) => (
              <NavigationLink
                key={item.to}
                item={item}
                language={language}
                locked={isLocked(item)}
                collapsed={sidebarCollapsed}
              />
            ))}
          </section>
          <details
            className="nav-more"
            open={secondaryNavOpen}
            onToggle={(event) => setSecondaryNavOpen(event.currentTarget.open)}
          >
            <summary>
              <IconSettings size={20} />
              <span>{language === "ar" ? "أدوات إضافية" : "More tools"}</span>
              <span className="nav-more__caret" aria-hidden="true">
                <IconCaretDown size={15} />
              </span>
            </summary>
            <div className="nav-more__groups">
              {visibleGroups.slice(1).map((group) => (
                <section className="nav-group" key={group.en}>
                  <span className="nav-group-label">
                    {language === "ar" ? group.ar : group.en}
                  </span>
                  {group.items.map((item) => (
                    <NavigationLink
                      key={item.to}
                      item={item}
                      language={language}
                      locked={isLocked(item)}
                      collapsed={sidebarCollapsed}
                    />
                  ))}
                </section>
              ))}
              {isOperator ? (
                <section className="nav-group nav-group--operator">
                  <span className="nav-group-label">
                    {language === "ar" ? "تشغيل المنصة" : "Platform"}
                  </span>
                  <NavigationLink
                    item={operatorItem}
                    language={language}
                    collapsed={sidebarCollapsed}
                  />
                </section>
              ) : null}
            </div>
          </details>
        </nav>
        <div className="sidebar-footer">
          {!sidebarCollapsed ? (
            <NavLink className="setup-card" to="/app/onboarding">
              <span className="setup-card__icon">
                <IconTarget size={18} />
              </span>
              <span>
                <b>{language === "ar" ? "جاهزية المتجر" : "Store readiness"}</b>
                <small>
                  {language === "ar"
                    ? "راجع ما ينقصك للانطلاق"
                    : "Review remaining setup"}
                </small>
              </span>
            </NavLink>
          ) : null}
          <button
            className="sidebar-collapse"
            type="button"
            onClick={toggleSidebar}
            aria-label={
              sidebarCollapsed
                ? language === "ar"
                  ? "توسيع الشريط الجانبي"
                  : "Expand sidebar"
                : language === "ar"
                  ? "طي الشريط الجانبي"
                  : "Collapse sidebar"
            }
          >
            <IconSidebar size={20} />
            {!sidebarCollapsed ? (
              <span>{language === "ar" ? "طي القائمة" : "Collapse"}</span>
            ) : null}
          </button>
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <div className="topbar-context">
            <Button
              className="mobile-menu-trigger icon-button"
              variant="ghost"
              onClick={() => setMobileMenuOpen(true)}
              aria-label={language === "ar" ? "فتح القائمة" : "Open menu"}
              aria-expanded={mobileMenuOpen}
            >
              <IconSidebar size={20} />
            </Button>
            <div className="topbar-title">
              <small>{messages.merchantWorkspace}</small>
              <span>{currentLabel}</span>
            </div>
            <button
              className="global-search"
              type="button"
              onClick={() => setCommandOpen(true)}
              aria-label={language === "ar" ? "فتح البحث" : "Open search"}
            >
              <IconSearch size={18} />
              <span>{language === "ar" ? "بحث سريع…" : "Search…"}</span>
              <kbd>⌘K</kbd>
            </button>
          </div>
          <div className="topbar-actions">
            {demoMode ? <DemoStatus language={language} compact /> : null}
            {freeAccess ? <AccessStatus language={language} compact /> : null}
            <Button
              className="icon-button"
              variant="ghost"
              onClick={toggleTheme}
              aria-label={
                theme === "dark"
                  ? "Activate light mode"
                  : theme === "light"
                    ? "Follow system theme"
                    : "Activate dark mode"
              }
              title={
                theme === "dark"
                  ? "Light mode"
                  : theme === "light"
                    ? "System theme"
                    : "Dark mode"
              }
            >
              {theme === "system" ? (
                <IconSystem size={20} />
              ) : resolvedTheme === "dark" ? (
                <IconSun size={20} />
              ) : (
                <IconMoon size={20} />
              )}
            </Button>
            <Button
              className="language-switch"
              variant="ghost"
              onClick={toggle}
              aria-label={language === "ar" ? "تغيير اللغة" : "Switch language"}
            >
              <IconGlobe size={18} />
              {language === "ar" ? "EN" : "AR"}
            </Button>
            <div className="topbar-popover-wrap">
              <button
                className="profile-trigger"
                type="button"
                onClick={() => {
                  setProfileOpen((current) => !current);
                }}
                aria-label={language === "ar" ? "قائمة الحساب" : "Account menu"}
                aria-expanded={profileOpen}
              >
                <span className="profile-avatar">
                  {(user?.email || "C").charAt(0).toUpperCase()}
                </span>
                <span className="profile-copy">
                  <b>{user?.email?.split("@")[0] || "Merchant"}</b>
                  <small>{user?.email}</small>
                </span>
                <IconCaretDown size={15} />
              </button>
              {profileOpen ? (
                <section className="topbar-popover profile-menu">
                  <button type="button" onClick={() => goTo("/app/settings")}>
                    <IconSettings size={18} />
                    {language === "ar"
                      ? "إعدادات مساحة العمل"
                      : "Workspace settings"}
                  </button>
                  <button
                    type="button"
                    onClick={signOut}
                    className="danger-link"
                  >
                    <IconLogout size={18} />
                    {messages.logout}
                  </button>
                </section>
              ) : null}
            </div>
          </div>
        </header>

        {!online || backOnline ? (
          <div
            className={`connection-banner ${backOnline ? "connection-banner--online" : ""}`}
            role="status"
          >
            <IconWifiOff size={18} />
            {backOnline
              ? language === "ar"
                ? "عدت للاتصال"
                : "Back online"
              : language === "ar"
                ? "أنت غير متصل — ستتم مزامنة التغييرات عند عودة الاتصال"
                : "You're offline — changes will sync when you're back"}
          </div>
        ) : null}

        <main className="page">
          <AnimatePresence mode="wait">
            <motion.div key={location.pathname}>
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      <nav
        className="mobile-nav"
        aria-label={language === "ar" ? "تنقل الهاتف" : "Mobile navigation"}
      >
        {(navigationGroups[0]?.items.slice(0, 4) ?? []).map((item) => (
          <NavigationLink key={item.to} item={item} language={language} />
        ))}
        <button
          type="button"
          onClick={() => setMobileMenuOpen(true)}
          aria-label={language === "ar" ? "المزيد" : "More"}
        >
          <IconSettings size={20} />
          <span>{language === "ar" ? "المزيد" : "More"}</span>
        </button>
      </nav>

      {mobileMenuOpen ? (
        <div className="mobile-menu-layer" role="presentation">
          <button
            className="mobile-menu-scrim"
            type="button"
            onClick={closeMenu}
            aria-label={language === "ar" ? "إغلاق القائمة" : "Close menu"}
          />
          <aside
            ref={drawerRef}
            className="mobile-menu-drawer"
            role="dialog"
            aria-modal="true"
            aria-label={
              language === "ar" ? "قائمة التطبيق" : "Application menu"
            }
          >
            <div className="mobile-menu-head">
              <Brand />
              <Button
                className="icon-button"
                variant="ghost"
                onClick={closeMenu}
                data-drawer-close
                aria-label={language === "ar" ? "إغلاق القائمة" : "Close menu"}
              >
                <IconX size={20} />
              </Button>
            </div>
            {freeAccess ? <AccessStatus language={language} /> : null}
            {demoMode ? <DemoStatus language={language} /> : null}
            <nav>
              {visibleGroups.map((group) => (
                <section className="nav-group" key={group.en}>
                  <span className="nav-group-label">
                    {language === "ar" ? group.ar : group.en}
                  </span>
                  {group.items.map((item) => (
                    <NavigationLink
                      key={item.to}
                      item={item}
                      language={language}
                      locked={isLocked(item)}
                      onNavigate={closeMenu}
                    />
                  ))}
                </section>
              ))}
              {isOperator ? (
                <NavigationLink
                  item={operatorItem}
                  language={language}
                  onNavigate={closeMenu}
                />
              ) : null}
              <NavigationLink
                item={{
                  to: "/app/onboarding",
                  ar: "جاهزية المتجر",
                  en: "Store readiness",
                  icon: IconTarget,
                }}
                language={language}
                onNavigate={closeMenu}
              />
            </nav>
          </aside>
        </div>
      ) : null}

      <CommandPalette
        open={commandOpen}
        language={language}
        items={allItems.filter((item) => !isLocked(item))}
        onClose={() => setCommandOpen(false)}
        onNavigate={goTo}
      />
    </div>
  );
}
