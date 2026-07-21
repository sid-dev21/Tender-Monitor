import type { ReactNode } from 'react'
import { LogoImage } from './Logo'

/** Centered card on the brand navy background, shared by the password-reset
 * screens — follows thesis_mockups/03_forgot_password.png. Login/Register use
 * the wider split layout; these two are short single-purpose forms, so the
 * focused card keeps attention on the single action. */
export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle: string
  children: ReactNode
  /** Rendered inside the card, centered, under the form (e.g. the back link). */
  footer?: ReactNode
}) {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-navy p-6">
      <div
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          background:
            'radial-gradient(circle at 50% 35%, rgba(201,152,42,0.12) 0%, rgba(201,152,42,0) 55%)',
        }}
      />

      <div className="relative w-full max-w-[460px]">
        <div className="rounded-2xl bg-white px-8 pb-8 pt-10 shadow-2xl sm:px-10">
          {/* White card, so the real logo (dark wordmark) is legible here. */}
          <div className="flex justify-center">
            <LogoImage className="h-20" />
          </div>

          <h1 className="mt-6 text-center font-display text-2xl font-extrabold leading-tight text-ink">
            {title}
          </h1>
          <p className="mx-auto mt-2 max-w-[340px] text-center text-sm text-muted">{subtitle}</p>

          <div className="mt-7">{children}</div>

          {footer && <div className="mt-6 text-center text-sm">{footer}</div>}
        </div>
      </div>

      <footer className="relative mt-10 text-center text-xs text-white/40">
        <p className="uppercase tracking-widest">© 2025 Tender Monitor</p>
      </footer>
    </div>
  )
}

export const authInputCls =
  'w-full rounded-xl border border-line py-3.5 pl-12 pr-4 text-base text-ink outline-none placeholder:text-muted-soft focus:border-orange focus:ring-2 focus:ring-orange/15'

export const authButtonCls =
  'flex w-full items-center justify-center gap-2 rounded-xl bg-orange py-4 text-base font-semibold text-white shadow-lg shadow-orange/20 transition-colors hover:bg-orange-dark disabled:opacity-60'
