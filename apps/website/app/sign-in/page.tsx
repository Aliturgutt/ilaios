import type { Metadata } from "next";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://ilaios.com";

export const metadata: Metadata = {
  title: "Sign In - ILAIOS",
  description: "Sign in to ILAIOS Governed AI Operating System",
  canonical: `${siteUrl}/sign-in`,
  alternates: {
    languages: {
      en: `${siteUrl}/sign-in`,
      tr: `${siteUrl}/tr/sign-in`,
      'x-default': `${siteUrl}/sign-in`,
    },
  },
};

export default function SignInPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-[var(--bg)] text-[var(--text)] p-4">
      <div className="max-w-md w-full space-y-6">
        <h1 className="text-3xl font-bold">Sign In</h1>
        <form className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-1">
              Email address
            </label>
            <input id="email" type="email" required className="w-full px-4 py-2 border border-[var(--line)] rounded-[var(--radius-md)] bg-[var(--panel)] text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-1">
              Password
            </label>
            <input id="password" type="password" required className="w-full px-4 py-2 border border-[var(--line)] rounded-[var(--radius-md)] bg-[var(--panel)] text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" />
          </div>
          <button type="submit" className="w-full bg-[var(--accent)] text-white px-6 py-3 rounded-[var(--radius-md)] font-medium hover:bg-[var(--accent-2)] transition-colors">
            Sign In
          </button>
        </form>
      </div>
    </main>
  );
}
