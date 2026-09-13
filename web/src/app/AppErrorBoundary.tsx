import { Component, type ErrorInfo, type ReactNode } from "react";
import { ErrorPage } from "../features/legal/PublicPages";

export class AppErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Application render failure", error, info.componentStack);
  }

  render() {
    if (this.state.failed) {
      return <ErrorPage retry={() => this.setState({ failed: false })} />;
    }
    return this.props.children;
  }
}
