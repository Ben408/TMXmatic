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
import { Badge } from "@/components/ui/badge"

const OKAPI_WORKFLOWS_FORK_URL = "https://github.com/Ben408/ldw-okapi-workflows/fork"
const BLOCKED_GITHUB_REPOS = new Set(["ben408/tmxmatic", "ben408/ldw-okapi-workflows"])

function validateGithubRepoClient(repo: string): string | null {
  const normalized = repo.trim()
  if (!normalized) {
    return "Enter your organization's fork (for example your-company/ldw-okapi-workflows)."
  }
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(normalized)) {
    return "Repository must look like owner/name."
  }
  if (BLOCKED_GITHUB_REPOS.has(normalized.toLowerCase())) {
    return "Use your own fork of the workflow template — not the main TMXmatic app or the upstream template repo."
  }
  return null
}

type OkapiTestIntegration = "okapi" | "okapi_docker" | "okapi_github" | "okapi_longhorn" | "okapi_local_tikal"

type BackendStatusRow = {
  backend: string
  available: boolean
  message: string
  active: boolean
}

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
  const [showGithubAdvanced, setShowGithubAdvanced] = useState(false)
  const [connectionDialogOpen, setConnectionDialogOpen] = useState(false)
  const [connectionResult, setConnectionResult] = useState<ConnectionTestResult | null>(null)
  const [currentTestIntegration, setCurrentTestIntegration] = useState<string>("")
  const [backendStatuses, setBackendStatuses] = useState<BackendStatusRow[]>([])
  const [activeBackendId, setActiveBackendId] = useState("docker")
  const [loadingBackends, setLoadingBackends] = useState(false)

  // Load settings on mount
  useEffect(() => {
    loadSettings()
  }, [])

  useEffect(() => {
    setIsMounted(true)
  }, [])

  const loadBackendStatuses = async () => {
    try {
      setLoadingBackends(true)
      const response = await fetch("http://127.0.0.1:5000/api/okapi/backends/status", { cache: "no-store" })
      if (!response.ok) return
      const data = await response.json()
      setBackendStatuses(data.backends || [])
      setActiveBackendId(data.active_backend || "docker")
    } catch (error) {
      console.error("backend status load failed", error)
    } finally {
      setLoadingBackends(false)
    }
  }

  useEffect(() => {
    if (okapiEnabled) {
      loadBackendStatuses()
    }
  }, [okapiEnabled, okapiBackend])

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

  const buildOkapiPayload = () => ({
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
  })

  const handleSave = async () => {
    if (okapiEnabled && okapiBackend === "github" && okapiGithubRepo.trim()) {
      const repoError = validateGithubRepoClient(okapiGithubRepo)
      if (repoError) {
        toast({ title: "GitHub repository not allowed", description: repoError, variant: "destructive" })
        return
      }
    }
    try {
      setSaving(true)
      const response = await fetch('http://127.0.0.1:5000/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          okapi: buildOkapiPayload(),
        }),
      })

      if (response.ok) {
        toast({
          title: "Success",
          description: "Settings saved successfully",
        })
        loadBackendStatuses()
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

  const runConnectionTest = async (
    integration: OkapiTestIntegration,
    label: string,
    validate?: () => string | null,
  ) => {
    if (validate) {
      const validationError = validate()
      if (validationError) {
        setConnectionResult({ success: false, message: validationError })
        setConnectionDialogOpen(true)
        setCurrentTestIntegration(label)
        return
      }
    }

    const okapiPayload = buildOkapiPayload()
    if (integration === "okapi") {
      okapiPayload.enabled = true
    }

    try {
      setTestingOkapi(true)
      const response = await fetch('http://127.0.0.1:5000/api/settings/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ integration, okapi: okapiPayload }),
      })
      const data = await response.json()
      setConnectionResult({
        success: data.success || false,
        message: data.message || (data.success ? "Connection successful" : "Connection failed"),
        statusCode: data.status_code,
        error: data.error,
      })
      setCurrentTestIntegration(label)
      setConnectionDialogOpen(true)
    } catch (error) {
      setConnectionResult({
        success: false,
        message: "Failed to test connection",
        error: error instanceof Error ? error.message : "Unknown error",
      })
      setCurrentTestIntegration(label)
      setConnectionDialogOpen(true)
    } finally {
      setTestingOkapi(false)
    }
  }

  const testHostedConnection = () =>
    runConnectionTest("okapi", "Hosted Okapi workspace", () => {
      if (!okapiApiKey || !okapiApiUrl || !okapiWorkspaceId) {
        return "Fill in API key, API URL, and workspace ID first."
      }
      return null
    })

  const testDockerBackend = () => runConnectionTest("okapi_docker", "Docker tikal")

  const testGithubBackend = () =>
    runConnectionTest("okapi_github", "GitHub Actions", () => {
      if (!okapiGithubToken.trim()) {
        return "Add a GitHub personal access token with repo and workflow permissions."
      }
      return validateGithubRepoClient(okapiGithubRepo)
    })

  const testLonghornBackend = () =>
    runConnectionTest("okapi_longhorn", "Longhorn (beta)", () => {
      if (!okapiLonghornUrl.trim()) {
        return "Enter your Longhorn base URL (for example http://localhost:8080/okapi-longhorn)."
      }
      return null
    })

  const testLocalTikalBackend = () => runConnectionTest("okapi_local_tikal", "Local tikal")

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
                  Convert and pipeline processing (Docker on this PC, or your organization&apos;s GitHub fork)
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
                  <SelectItem value="docker">Docker tikal (recommended on this PC)</SelectItem>
                  <SelectItem value="github">GitHub Actions (your organization&apos;s fork)</SelectItem>
                  <SelectItem value="hosted">Hosted Okapi workspace</SelectItem>
                  <SelectItem value="longhorn">Longhorn server (beta)</SelectItem>
                  <SelectItem value="local_tikal">Local tikal (IT only — not recommended)</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Jobs always run in the backend you choose here. LDW never uses a shared TMXmatic GitHub Actions queue.
              </p>
            </div>

            {okapiEnabled && (
              <div className="rounded-lg border bg-muted/20 p-4 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <Label>Backend health</Label>
                  <Button variant="ghost" size="sm" onClick={loadBackendStatuses} disabled={loadingBackends}>
                    {loadingBackends ? <Loader2 className="h-3 w-3 animate-spin" /> : "Refresh"}
                  </Button>
                </div>
                <p className="text-sm text-muted-foreground">
                  Active backend: <strong>{activeBackendId}</strong>
                </p>
                <div className="flex flex-wrap gap-2">
                  {backendStatuses.map((row) => (
                    <Badge
                      key={row.backend}
                      variant={row.available ? "default" : "secondary"}
                      title={row.message}
                    >
                      {row.backend === "longhorn" ? "longhorn (beta)" : row.backend}:{" "}
                      {row.available ? "ready" : "off"}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {okapiEnabled && okapiBackend === "docker" && (
              <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
                <p className="text-sm font-medium">Docker tikal on this computer</p>
                <p className="text-sm text-muted-foreground">
                  One-time setup: install Docker Desktop, then run{" "}
                  <code className="text-xs">scripts\build_okapi_tikal_image.ps1</code> from the LDW install folder.
                </p>
                <div className="space-y-2">
                  <Label htmlFor="okapi-docker-image">Docker image name</Label>
                  <Input
                    id="okapi-docker-image"
                    placeholder="ldw-okapi-tikal:1.48"
                    value={okapiDockerImage}
                    onChange={(e) => setOkapiDockerImage(e.target.value)}
                  />
                </div>
                <Button variant="outline" onClick={testDockerBackend} disabled={testingOkapi} className="w-full">
                  {testingOkapi ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <Wifi className="mr-2 h-4 w-4" />
                      Test Docker tikal
                    </>
                  )}
                </Button>
              </div>
            )}

            {okapiEnabled && okapiBackend === "github" && (
              <div className="rounded-lg border bg-muted/30 p-4 space-y-4">
                <div>
                  <p className="text-sm font-medium">GitHub Actions in your organization</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Your IT team forks a small workflow repo once. You paste that fork here so files stay in your GitHub account.
                  </p>
                </div>
                <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                  <li>
                    Fork the template:{" "}
                    <a
                      href={OKAPI_WORKFLOWS_FORK_URL}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline"
                    >
                      ldw-okapi-workflows
                    </a>{" "}
                    to your company or personal GitHub (public template; your fork can be private).
                  </li>
                  <li>Create a GitHub token with <strong>repo</strong> and <strong>workflow</strong> permissions.</li>
                  <li>Enter your fork below (for example <code className="text-xs">acme-corp/ldw-okapi-workflows</code>).</li>
                </ol>
                <div className="space-y-2">
                  <Label htmlFor="okapi-github-repo">Your workflow repository</Label>
                  <Input
                    id="okapi-github-repo"
                    placeholder="your-company/ldw-okapi-workflows"
                    value={okapiGithubRepo}
                    onChange={(e) => setOkapiGithubRepo(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Do not use Ben408/TMXmatic or the upstream template repo — use a fork you control.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="okapi-github-token">GitHub personal access token</Label>
                  <Input
                    id="okapi-github-token"
                    type="password"
                    placeholder="ghp_..."
                    value={okapiGithubToken}
                    onChange={(e) => setOkapiGithubToken(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">Stored locally in integration_secrets.json on this PC.</p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="px-0 h-auto text-xs"
                  onClick={() => setShowGithubAdvanced((v) => !v)}
                >
                  {showGithubAdvanced ? "Hide advanced settings" : "Show advanced settings"}
                </Button>
                {showGithubAdvanced && (
                  <div className="space-y-3 pt-1">
                    <div className="space-y-2">
                      <Label htmlFor="okapi-github-workflow">Workflow file</Label>
                      <Input
                        id="okapi-github-workflow"
                        value={okapiGithubWorkflow}
                        onChange={(e) => setOkapiGithubWorkflow(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="okapi-github-branch">Branch</Label>
                      <Input
                        id="okapi-github-branch"
                        value={okapiGithubBranch}
                        onChange={(e) => setOkapiGithubBranch(e.target.value)}
                      />
                    </div>
                  </div>
                )}
                <Button variant="outline" onClick={testGithubBackend} disabled={testingOkapi} className="w-full">
                  {testingOkapi ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <Wifi className="mr-2 h-4 w-4" />
                      Test GitHub connection
                    </>
                  )}
                </Button>
              </div>
            )}

            {okapiEnabled && okapiBackend === "local_tikal" && (
              <div className="space-y-2">
                <Label htmlFor="okapi-tikal-path">Local tikal path</Label>
                <Input
                  id="okapi-tikal-path"
                  placeholder="C:\\Okapi\\tikal.bat"
                  value={okapiTikalPath}
                  onChange={(e) => setOkapiTikalPath(e.target.value)}
                />
                <Button variant="outline" onClick={testLocalTikalBackend} disabled={testingOkapi} className="w-full">
                  {testingOkapi ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <Wifi className="mr-2 h-4 w-4" />
                      Test local tikal
                    </>
                  )}
                </Button>
              </div>
            )}

            {okapiEnabled && okapiBackend === "longhorn" && (
              <div className="space-y-2">
                <Label htmlFor="okapi-longhorn-url">Longhorn URL</Label>
                <Input
                  id="okapi-longhorn-url"
                  type="text"
                  placeholder="http://localhost:8080/okapi-longhorn"
                  value={okapiLonghornUrl}
                  onChange={(e) => setOkapiLonghornUrl(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Stock Okapi Longhorn (beta). LDW orchestrates ephemeral Rainbow projects — not a custom gateway API.
                </p>
                <Button variant="outline" onClick={testLonghornBackend} disabled={testingOkapi} className="w-full">
                  {testingOkapi ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <Wifi className="mr-2 h-4 w-4" />
                      Test Longhorn connection
                    </>
                  )}
                </Button>
              </div>
            )}

            {okapiEnabled && okapiBackend === "hosted" && (
              <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
                <p className="text-sm font-medium">Hosted Okapi workspace API</p>
                <div className="space-y-2">
                  <Label htmlFor="okapi-api-key">API Key</Label>
                  <Input
                    id="okapi-api-key"
                    type="password"
                    placeholder="Enter your Okapi API key"
                    value={okapiApiKey}
                    onChange={(e) => setOkapiApiKey(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="okapi-api-url">API URL</Label>
                  <Input
                    id="okapi-api-url"
                    type="url"
                    placeholder="https://api.okapi.example.com"
                    value={okapiApiUrl}
                    onChange={(e) => setOkapiApiUrl(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="okapi-workspace-id">Workspace ID</Label>
                  <Input
                    id="okapi-workspace-id"
                    placeholder="Enter your workspace ID"
                    value={okapiWorkspaceId}
                    onChange={(e) => setOkapiWorkspaceId(e.target.value)}
                  />
                </div>
                <Button variant="outline" onClick={testHostedConnection} disabled={testingOkapi} className="w-full">
                  {testingOkapi ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <Wifi className="mr-2 h-4 w-4" />
                      Test hosted workspace
                    </>
                  )}
                </Button>
              </div>
            )}
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

