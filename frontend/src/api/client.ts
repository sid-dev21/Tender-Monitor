import axios from 'axios'

// The one axios instance the whole app uses. Base URL comes from the environment
// (VITE_API_URL), falling back to the local backend for dev.
const baseURL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach the JWT access token (saved at login) to every outgoing request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
