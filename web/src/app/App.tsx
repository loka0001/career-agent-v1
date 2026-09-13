import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { Spinner } from "../components/ui";
import {
  ErrorPage,
  NotFoundPage,
  TermsPage,
} from "../features/legal/PublicPages";
import { AuthProvider } from "./AuthContext";
import { EntitledRoute, OperatorRoute, ProtectedRoute } from "./ProtectedRoute";

const AppShell = lazy(() =>
  import("./AppShell").then(({ AppShell: shell }) => ({ default: shell })),
);
const LandingPage = lazy(() =>
  import("../features/landing/LandingPage").then(({ LandingPage: page }) => ({
    default: page,
  })),
);
const LoginPage = lazy(() =>
  import("../features/auth/LoginPage").then(({ LoginPage: page }) => ({
    default: page,
  })),
);
const SignupPage = lazy(() =>
  import("../features/auth/AccountPages").then(({ SignupPage: page }) => ({
    default: page,
  })),
);
const VerifyEmailPage = lazy(() =>
  import("../features/auth/AccountPages").then(({ VerifyEmailPage: page }) => ({
    default: page,
  })),
);
const ForgotPasswordPage = lazy(() =>
  import("../features/auth/AccountPages").then(
    ({ ForgotPasswordPage: page }) => ({
      default: page,
    }),
  ),
);
const ResetPasswordPage = lazy(() =>
  import("../features/auth/AccountPages").then(
    ({ ResetPasswordPage: page }) => ({
      default: page,
    }),
  ),
);
const AcceptInvitePage = lazy(() =>
  import("../features/auth/AccountPages").then(
    ({ AcceptInvitePage: page }) => ({
      default: page,
    }),
  ),
);
const CommandCenterPage = lazy(() =>
  import("../features/command/CommandCenterPage").then(
    ({ CommandCenterPage: page }) => ({ default: page }),
  ),
);
const InboxPage = lazy(() =>
  import("../features/inbox/InboxPage").then(({ InboxPage: page }) => ({
    default: page,
  })),
);
const OpportunitiesPage = lazy(() =>
  import("../features/opportunities/OpportunitiesPage").then(
    ({ OpportunitiesPage: page }) => ({ default: page }),
  ),
);
const CustomersPage = lazy(() =>
  import("../features/customers/CustomersPage").then(
    ({ CustomersPage: page }) => ({
      default: page,
    }),
  ),
);
const ProductsPage = lazy(() =>
  import("../features/products/ProductsPage").then(
    ({ ProductsPage: page }) => ({
      default: page,
    }),
  ),
);
const NewProductPage = lazy(() =>
  import("../features/products/NewProductPage").then(
    ({ NewProductPage: page }) => ({
      default: page,
    }),
  ),
);
const OrdersPage = lazy(() =>
  import("../features/orders/OrdersPage").then(({ OrdersPage: page }) => ({
    default: page,
  })),
);
const ContentStudioPage = lazy(() =>
  import("../features/studio/ContentStudioPage").then(
    ({ ContentStudioPage: page }) => ({ default: page }),
  ),
);
const CampaignCalendarPage = lazy(() =>
  import("../features/studio/CampaignCalendarPage").then(
    ({ CampaignCalendarPage: page }) => ({ default: page }),
  ),
);
const AnalyticsPage = lazy(() =>
  import("../features/analytics/AnalyticsPage").then(
    ({ AnalyticsPage: page }) => ({
      default: page,
    }),
  ),
);
const AutomationsPage = lazy(() =>
  import("../features/automations/AutomationsPage").then(
    ({ AutomationsPage: page }) => ({ default: page }),
  ),
);
const IntegrationsPage = lazy(() =>
  import("../features/integrations/IntegrationsPage").then(
    ({ IntegrationsPage: page }) => ({ default: page }),
  ),
);
const BillingPage = lazy(() =>
  import("../features/billing/BillingPage").then(({ BillingPage: page }) => ({
    default: page,
  })),
);
const StoreSettingsPage = lazy(() =>
  import("../features/settings/SettingsPages").then(
    ({ StoreSettingsPage: page }) => ({ default: page }),
  ),
);
const AgentSettingsPage = lazy(() =>
  import("../features/settings/SettingsPages").then(
    ({ AgentSettingsPage: page }) => ({ default: page }),
  ),
);
const TeamPage = lazy(() =>
  import("../features/settings/SettingsPages").then(({ TeamPage: page }) => ({
    default: page,
  })),
);
const SecurityPage = lazy(() =>
  import("../features/settings/SettingsPages").then(
    ({ SecurityPage: page }) => ({
      default: page,
    }),
  ),
);
const ApiKeysPage = lazy(() =>
  import("../features/settings/SettingsPages").then(
    ({ ApiKeysPage: page }) => ({
      default: page,
    }),
  ),
);
const OnboardingPage = lazy(() =>
  import("../features/settings/SettingsPages").then(
    ({ OnboardingPage: page }) => ({ default: page }),
  ),
);
const PrivacyPage = lazy(() =>
  import("../features/settings/PrivacyPage").then(({ PrivacyPage: page }) => ({
    default: page,
  })),
);
const OperatorPage = lazy(() =>
  import("../features/operator/OperatorPage").then(
    ({ OperatorPage: page }) => ({
      default: page,
    }),
  ),
);
function RouteLoader() {
  return (
    <main className="center">
      <Spinner label="جارٍ تحميل الصفحة…" />
    </main>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<RouteLoader />}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/accept-invite" element={<AcceptInvitePage />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/500" element={<ErrorPage />} />
            <Route
              path="/app"
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="command" replace />} />
              <Route path="command" element={<CommandCenterPage />} />
              <Route
                path="dashboard"
                element={<Navigate to="/app/command" replace />}
              />
              <Route path="inbox" element={<InboxPage />} />
              <Route
                path="opportunities"
                element={
                  <EntitledRoute feature="opportunities">
                    <OpportunitiesPage />
                  </EntitledRoute>
                }
              />
              <Route path="customers" element={<CustomersPage />} />
              <Route
                path="products"
                element={
                  <EntitledRoute feature="catalog">
                    <ProductsPage />
                  </EntitledRoute>
                }
              />
              <Route
                path="products/new"
                element={
                  <EntitledRoute feature="catalog">
                    <NewProductPage />
                  </EntitledRoute>
                }
              />
              <Route path="orders" element={<OrdersPage />} />
              <Route
                path="studio"
                element={
                  <EntitledRoute feature="content_studio">
                    <ContentStudioPage />
                  </EntitledRoute>
                }
              />
              <Route
                path="calendar"
                element={
                  <EntitledRoute feature="content_studio">
                    <CampaignCalendarPage />
                  </EntitledRoute>
                }
              />
              <Route
                path="analytics"
                element={
                  <EntitledRoute feature="analytics">
                    <AnalyticsPage />
                  </EntitledRoute>
                }
              />
              <Route
                path="automations"
                element={
                  <EntitledRoute feature="automations">
                    <AutomationsPage />
                  </EntitledRoute>
                }
              />
              <Route path="integrations" element={<IntegrationsPage />} />
              <Route
                path="agent-settings"
                element={
                  <EntitledRoute feature="inbox">
                    <AgentSettingsPage />
                  </EntitledRoute>
                }
              />
              <Route path="team" element={<TeamPage />} />
              <Route path="billing" element={<BillingPage />} />
              <Route path="settings" element={<StoreSettingsPage />} />
              <Route path="security" element={<SecurityPage />} />
              <Route
                path="api-keys"
                element={
                  <EntitledRoute feature="website_widget">
                    <ApiKeysPage />
                  </EntitledRoute>
                }
              />
              <Route path="onboarding" element={<OnboardingPage />} />
              <Route path="privacy" element={<PrivacyPage />} />
              <Route
                path="operator"
                element={
                  <OperatorRoute>
                    <OperatorPage />
                  </OperatorRoute>
                }
              />
              <Route
                path="*"
                element={<Navigate to="/app/command" replace />}
              />
            </Route>
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
