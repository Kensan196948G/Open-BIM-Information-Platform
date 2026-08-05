import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, History, Layers, Shield } from "lucide-react";
import { useAuthStore } from "@/hooks/useAuthStore";
import { api } from "@/lib/api";
import type { User } from "@/types";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [oidcUrl, setOidcUrl] = useState<string | null>(null);
  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    document.documentElement.dataset.theme =
      localStorage.getItem("obim-theme") || "light";
    api
      .get<{ enabled: boolean; authorize_url: string | null }>(
        "/auth/oidc/config",
      )
      .then((r) => {
        if (r.data.enabled && r.data.authorize_url) {
          setOidcUrl(r.data.authorize_url);
        }
      })
      .catch(() => {
        // OIDC endpoint unavailable — keep SSO disabled
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    // Demo credentials are only accepted in mock/demo mode; never in a real deployment.
    if (
      import.meta.env.VITE_MOCK_MODE === "true" &&
      email === "demo@example.com" &&
      password === "pass1234"
    ) {
      const demoToken = "demo-preview-token";
      localStorage.setItem("access_token", demoToken);
      setAuth(
        demoToken,
        {
          id: "demo-user",
          email,
          username: "demouser",
          full_name: "Demo User",
          is_active: true,
          is_platform_admin: true,
        },
        "demo-refresh-token",
      );
      navigate("/dashboard");
      setLoading(false);
      return;
    }
    try {
      const form = new URLSearchParams();
      form.append("username", email);
      form.append("password", password);
      const tokenRes = await api.post<{
        access_token: string;
        refresh_token: string;
      }>(
        "/auth/login",
        form,
        { headers: { "Content-Type": "application/x-www-form-urlencoded" } },
      );
      localStorage.setItem("access_token", tokenRes.data.access_token);
      localStorage.setItem("refresh_token", tokenRes.data.refresh_token);
      const meRes = await api.get<User>("/auth/me");
      setAuth(tokenRes.data.access_token, meRes.data, tokenRes.data.refresh_token);
      navigate("/dashboard");
    } catch {
      setError("メールアドレスまたはパスワードが正しくありません");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen" style={{ background: "var(--bg)", color: "var(--text)" }}>
      <div className="relative hidden flex-[1.1] flex-col justify-between overflow-hidden p-12 text-white lg:flex" style={{ background: "linear-gradient(150deg, #0e1116 0%, #15233f 60%, #1a2a52 100%)" }}>
        <div className="absolute inset-0 opacity-60" style={{ backgroundImage: "linear-gradient(rgba(120,150,220,.10) 1px, transparent 1px), linear-gradient(90deg, rgba(120,150,220,.10) 1px, transparent 1px)", backgroundSize: "32px 32px" }} />
        <div className="relative flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-[#0e1116]">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <div className="text-[15px] font-bold">Open BIM 情報基盤</div>
            <div className="text-[10.5px] tracking-[0.06em] text-white/55">COMMON DATA ENVIRONMENT</div>
          </div>
        </div>

        <div className="relative max-w-md">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-[11.5px] font-semibold">
            <span className="h-1.5 w-1.5 rounded-full bg-[#5fd699]" />
            ISO 19650 準拠支援（未認証）
          </div>
          <h1 className="text-[30px] font-semibold leading-snug tracking-normal">
            建設情報を、
            <br />
            ひとつの信頼できる基盤で。
          </h1>
          <p className="mt-4 text-[13.5px] leading-7 text-white/65">
            CDE 状態管理・命名規則検証・承認ワークフロー・監査証跡を統合。
          </p>
          <div className="mt-8 flex gap-7">
            {[
              ["状態管理", "WIP → Published"],
              ["監査証跡", "Append-Only"],
              ["命名検証", "Annex A 準拠"],
            ].map(([label, value]) => (
              <div key={label}>
                <div className="text-sm font-semibold">{label}</div>
                <div className="mono mt-1 text-[11px] text-white/50">{value}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative text-[11px] text-white/40">© 2026 Open BIM 情報基盤 · v0.1.0</div>
      </div>

      <div className="flex flex-1 items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-[360px]">
          <h2 className="t-h1 text-[22px]">ログイン</h2>
          <p className="t-sec mb-7 mt-1">アカウントにサインインして続行</p>

          {oidcUrl ? (
            <a href={oidcUrl} className="app-btn h-10 w-full">
              <Shield className="h-4 w-4" />
              SSO / OIDC でサインイン
            </a>
          ) : (
            <button
              className="app-btn h-10 w-full"
              disabled
              title="SSO連携は未設定です"
            >
              <Shield className="h-4 w-4" />
              SSO / OIDC でサインイン（未設定）
            </button>
          )}
          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1" style={{ background: "var(--border)" }} />
            <span className="t-tiny">またはメールアドレス</span>
            <div className="h-px flex-1" style={{ background: "var(--border)" }} />
          </div>

          <form onSubmit={handleSubmit} className="grid gap-4">
            <label>
              <div className="mb-1 text-[12.5px] font-medium" style={{ color: "var(--text-2)" }}>メールアドレス</div>
              <input className="app-field h-10" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="user@example.com" />
            </label>
            <label>
              <div className="mb-1 text-[12.5px] font-medium" style={{ color: "var(--text-2)" }}>パスワード</div>
              <input className="app-field h-10" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </label>
            {error && <div className="rounded-lg p-3 text-sm tone-danger">{error}</div>}
            <button className="app-btn app-btn-primary h-10 w-full" disabled={loading}>
              {loading ? (
                <>
                  <History className="h-4 w-4 animate-spin" />
                  認証中...
                </>
              ) : (
                <>
                  ログイン
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          <p className="t-tiny mt-6 text-center leading-6">
            現在はパスワード認証です（MFA / SSO は今後対応予定）。
            <br />
            主要な操作は監査ログに記録されます。
          </p>
        </div>
      </div>
    </div>
  );
}
