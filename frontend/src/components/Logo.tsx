/**
 * Tender Monitor brand mark, rendered as inline SVG so it stays crisp on any
 * background (the raster logo ships with an opaque blue box, unusable on navy).
 * A flat interpretation of the signal-over-building mark from the mockups.
 */

import logoMark from '../assets/logo-mark.png'
import logoMarkLight from '../assets/logo-mark-light.png'

const GOLD = '#c9982a'

let markId = 0

/**
 * The real brand logo (3-D render, mark above wordmark, transparent background).
 *
 * Two variants, because the artwork's structure and "TENDER" wordmark are dark
 * navy and vanish on the navy surfaces:
 *   tone="dark"  (default) — original artwork, for white/light surfaces.
 *   tone="light"           — navy parts lifted to near-white, copper untouched,
 *                            for the navy sidebar and auth asides. Matches
 *                            thesis_mockups/03_dashboard.png.
 *
 * It is a detailed render: readable from roughly 64px up. Below that, prefer
 * the flat <LogoMark />.
 */
export function LogoImage({
  tone = 'dark',
  className = 'h-20',
}: {
  tone?: 'light' | 'dark'
  className?: string
}) {
  return (
    <img
      src={tone === 'light' ? logoMarkLight : logoMark}
      alt="Tender Monitor"
      className={`${className} w-auto object-contain`}
    />
  )
}

export function LogoMark({ className = 'h-9 w-9', tone = 'light' }: { className?: string; tone?: 'light' | 'dark' }) {
  // Flat reading of the 3-D brand mark: three copper signal arcs above a
  // navy tower + colonnade, wrapped by two copper orbit swooshes. The
  // structure takes the tone colour so it stays visible on navy or on white.
  const bar = tone === 'light' ? '#ffffff' : '#12314f'
  const gid = `tm-gold-${markId++}`
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" aria-hidden="true">
      <defs>
        <linearGradient id={gid} x1="8" y1="6" x2="40" y2="46" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#f2cd7d" />
          <stop offset="0.45" stopColor={GOLD} />
          <stop offset="1" stopColor="#8a5a16" />
        </linearGradient>
      </defs>

      {/* signal arcs */}
      <g stroke={`url(#${gid})`} strokeLinecap="round" fill="none">
        <path d="M12.5 18.5 Q24 5.5 35.5 18.5" strokeWidth="2.7" />
        <path d="M16.5 22 Q24 12.5 31.5 22" strokeWidth="2.5" />
        <path d="M20.2 25.4 Q24 20.4 27.8 25.4" strokeWidth="2.3" />
      </g>

      {/* tower + colonnade */}
      <g stroke={bar} strokeWidth="1.9" strokeLinejoin="round" fill="none">
        <path d="M21 43V27.5l4-3.5 4 3.5V43" />
        <path d="M14.5 43V32l6.5-4.5" />
      </g>
      <g fill={bar}>
        {[15.5, 19.6, 23.7, 27.8, 31.9].map((x) => (
          <rect key={x} x={x} y="35.5" width="2.4" height="7.5" rx="0.6" />
        ))}
        <rect x="13" y="43" width="22" height="1.9" rx="0.9" />
      </g>

      {/* orbit swooshes */}
      <g stroke={`url(#${gid})`} strokeLinecap="round" fill="none">
        <path d="M9.5 33.5q7.5 9 24.5 2.5Q42 32.5 38.5 24" strokeWidth="2.5" />
        <path d="M12 39.5q8 5.5 21.5-.5" strokeWidth="2.1" opacity="0.85" />
      </g>
    </svg>
  )
}

export function Logo({
  tone = 'light',
  className = '',
  markClassName = 'h-9 w-9',
}: {
  tone?: 'light' | 'dark'
  className?: string
  markClassName?: string
}) {
  const tender = tone === 'light' ? 'text-white' : 'text-ink'
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <LogoMark tone={tone} className={markClassName} />
      <span className="font-display text-lg font-extrabold tracking-tight">
        <span className={tender}>TENDER </span>
        <span className="text-gold">MONITOR</span>
      </span>
    </span>
  )
}
