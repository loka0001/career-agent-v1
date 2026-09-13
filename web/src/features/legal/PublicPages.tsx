import { useEffect, type ReactNode } from "react";
import { Link } from "react-router";
import { Brand } from "../../components/layout/Brand";

function PublicPageFrame({ children }: { children: ReactNode }) {
  return (
    <main className="public-page">
      <div className="public-page__backdrop" aria-hidden="true" />
      <header className="public-page__header">
        <Brand />
      </header>
      {children}
    </main>
  );
}

function StatusPage({
  code,
  title,
  description,
  retry,
}: {
  code: string;
  title: string;
  description: string;
  retry?: () => void;
}) {
  useEffect(() => {
    document.title = `${code} — Commerce Revenue Autopilot`;
  }, [code]);

  return (
    <PublicPageFrame>
      <section className="public-status card" aria-labelledby="status-title">
        <p className="public-status__code" aria-hidden="true">
          {code}
        </p>
        <p className="public-status__eyebrow">Commerce Revenue Autopilot</p>
        <h1 id="status-title">{title}</h1>
        <p>{description}</p>
        <div className="public-status__actions">
          {retry && (
            <button
              className="button button--primary"
              type="button"
              onClick={retry}
            >
              Try again
            </button>
          )}
          <Link
            className={`button ${retry ? "button--secondary" : "button--primary"}`}
            to="/"
          >
            Return home
          </Link>
        </div>
      </section>
    </PublicPageFrame>
  );
}

export function NotFoundPage() {
  return (
    <StatusPage
      code="404"
      title="This page is off the map"
      description="The address may be outdated, or the page may have moved. Your commerce workspace is still safe."
    />
  );
}

export function ErrorPage({
  retry = () => window.location.reload(),
}: {
  retry?: () => void;
}) {
  return (
    <StatusPage
      code="500"
      title="This page did not load"
      description="Something unexpected happened. Try once more, or return to the homepage while we recover."
      retry={retry}
    />
  );
}

const sections = [
  [
    "Using the service",
    "Use the platform lawfully, keep account credentials secure, and provide accurate store and billing details.",
  ],
  [
    "Your content and data",
    "You retain ownership of content you submit. You permit us to process it only to operate and improve the service.",
  ],
  [
    "Connected services",
    "Third-party commerce, messaging, and payment providers remain governed by their own terms and availability.",
  ],
  [
    "Plans and billing",
    "Paid plans renew according to the selected billing interval. Fees and cancellation terms are shown before purchase.",
  ],
  [
    "Acceptable use",
    "Do not abuse public widgets, bypass security controls, send unlawful communications, or interfere with other customers.",
  ],
  [
    "Service availability",
    "We work to keep the platform reliable, but maintenance, provider outages, and events outside our control may interrupt access.",
  ],
  [
    "Account termination",
    "You may stop using the service at any time. We may suspend access for material breach, abuse, or legal requirements.",
  ],
  [
    "Changes and contact",
    "Material updates will be communicated through the product or account email. Contact support with questions about these terms.",
  ],
] as const;

export function TermsPage() {
  useEffect(() => {
    document.title = "Terms & Conditions — Commerce Revenue Autopilot";
  }, []);

  return (
    <PublicPageFrame>
      <article className="legal-document card">
        <header>
          <p className="public-status__eyebrow">Legal</p>
          <h1>Terms &amp; Conditions</h1>
          <p>Effective August 8, 2026</p>
        </header>
        <p>
          These terms govern access to Commerce Revenue Autopilot. By creating
          an account or using the service, you agree to them and confirm you can
          enter this agreement.
        </p>
        {sections.map(([title, body]) => (
          <section key={title}>
            <h2>{title}</h2>
            <p>{body}</p>
          </section>
        ))}
        <footer>
          <Link className="button button--secondary" to="/">
            Back to homepage
          </Link>
        </footer>
      </article>
    </PublicPageFrame>
  );
}
