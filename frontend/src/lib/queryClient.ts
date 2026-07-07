import { QueryClient } from '@tanstack/react-query'

// Single shared query client. Sensible defaults for a monitoring app:
// data is considered fresh for 30s, and failed requests retry once.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})
