"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Loader2, Download, Upload, Trash2 } from "lucide-react"
import { toast } from "@/components/ui/use-toast"
import { WorkspaceFile } from "./tmx-workspace"
import { PipelineBuilder } from "./pipeline-builder"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ldwApi } from "@/lib/ldw-api"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

type OkapiOperation = {
  id: string
  label: string
  description: string
  complexity: string
  inputs?: { formats?: string[] }
}

type PipelineTemplate = {
  id: string
  name: string
  description: string
  source?: string
  steps?: unknown[]
  category?: string
}

type BackendStatus = {
  backend: string
  available: boolean
  message: string
  active: boolean
}

export interface OkapiPanelProps {
  files: WorkspaceFile[]
  /** Total files in workspace (selected count may be zero). */
  workspaceFileCount?: number
}

/** Okapi operations + pipeline templates — Phase 2 UI (registry-driven). */
export function OkapiPanel({ files, workspaceFileCount = 0 }: OkapiPanelProps) {
  const [operations, setOperations] = useState<OkapiOperation[]>([])
  const [templates, setTemplates] = useState<PipelineTemplate[]>([])
  const [backends, setBackends] = useState<BackendStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState<string | null>(null)
  const [sourceLang, setSourceLang] = useState("en-us")
  const [targetLang, setTargetLang] = useState("fr-fr")
  const importRef = useRef<HTMLInputElement>(null)

  const langOptions = () =>
    JSON.stringify({ source_lang: sourceLang.trim() || "en-us", target_lang: targetLang.trim() || "fr-fr" })

  const loadDiscovery = useCallback(async () => {
    setLoading(true)
    try {
      const [opsRes, tplRes, backRes] = await Promise.all([
        fetch(ldwApi("/api/okapi/operations")),
        fetch(ldwApi("/api/pipeline-templates")),
        fetch(ldwApi("/api/okapi/backends/status")),
      ])
      if (opsRes.ok) {
        const opsJson = await opsRes.json()
        setOperations(opsJson.operations || [])
      }
      if (tplRes.ok) {
        const tplJson = await tplRes.json()
        setTemplates(tplJson.templates || [])
      }
      if (backRes.ok) {
        const backJson = await backRes.json()
        setBackends(backJson.backends || [])
      }
    } catch (error) {
      console.error(error)
      toast({
        title: "Okapi discovery failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadDiscovery()
  }, [loadDiscovery])

  const pollJob = async (jobId: string): Promise<boolean> => {
    const deadline = Date.now() + 120_000
    while (Date.now() < deadline) {
      const res = await fetch(ldwApi(`/api/okapi/status/${jobId}`))
      if (!res.ok) return false
      const job = await res.json()
      if (job.status === "completed") return true
      if (job.status === "failed" || job.status === "cancelled") {
        toast({
          title: "Okapi job failed",
          description: job.error || job.message,
          variant: "destructive",
        })
        return false
      }
      await new Promise((r) => setTimeout(r, 500))
    }
    return false
  }

  const downloadArtifact = async (jobId: string, name: string) => {
    const res = await fetch(ldwApi(`/api/jobs/${jobId}/artifacts/${encodeURIComponent(name)}`))
    if (!res.ok) {
      toast({ title: "Download failed", variant: "destructive" })
      return
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = name
    a.click()
    URL.revokeObjectURL(url)
  }

  const runOperation = async (operationId: string) => {
    if (files.length === 0) return
    const file = files[0]
    setRunning(operationId)
    try {
      const form = new FormData()
      form.append("file", file.originalData, file.name)
      form.append("operation", operationId)
      form.append("options_json", langOptions())
      const res = await fetch(ldwApi("/api/okapi/submit-upload"), { method: "POST", body: form })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || res.statusText)
      }
      const body = await res.json()
      const jobId = body.job.id
      const ok = await pollJob(jobId)
      if (ok) {
        const results = await fetch(ldwApi(`/api/okapi/results/${jobId}`))
        const parsed = await results.json()
        const primary = parsed.artifacts?.[0]?.name
        if (primary) await downloadArtifact(jobId, primary)
        toast({ title: "Okapi complete", description: `${operationId} finished` })
      }
    } catch (error) {
      toast({
        title: "Okapi operation failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      })
    } finally {
      setRunning(null)
    }
  }

  const runTemplate = async (templateId: string) => {
    if (files.length === 0) return
    const file = files[0]
    setRunning(templateId)
    try {
      const form = new FormData()
      form.append("file", file.originalData, file.name)
      form.append("template_id", templateId)
      form.append("options_json", langOptions())
      const res = await fetch(ldwApi("/api/pipelines/execute"), { method: "POST", body: form })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || res.statusText)
      }
      const body = await res.json()
      const ok = await pollJob(body.job.id)
      if (ok) toast({ title: "Pipeline complete", description: templateId })
    } catch (error) {
      toast({
        title: "Pipeline failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      })
    } finally {
      setRunning(null)
    }
  }

  const importTemplate = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ""
    if (!file) return
    try {
      const text = await file.text()
      const template = JSON.parse(text) as PipelineTemplate
      const res = await fetch(ldwApi("/api/pipeline-templates"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(template),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || res.statusText)
      }
      toast({ title: "Template imported", description: template.name || template.id })
      loadDiscovery()
    } catch (error) {
      toast({
        title: "Import failed",
        description: error instanceof Error ? error.message : "Invalid template JSON",
        variant: "destructive",
      })
    }
  }

  const exportTemplate = (tpl: PipelineTemplate) => {
    const blob = new Blob([JSON.stringify(tpl, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${tpl.id || "pipeline"}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const deleteTemplate = async (templateId: string) => {
    try {
      const res = await fetch(ldwApi(`/api/pipeline-templates/${encodeURIComponent(templateId)}`), {
        method: "DELETE",
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || res.statusText)
      }
      toast({ title: "Template deleted", description: templateId })
      loadDiscovery()
    } catch (error) {
      toast({
        title: "Delete failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      })
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 py-8">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Loading Okapi capabilities…</span>
        </CardContent>
      </Card>
    )
  }

  const activeBackend = backends.find((b) => b.active)

  const workspaceHint =
    files.length > 0 ? (
      <p className="text-sm text-muted-foreground">
        Input file: <span className="font-medium text-foreground">{files[0].name}</span>
        {files.length > 1 ? ` (+${files.length - 1} more selected)` : ""}
      </p>
    ) : workspaceFileCount > 0 ? (
      <p className="text-sm text-amber-700 dark:text-amber-400">
        Click a file in <strong>Workspace Files</strong> above to select it for Okapi and pipelines.
      </p>
    ) : (
      <p className="text-sm text-muted-foreground">
        Add a file using the upload area at the top of the page — pipelines reuse the same workspace
        (no separate upload here). For Tikal document tests use <strong>.docx</strong> or{" "}
        <strong>.xlsx</strong>; TMX files use the TMX Operations panel above.
      </p>
    )

  return (
    <Tabs defaultValue="operations" className="space-y-4">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="operations">Okapi ops</TabsTrigger>
        <TabsTrigger value="pipelines">Pipelines</TabsTrigger>
        <TabsTrigger value="builder">Builder</TabsTrigger>
      </TabsList>

      <Card>
        <CardContent className="pt-4">{workspaceHint}</CardContent>
      </Card>

      <TabsContent value="operations" className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Okapi backends</CardTitle>
          <CardDescription>
            Active: {activeBackend?.backend || "docker"}
            {activeBackend && !activeBackend.available && " (unavailable — check Settings)"}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {backends.map((b) => (
            <Badge key={b.backend} variant={b.available ? "default" : "secondary"} title={b.message}>
              {b.backend === "longhorn" ? "longhorn (beta)" : b.backend}: {b.available ? "ready" : "off"}
            </Badge>
          ))}
          <Button variant="outline" size="sm" onClick={loadDiscovery}>
            Refresh
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Language pair</CardTitle>
          <CardDescription>Passed to tikal as -sl / -tl on Okapi operations and pipelines.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 max-w-lg">
          <div className="space-y-1">
            <Label htmlFor="okapi-source-lang">Source</Label>
            <Input
              id="okapi-source-lang"
              value={sourceLang}
              onChange={(e) => setSourceLang(e.target.value)}
              placeholder="en-us"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="okapi-target-lang">Target</Label>
            <Input
              id="okapi-target-lang"
              value={targetLang}
              onChange={(e) => setTargetLang(e.target.value)}
              placeholder="fr-fr"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Okapi operations</CardTitle>
          <CardDescription>Convert, merge, QA, and terminology via tikal (all Okapi filters).</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          {operations.map((op) => (
            <div key={op.id} className="rounded-lg border p-3 space-y-2">
              <div className="font-medium">{op.label}</div>
              <p className="text-sm text-muted-foreground">{op.description}</p>
              <Button
                size="sm"
                disabled={files.length === 0 || running !== null}
                onClick={() => runOperation(op.id)}
              >
                {running === op.id ? (
                  <>
                    <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                    Running…
                  </>
                ) : (
                  "Run on selected file"
                )}
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      </TabsContent>

      <TabsContent value="pipelines" className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-2">
          <div>
            <CardTitle>Predefined pipelines</CardTitle>
            <CardDescription>Hybrid workflows — Okapi + Python steps from the spec templates.</CardDescription>
          </div>
          <div className="flex gap-2 shrink-0">
            <input
              ref={importRef}
              type="file"
              accept=".json,application/json"
              className="hidden"
              onChange={importTemplate}
            />
            <Button variant="outline" size="sm" onClick={() => importRef.current?.click()}>
              <Upload className="h-3 w-3 mr-1" />
              Import
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {templates.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No pipeline templates loaded — check that the Flask backend is running on port 5000,
              then click Refresh on Okapi ops.
            </p>
          ) : null}
          {templates.map((tpl) => (
            <div key={tpl.id} className="flex items-center justify-between gap-2 rounded-lg border p-3">
              <div className="min-w-0">
                <div className="font-medium flex items-center gap-2 flex-wrap">
                  {tpl.name}
                  {tpl.source === "user" ? (
                    <Badge variant="outline" className="text-xs">
                      user
                    </Badge>
                  ) : null}
                </div>
                <p className="text-sm text-muted-foreground">{tpl.description}</p>
              </div>
              <div className="flex gap-1 shrink-0">
                <Button size="sm" variant="ghost" onClick={() => exportTemplate(tpl)} title="Export JSON">
                  <Download className="h-3 w-3" />
                </Button>
                {tpl.source === "user" ? (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => deleteTemplate(tpl.id)}
                    title="Delete user template"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                ) : null}
                <Button
                  size="sm"
                  variant="outline"
                  disabled={files.length === 0 || running !== null}
                  onClick={() => runTemplate(tpl.id)}
                >
                  {running === tpl.id ? <Loader2 className="h-3 w-3 animate-spin" /> : "Execute"}
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
      </TabsContent>

      <TabsContent value="builder">
        <PipelineBuilder files={files} />
      </TabsContent>
    </Tabs>
  )
}
