"use client"

import { useState } from "react"
import { TMXWorkspace } from "@/components/tmx-workspace"
import { SettingsPage } from "@/components/settings-page"
import { Button } from "@/components/ui/button"
import { Settings } from "lucide-react"

export default function Home() {
  const [showSettings, setShowSettings] = useState(false)

  return (
    <main className="container mx-auto py-6 px-4 md:px-6 min-h-screen">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Language Data Workbench</h1>
          <p className="text-muted-foreground">
            Upload TMX, Excel, and XLIFF files and apply multiple operations before downloading
          </p>
        </div>
        {!showSettings && (
          <Button
            variant="outline"
            size="icon"
            onClick={() => setShowSettings(true)}
            className="ml-4"
          >
            <Settings className="h-5 w-5" />
          </Button>
        )}
      </div>
      {showSettings ? (
        <SettingsPage onBack={() => setShowSettings(false)} />
      ) : (
        <TMXWorkspace />
      )}
    </main>
  )
}

