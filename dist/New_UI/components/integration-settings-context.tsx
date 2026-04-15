"use client"

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react"

export type IntegrationSettings = {
  okapi?: {
    enabled?: boolean
    api_key?: string
    api_url?: string
    workspace_id?: string
  }
}

type ContextValue = {
  settings: IntegrationSettings | null
  refresh: () => Promise<void>
}

const IntegrationSettingsContext = createContext<ContextValue | null>(null)

const SETTINGS_URL = "http://127.0.0.1:5000/api/settings"

export function IntegrationSettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<IntegrationSettings | null>(null)

  const refresh = useCallback(async () => {
    try {
      const res = await fetch(SETTINGS_URL, { cache: "no-store" })
      if (res.ok) {
        const data = await res.json()
        setSettings(data)
      }
    } catch (e) {
      console.error("Failed to refresh integration settings:", e)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <IntegrationSettingsContext.Provider value={{ settings, refresh }}>
      {children}
    </IntegrationSettingsContext.Provider>
  )
}

export function useIntegrationSettings(): ContextValue {
  const ctx = useContext(IntegrationSettingsContext)
  if (!ctx) {
    return {
      settings: null,
      refresh: async () => {},
    }
  }
  return ctx
}
