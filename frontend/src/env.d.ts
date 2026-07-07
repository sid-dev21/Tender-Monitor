/// <reference types="vite/client" />

// Type our custom Vite env vars so TypeScript knows about import.meta.env.VITE_API_URL.
interface ImportMetaEnv {
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
