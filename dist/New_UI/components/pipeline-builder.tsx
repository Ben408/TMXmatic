"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Loader2 } from "lucide-react"
import { toast } from "@/components/ui/use-toast"
import { WorkspaceFile } from "./tmx-workspace"
import { ldwApi } from "@/lib/ldw-api"

type PipelineStep = {
  id: string
  type: string
  operation: string
  description: string
}

type CatalogStep = PipelineStep & { source: "okapi" | "python" }

export interface PipelineBuilderProps {
  files: WorkspaceFile[]
}

/** Visual pipeline builder — add Okapi + Python steps and execute via job API. */
export function PipelineBuilder({ files }: PipelineBuilderProps) {
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [catalog, setCatalog] = useState<CatalogStep[]>([])
  const [steps, setSteps] = useState<PipelineStep[]>([])
  const [running, setRunning] = useState(false)

  useEffect(() => {
    const load = async () => {
      const [opsRes, pyRes] = await Promise.all([
        fetch(ldwApi("/api/okapi/operations")),
        fetch(ldwApi("/api/okapi/python-operations")),
      ])
      const merged: CatalogStep[] = []
      if (opsRes.ok) {
        const ops = await opsRes.json()
        for (const row of ops.operations || []) {
          merged.push({
            id: row.id,
            type: "okapi",
            operation: row.id,
            description: row.description || row.label,
            source: "okapi",
          })
        }
      }
      if (pyRes.ok) {
        const py = await pyRes.json()
        for (const op of py.operations || []) {
          merged.push({
            id: `py-${op}`,
            type: "python",
            operation: op,
            description: `LDW python: ${op}`,
            source: "python",
          })
        }
      }
      setCatalog(merged)
    }
    load()
  }, [])

  const addStep = (stepId: string) => {
    const found = catalog.find((s) => s.id === stepId)
    if (!found) return
    setSteps((prev) => [
      ...prev,
      {
        id: `${found.operation}-${prev.length + 1}`,
        type: found.type,
        operation: found.operation,
        description: found.description,
      },
    ])
  }

  const removeStep = (index: number) => {
    setSteps((prev) => prev.filter((_, i) => i !== index))
  }

  const saveTemplate = async () => {
    if (!name.trim()) {
      toast({ title: "Name required", variant: "destructive" })
      return
    }
    const id = name.trim().toLowerCase().replace(/\s+/g, "_")
    const res = await fetch(ldwApi("/api/pipeline-templates"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, name, description, category: "custom", steps }),
    })
    if (!res.ok) {
      const err = await res.json()
      toast({ title: "Save failed", description: err.error, variant: "destructive" })
      return
    }
    toast({ title: "Template saved", description: id })
  }

  const executePipeline = async () => {
    if (files.length === 0 || steps.length === 0) return
    setRunning(true)
    try {
      const form = new FormData()
      form.append("file", files[0].originalData, files[0].name)
      form.append("steps_json", JSON.stringify(steps))
      const res = await fetch(ldwApi("/api/execute-pipeline"), { method: "POST", body: form })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || res.statusText)
      }
      const body = await res.json()
      const jobId = body.job.id
      let status = "queued"
      const deadline = Date.now() + 120_000
      while (status !== "completed" && Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 500))
        const poll = await fetch(ldwApi(`/api/okapi/status/${jobId}`))
        status = (await poll.json()).status
        if (status === "failed") throw new Error("pipeline job failed")
      }
      toast({ title: "Pipeline complete", description: `Job ${jobId}` })
    } catch (error) {
      toast({
        title: "Pipeline failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      })
    } finally {
      setRunning(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline builder</CardTitle>
        <CardDescription>Combine Python-native and Okapi steps in one job.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Pipeline name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="My DOCX pipeline" />
          </div>
          <div className="space-y-2">
            <Label>Description</Label>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
        </div>

        <div className="space-y-2">
          <Label>Add step</Label>
          <Select onValueChange={addStep}>
            <SelectTrigger>
              <SelectValue placeholder="Select operation" />
            </SelectTrigger>
            <SelectContent>
              {catalog.map((step) => (
                <SelectItem key={step.id} value={step.id}>
                  [{step.source}] {step.operation}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>Steps</Label>
          {steps.length === 0 && (
            <p className="text-sm text-muted-foreground">No steps yet.</p>
          )}
          {steps.map((step, index) => (
            <div key={`${step.id}-${index}`} className="flex items-center gap-2 rounded border p-2 text-sm">
              <span className="flex-1">
                {index + 1}. [{step.type}] {step.operation}
              </span>
              <Button variant="outline" size="sm" onClick={() => removeStep(index)}>
                Remove
              </Button>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={saveTemplate} disabled={steps.length === 0}>
            Save template
          </Button>
          <Button onClick={executePipeline} disabled={running || files.length === 0 || steps.length === 0}>
            {running ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running…
              </>
            ) : (
              "Execute pipeline"
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
