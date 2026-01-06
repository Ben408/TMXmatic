"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, CheckCircle2, XCircle, Wifi, X } from "lucide-react"
import { Switch } from "@/components/ui/switch"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { toast } from "@/components/ui/use-toast"

interface SettingsPageProps {
  onBack: () => void
}

interface ConnectionTestResult {
  success: boolean
  message: string
  statusCode?: number
  error?: string
}

export function SettingsPage({ onBack }: SettingsPageProps) {
  const [blackbirdEnabled, setBlackbirdEnabled] = useState(false)
  const [okapiEnabled, setOkapiEnabled] = useState(false)
  
  // Blackbird settings
  const [blackbirdApiKey, setBlackbirdApiKey] = useState("")
  const [blackbirdApiUrl, setBlackbirdApiUrl] = useState("")
  const [blackbirdProjectId, setBlackbirdProjectId] = useState("")
  
  // Okapi settings
  const [okapiApiKey, setOkapiApiKey] = useState("")
  const [okapiApiUrl, setOkapiApiUrl] = useState("")
  const [okapiWorkspaceId, setOkapiWorkspaceId] = useState("")

  // Loading and connection test states
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testingBlackbird, setTestingBlackbird] = useState(false)
  const [testingOkapi, setTestingOkapi] = useState(false)
  const [connectionDialogOpen, setConnectionDialogOpen] = useState(false)
  const [connectionResult, setConnectionResult] = useState<ConnectionTestResult | null>(null)
  const [currentTestIntegration, setCurrentTestIntegration] = useState<string>("")

  // Load settings on mount
  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const response = await fetch('http://127.0.0.1:5000/api/settings')
      if (response.ok) {
        const data = await response.json()
        
        // Set Blackbird settings
        if (data.blackbird) {
          setBlackbirdEnabled(data.blackbird.enabled || false)
          setBlackbirdApiKey(data.blackbird.api_key || "")
          setBlackbirdApiUrl(data.blackbird.api_url || "")
          setBlackbirdProjectId(data.blackbird.project_id || "")
        }
        
        // Set Okapi settings
        if (data.okapi) {
          setOkapiEnabled(data.okapi.enabled || false)
          setOkapiApiKey(data.okapi.api_key || "")
          setOkapiApiUrl(data.okapi.api_url || "")
          setOkapiWorkspaceId(data.okapi.workspace_id || "")
        }
      }
    } catch (error) {
      console.error("Error loading settings:", error)
      toast({
        title: "Error",
        description: "Failed to load settings",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      const response = await fetch('http://127.0.0.1:5000/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          blackbird: {
            enabled: blackbirdEnabled,
            api_key: blackbirdApiKey,
            api_url: blackbirdApiUrl,
            project_id: blackbirdProjectId,
          },
          okapi: {
            enabled: okapiEnabled,
            api_key: okapiApiKey,
            api_url: okapiApiUrl,
            workspace_id: okapiWorkspaceId,
          },
        }),
      })

      if (response.ok) {
        toast({
          title: "Success",
          description: "Settings saved successfully",
        })
      } else {
        const error = await response.json()
        throw new Error(error.error || "Failed to save settings")
      }
    } catch (error) {
      console.error("Error saving settings:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to save settings",
        variant: "destructive",
      })
    } finally {
      setSaving(false)
    }
  }

  const testConnection = async (integration: 'blackbird' | 'okapi') => {
    // First save current settings temporarily
    const tempSettings = {
      blackbird: {
        enabled: integration === 'blackbird' ? true : blackbirdEnabled,
        api_key: blackbirdApiKey,
        api_url: blackbirdApiUrl,
        project_id: blackbirdProjectId,
      },
      okapi: {
        enabled: integration === 'okapi' ? true : okapiEnabled,
        api_key: okapiApiKey,
        api_url: okapiApiUrl,
        workspace_id: okapiWorkspaceId,
      },
    }

    // Validate required fields
    if (integration === 'blackbird') {
      if (!blackbirdApiKey || !blackbirdApiUrl || !blackbirdProjectId) {
        setConnectionResult({
          success: false,
          message: "Some fields are missing, please fill them in.",
        })
        setConnectionDialogOpen(true)
        setCurrentTestIntegration("Blackbird")
        return
      }
    } else {
      if (!okapiApiKey || !okapiApiUrl || !okapiWorkspaceId) {
        setConnectionResult({
          success: false,
          message: "Some fields are missing, please fill them in.",
        })
        setConnectionDialogOpen(true)
        setCurrentTestIntegration("Okapi")
        return
      }
    }

    try {
      if (integration === 'blackbird') {
        setTestingBlackbird(true)
      } else {
        setTestingOkapi(true)
      }

      // Save settings temporarily for the test
      await fetch('http://127.0.0.1:5000/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(tempSettings),
      })

      // Test connection
      const response = await fetch('http://127.0.0.1:5000/api/settings/test-connection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ integration }),
      })

      const data = await response.json()
      
      setConnectionResult({
        success: data.success || false,
        message: data.message || (data.success ? "Connection successful" : "Connection failed"),
        statusCode: data.status_code,
        error: data.error,
      })
      setCurrentTestIntegration(integration === 'blackbird' ? "Blackbird" : "Okapi")
      setConnectionDialogOpen(true)
    } catch (error) {
      setConnectionResult({
        success: false,
        message: "Failed to test connection",
        error: error instanceof Error ? error.message : "Unknown error",
      })
      setCurrentTestIntegration(integration === 'blackbird' ? "Blackbird" : "Okapi")
      setConnectionDialogOpen(true)
    } finally {
      if (integration === 'blackbird') {
        setTestingBlackbird(false)
      } else {
        setTestingOkapi(false)
      }
    }
  }

  return (
    <div className="container mx-auto py-6 px-4 md:px-6 min-h-screen">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Settings</h1>
          <p className="text-muted-foreground">
            Configure your integration settings
          </p>
        </div>
        <Button
          variant="outline"
          size="icon"
          onClick={onBack}
          className="ml-4"
        >
          <X className="h-5 w-5" />
        </Button>
      </div>

      <div className="space-y-6 max-w-4xl">
        {/* Blackbird Integration */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Blackbird Integration</CardTitle>
                <CardDescription>
                  Configure your Blackbird API connection settings
                </CardDescription>
              </div>
              <Switch
                checked={blackbirdEnabled}
                onCheckedChange={setBlackbirdEnabled}
                className="data-[state=checked]:bg-blue-600 data-[state=unchecked]:bg-red-500"
              />
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="blackbird-api-key">API Key</Label>
              <Input
                id="blackbird-api-key"
                type="password"
                placeholder="Enter your Blackbird API key"
                value={blackbirdApiKey}
                onChange={(e) => setBlackbirdApiKey(e.target.value)}
                disabled={!blackbirdEnabled}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="blackbird-api-url">API URL</Label>
              <Input
                id="blackbird-api-url"
                type="url"
                placeholder="https://api.blackbird.com"
                value={blackbirdApiUrl}
                onChange={(e) => setBlackbirdApiUrl(e.target.value)}
                disabled={!blackbirdEnabled}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="blackbird-project-id">Project ID</Label>
              <Input
                id="blackbird-project-id"
                placeholder="Enter your project ID"
                value={blackbirdProjectId}
                onChange={(e) => setBlackbirdProjectId(e.target.value)}
                disabled={!blackbirdEnabled}
              />
            </div>
            <Button
              variant="outline"
              onClick={() => testConnection('blackbird')}
              disabled={!blackbirdEnabled || testingBlackbird}
              className="w-full"
            >
              {testingBlackbird ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Testing...
                </>
              ) : (
                <>
                  <Wifi className="mr-2 h-4 w-4" />
                  Test Connection
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Okapi Integration */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Okapi Integration</CardTitle>
                <CardDescription>
                  Configure your Okapi API connection settings
                </CardDescription>
              </div>
              <Switch
                checked={okapiEnabled}
                onCheckedChange={setOkapiEnabled}
                className="data-[state=checked]:bg-blue-600 data-[state=unchecked]:bg-red-500"
              />
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="okapi-api-key">API Key</Label>
              <Input
                id="okapi-api-key"
                type="password"
                placeholder="Enter your Okapi API key"
                value={okapiApiKey}
                onChange={(e) => setOkapiApiKey(e.target.value)}
                disabled={!okapiEnabled}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="okapi-api-url">API URL</Label>
              <Input
                id="okapi-api-url"
                type="url"
                placeholder="https://api.okapi.com"
                value={okapiApiUrl}
                onChange={(e) => setOkapiApiUrl(e.target.value)}
                disabled={!okapiEnabled}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="okapi-workspace-id">Workspace ID</Label>
              <Input
                id="okapi-workspace-id"
                placeholder="Enter your workspace ID"
                value={okapiWorkspaceId}
                onChange={(e) => setOkapiWorkspaceId(e.target.value)}
                disabled={!okapiEnabled}
              />
            </div>
            <Button
              variant="outline"
              onClick={() => testConnection('okapi')}
              disabled={!okapiEnabled || testingOkapi}
              className="w-full"
            >
              {testingOkapi ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Testing...
                </>
              ) : (
                <>
                  <Wifi className="mr-2 h-4 w-4" />
                  Test Connection
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Save Button */}
        <div className="flex justify-end gap-4">
          <Button variant="outline" onClick={onBack}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving || loading}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              "Save Settings"
            )}
          </Button>
        </div>
      </div>

      {/* Connection Test Result Dialog */}
      <Dialog open={connectionDialogOpen} onOpenChange={setConnectionDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {connectionResult?.success ? (
                <>
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  Connection Successful
                </>
              ) : (
                <>
                  <XCircle className="h-5 w-5 text-red-600" />
                  Could Not Connect
                </>
              )}
            </DialogTitle>
            <DialogDescription>
              {currentTestIntegration} Connection Test Result
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="rounded-lg border p-4">
              <p className={`font-medium ${connectionResult?.success ? 'text-green-600' : 'text-red-600'}`}>
                {connectionResult?.message || "Unknown result"}
              </p>
            </div>
            {!connectionResult?.success && (
              <div className="space-y-2">
                {connectionResult?.statusCode && (
                  <div className="text-sm">
                    <span className="font-medium">HTTP Status Code: </span>
                    <span className="text-muted-foreground">{connectionResult.statusCode}</span>
                  </div>
                )}
                {connectionResult?.error && (
                  <div className="text-sm">
                    <span className="font-medium">Error Details: </span>
                    <span className="text-muted-foreground">{connectionResult.error}</span>
                  </div>
                )}
              </div>
            )}
            <div className="flex justify-end">
              <Button onClick={() => setConnectionDialogOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

