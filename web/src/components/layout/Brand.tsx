import { Link } from "react-router";
import { IconSpark } from "../icons";

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link
      to="/app/command"
      className={`brand ${compact ? "brand--compact" : ""}`}
    >
      <span className="brand-mark">
        <IconSpark size={16} />
      </span>
      <span className="brand-copy">
        <b>Commerce</b>
        <small>Revenue Autopilot</small>
      </span>
    </Link>
  );
}
