import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { AlertOctagon, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('RESQROUTE Runtime Exception Captured:', error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen w-screen bg-[#090d16] text-slate-100 flex flex-col items-center justify-center p-6 font-mono select-none">
          <div className="max-w-md w-full bg-[#0b0f19] border border-red-900/60 rounded-lg p-6 shadow-2xl space-y-4">
            <div className="flex items-center space-x-3 text-red-400">
              <div className="p-2 rounded bg-red-950/60 border border-red-800">
                <AlertOctagon className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-base tracking-wider uppercase text-slate-100">
                  SYSTEM EXCEPTION DETECTED
                </h3>
                <p className="text-xs text-red-400/90 font-mono">RESQROUTE RUNTIME PROTECTION</p>
              </div>
            </div>

            <div className="p-3 rounded bg-slate-900 border border-slate-800 text-xs text-slate-300 overflow-x-auto max-h-32">
              <code>{this.state.error?.message || 'An unexpected rendering error occurred.'}</code>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              The application encountered a client-side exception. Click below to re-initialize the Command Center dashboard.
            </p>

            <button
              type="button"
              onClick={this.handleReload}
              className="w-full py-2.5 px-4 rounded bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs uppercase tracking-wider transition-colors flex items-center justify-center space-x-2 shadow-lg"
            >
              <RefreshCw className="w-4 h-4" />
              <span>RELOAD COMMAND CENTER</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
