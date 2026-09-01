"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, CheckCircle2, XCircle, Wifi, X } from "lucide-react"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useTheme } from "next-themes"
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
  const { theme, resolvedTheme, setTheme } = useTheme()
  const [isMounted, setIsMounted] = useState(false)
  const [okapiEnabled, setOkapiEnabled] = useState(false)
  
  // Okapi settings — backend + hosted workspace (Phase 2)
  const [okapiBackend, setOkapiBackend] = useState("docker")
  const [okapiDockerImage, setOkapiDockerImage] = useState("ldw-okapi-tikal:1.48")
  const [okapiTikalPath, setOkapiTikalPath] = useState("")
  const [okapiLonghornUrl, setOkapiLonghornUrl] = useState("")
  const [okapiGithubRepo, setOkapiGithubRepo] = useState("")
  const [okapiGithubWorkflow, setOkapiGithubWorkflow] = useState("okapi-ops.yml")
  const [okapiGithubBranch, setOkapiGithubBranch] = useState("main")
  const [okapiGithubToken, setOkapiGithubToken] = useState("")
  const [okapiApiKey, setOkapiApiKey] = useState("")
  const [okapiApiUrl, setOkapiApiUrl] = useState("")
  const [okapiWorkspaceId, setOkapiWorkspaceId] = useState("")

  // Loading and connection test states
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testingOkapi, setTestingOkapi] = useState(false)
  const [connectionDialogOpen, setConnectionDialogOpen] = useState(false)
  const [connectionResult, setConnectionResult] = useState<ConnectionTestResult | null>(null)
  const [currentTestIntegration, setCurrentTestIntegration] = useState<string>("")

  // Load settings on mount
  useEffect(() => {
    loadSettings()
  }, [])

  useEffect(() => {
    setIsMounted(true)
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const response = await fetch('http://127.0.0.1:5000/api/settings', { cache: 'no-store' })
      if (response.ok) {
        const data = await response.json()
        
        // Set Okapi settings
        if (data.okapi) {
          setOkapiEnabled(data.okapi.enabled || false)
          setOkapiBackend(data.okapi.backend || "docker")
          setOkapiDockerImage(data.okapi.docker_image || "ldw-okapi-tikal:1.48")
          setOkapiTikalPath(data.okapi.tikal_path || "")
          setOkapiLonghornUrl(data.okapi.longhorn_url || "")
          setOkapiGithubRepo(data.okapi.github_repo || "")
          setOkapiGithubWorkflow(data.okapi.github_workflow || "okapi-ops.yml")
          setOkapiGithubBranch(data.okapi.github_branch || "main")
          setOkapiGithubToken(data.okapi.github_token || "")
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
          okapi: {
            enabled: okapiEnabled,
            backend: okapiBackend,
            docker_image: okapiDockerImage,
            tikal_path: okapiTikalPath,
            longhorn_url: okapiLonghornUrl,
            github_repo: okapiGithubRepo,
            github_workflow: okapiGithubWorkflow,
            github_branch: okapiGithubBranch,
            github_token: okapiGithubToken,
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

  const testConnection = async (integration: 'okapi') => {
    // First save current settings temporarily
    const tempSettings = {
      okapi: {
        enabled: integration === 'okapi' ? true : okapiEnabled,
        api_key: okapiApiKey,
        api_url: okapiApiUrl,
        workspace_id: okapiWorkspaceId,
      },
    }

    // Validate required fields
    if (!okapiApiKey || !okapiApiUrl || !okapiWorkspaceId) {
      setConnectionResult({
        success: false,
        message: "Some fields are missing, please fill them in.",
      })
      setConnectionDialogOpen(true)
      setCurrentTestIntegration("Okapi")
      return
    }

    try {
      setTestingOkapi(true)

      // Save settings temporarily for the test
      await fetch('http://127.0.0.1:5000/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(tempSettings),
      })

      // Test connection using current form values so backend doesn't rely on saved files
      const response = await fetch('http://127.0.0.1:5000/api/settings/test-connection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          integration,
          okapi: tempSettings.okapi,
        }),
      })

      const data = await response.json()
      
      setConnectionResult({
        success: data.success || false,
        message: data.message || (data.success ? "Connection successful" : "Connection failed"),
        statusCode: data.status_code,
        error: data.error,
      })
      setCurrentTestIntegration("Okapi")
      setConnectionDialogOpen(true)
    } catch (error) {
      setConnectionResult({
        success: false,
        message: "Failed to test connection",
        error: error instanceof Error ? error.message : "Unknown error",
      })
      setCurrentTestIntegration("Okapi")
      setConnectionDialogOpen(true)
    } finally {
      setTestingOkapi(false)
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
        {/* Appearance */}
        <Card>
          <CardHeader>
            <CardTitle>Appearance</CardTitle>
            <CardDescription>
              Light, dark, or match your system setting
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Label htmlFor="theme-select">Theme</Label>
            <Select
              value={isMounted ? (theme ?? "system") : "system"}
              onValueChange={(value) => setTheme(value)}
              disabled={!isMounted}
            >
              <SelectTrigger id="theme-select" className="max-w-xs">
                <SelectValue placeholder="Theme" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">Light</SelectItem>
                <SelectItem value="dark">Dark</SelectItem>
                <SelectItem value="system">System</SelectItem>
              </SelectContent>
            </Select>
            {isMounted && theme === "system" && resolvedTheme && (
              <p className="text-sm text-muted-foreground">
                Using {resolvedTheme === "dark" ? "dark" : "light"} from your
                system
              </p>
            )}
          </CardContent>
        </Card>

        {/* Okapi Integration */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Okapi Integration</CardTitle>
                <CardDescription>
                  Processing backend (Docker tikal, local tikal, GHA, Longhorn) and hosted workspace API
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
              <Label htmlFor="okapi-backend">Processing backend</Label>
              <Select
                value={okapiBackend}
                onValueChange={setOkapiBackend}
                disabled={!okapiEnabled}
              >
                <SelectTrigger id="okapi-backend">
                  <SelectValue placeholder="Select backend" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="docker">Docker tikal (pilot default — JRE in container)</SelectItem>
                  <SelectItem value="github">GitHub Actions (user fork — JRE on runner)</SelectItem>
                  <SelectItem value="longhorn">External Longhorn API</SelectItem>
                  <SelectItem value="hosted">Hosted Okapi workspace</SelectItem>
                  <SelectItem value="local_tikal">Local tikal (not recommended — host JRE)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="okapi-docker-image">Docker image</Label>
              <Input
                id="okapi-docker-image"
                placeholder="ldw-okapi-tikal:1.48"
                value={okapiDockerImage}
                onChange={(e) => setOkapiDockerImage(e.target.value)}
                disabled={!okapiEnabled || okapiBackend !== "docker"}
              />
              <p className="text-xs text-muted-foreground">
                Build locally: <code className="text-xs">scripts\build_okapi_tikal_image.ps1</code>
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="okapi-tikal-path">Local tikal path</Label>
              <Input
                id="okapi-tikal-path"
                placeholder="C:\\Okapi\\tikal.bat"
                value={okapiTikalPath}
                onChange={(e) => setOkapiTikalPath(e.target.value)}
                disabled={!okapiEnabled || okapiBackend !== "local_tikal"}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="okapi-longhorn-url">Longhorn URL</Label>
              <Input
                id="okapi-longhorn-url"
                type="url"
                placeholder="https://longhorn.example.com"
                value={okapiLonghornUrl}
                onChange={(e) => setOkapiLonghornUrl(e.target.value)}
                disabled={!okapiEnabled || okapiBackend !== "longhorn"}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="okapi-github-repo">GitHub repo (user fork)</Label>
              <Input
                id="okapi-github-repo"
                placeholder="your-user/ldw-okapi-workflows"
                value={okapiGithubRepo}
                onChange={(e) => setOkapiGithubRepo(e.target.value)}
                disabled={!okapiEnabled || okapiBackend !== "github"}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="okapi-github-token">GitHub token (PAT)</Label>
              <Input
                id="okapi-github-token"
                type="password"
                placeholder="ghp_..."
                value={okapiGithubToken}
                onChange={(e) => setOkapiGithubToken(e.target.value)}
                disabled={!okapiEnabled || okapiBackend !== "github"}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="okapi-github-workflow">Workflow file</Label>
              <Input
                id="okapi-github-workflow"
                value={okapiGithubWorkflow}
                onChange={(e) => setOkapiGithubWorkflow(e.target.value)}
                disabled={!okapiEnabled || okapiBackend !== "github"}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="okapi-github-branch">Branch</Label>
              <Input
                id="okapi-github-branch"
                value={okapiGithubBranch}
                onChange={(e) => setOkapiGithubBranch(e.target.value)}
                disabled={!okapiEnabled || okapiBackend !== "github"}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="okapi-api-key">Hosted API Key</Label>
              <Input
                id="okapi-api-key"
                type="password"
                placeholder="Enter your Okapi API key"
                value={okapiApiKey}
                onChange={(e) => setOkapiApiKey(e.target.value)}
                disabled={!okapiEnabled || okapiBackend !== "hosted"}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="okapi-api-url">Hosted API URL</Label>
              <Input
                id="okapi-api-url"
                type="url"
                placeholder="https://api.okapi.com"
                value={okapiApiUrl}
                onChange={(e) => setOkapiApiUrl(e.target.value)}
                disabled={!okapiEnabled || okapiBackend !== "hosted"}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="okapi-workspace-id">Hosted Workspace ID</Label>
              <Input
                id="okapi-workspace-id"
                placeholder="Enter your workspace ID"
                value={okapiWorkspaceId}
                onChange={(e) => setOkapiWorkspaceId(e.target.value)}
                disabled={!okapiEnabled || okapiBackend !== "hosted"}
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

