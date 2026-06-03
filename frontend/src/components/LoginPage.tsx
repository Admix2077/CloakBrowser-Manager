import { useState, type FormEvent } from "react";
import { Lock } from "lucide-react";
import { api } from "../lib/api";

interface LoginPageProps {
  onSuccess: () => void;
}

export function LoginPage({ onSuccess }: LoginPageProps) {
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.login(token);
      onSuccess();
    } catch {
      setError("Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-surface-0">
      <div className="w-80 rounded-lg border border-border bg-surface-1 p-6 shadow-panel">
        <div className="flex flex-col items-center mb-6">
          <div className="h-10 w-10 rounded-lg bg-accent/10 flex items-center justify-center mb-3">
            <Lock className="h-5 w-5 text-accent" />
          </div>
          <h1 className="text-lg font-semibold text-slate-950">
            Invisible Browser Manager
          </h1>
          <p className="mt-1 text-xs text-slate-500">Enter your access token</p>
        </div>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            className="input mb-3"
            placeholder="Access token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            autoFocus
          />
          {error && <p className="mb-3 text-xs text-red-700">{error}</p>}
          <button
            type="submit"
            disabled={loading || !token}
            className="btn-primary w-full disabled:opacity-50"
          >
            {loading ? "Authenticating..." : "Unlock"}
          </button>
        </form>
      </div>
    </div>
  );
}
