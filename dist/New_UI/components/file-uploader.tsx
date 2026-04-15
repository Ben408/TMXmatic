"use client"

import type React from "react"

import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Upload, FileIcon, Download, Loader2 } from "lucide-react"
import { useIntegrationSettings } from "@/components/integration-settings-context"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Checkbox } from "@/components/ui/checkbox"
import { ScrollArea } from "@/components/ui/scroll-area"
import { toast } from "@/components/ui/use-toast"
import { Input } from "@/components/ui/input"

type SourceProject = {
  integration: "okapi"
  projectId?: string
  workspaceId?: string
  fileId?: string
}

interface FileUploaderProps {
  onFilesAdded: (files: File[], sourceProject?: SourceProject | SourceProject[]) => void
}

type ProjectFile = { id: string; name: string; size?: number }

export function FileUploader({ onFilesAdded }: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { settings } = useIntegrationSettings()

  const [pullDialogOpen, setPullDialogOpen] = useState(false)
  const [pullDialogFiles, setPullDialogFiles] = useState<ProjectFile[]>([])
  const [pullDialogIntegration, setPullDialogIntegration] = useState<"okapi" | null>(null)
  const [pullDialogWorkspaceId, setPullDialogWorkspaceId] = useState<string | null>(null)
  const [pullDialogProjectId, setPullDialogProjectId] = useState<string | null>(null)
  const [selectedPullFileIds, setSelectedPullFileIds] = useState<Set<string>>(new Set())
  const [pullListLoading, setPullListLoading] = useState(false)
  const [pullButtonLoading, setPullButtonLoading] = useState(false)
  const [pullSearch, setPullSearch] = useState("")

  const filteredPullFiles = pullDialogFiles.filter((f) => {
    if (!pullSearch.trim()) return true
    const q = pullSearch.toLowerCase()
    return f.name.toLowerCase().includes(q) || f.id.toLowerCase().includes(q)
  })

  const hasIntegration = settings?.okapi?.enabled && settings?.okapi?.api_key && settings?.okapi?.workspace_id

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    if (e.dataTransfer.files.length > 0) {
      const filesArray = Array.from(e.dataTransfer.files)
      const validFiles = filesArray.filter((file) => {
        const extension = file.name.split(".").pop()?.toLowerCase()
        return ["tbx", "tmx", "xlsx", "xls", "csv", "xliff", "xlf", "zip"].includes(extension || "")
      })

      if (validFiles.length > 0) {
        onFilesAdded(validFiles)
      }
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files)
      const validFiles = filesArray.filter((file) => {
        const extension = file.name.split(".").pop()?.toLowerCase()
        return ["tbx", "tmx", "xlsx", "xls", "csv", "xliff", "xlf", "zip"].includes(extension || "")
      })

      if (validFiles.length > 0) {
        onFilesAdded(validFiles)
      }

      // Reset the input so the same file can be uploaded again if needed
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    }
  }

  const handleButtonClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click()
    }
  }

  const handlePullFromProject = async () => {
    try {
      const settingsResponse = await fetch('http://127.0.0.1:5000/api/settings', { cache: 'no-store' })
      if (!settingsResponse.ok) {
        toast({ title: "Error", description: "Failed to load settings.", variant: "destructive" })
        return
      }
      const settings = await settingsResponse.json()
      let integration: "okapi" | null = null
      let workspaceId: string | undefined
      if (settings.okapi?.enabled && settings.okapi?.api_key && settings.okapi?.workspace_id) {
        integration = "okapi"
        workspaceId = settings.okapi.workspace_id
      } else {
        toast({ title: "No integration", description: "Configure Okapi in Settings first.", variant: "destructive" })
        return
      }
      setPullListLoading(true)
      setPullDialogOpen(true)
      setPullDialogFiles([])
      setSelectedPullFileIds(new Set())
      const pullResponse = await fetch('http://127.0.0.1:5000/api/pull-from-project', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ integration, workspace_id: workspaceId }),
      })
      if (!pullResponse.ok) {
        const err = await pullResponse.json()
        setPullDialogOpen(false)
        toast({ title: "Error", description: err.error || "Failed to list files", variant: "destructive" })
        return
      }
      const result = await pullResponse.json()
      const fileList: ProjectFile[] = (result.files || [])
        .map((f: { id?: string; file_id?: string; name?: string; filename?: string; size?: number }) => ({
          id: f.id ?? f.file_id ?? "",
          name: f.name ?? f.filename ?? "Unnamed",
          size: f.size,
        }))
        .filter((f: ProjectFile) => f.id)
      setPullDialogFiles(fileList)
      setPullDialogIntegration(integration)
      setPullDialogWorkspaceId(workspaceId ?? null)
      setPullDialogProjectId(null)
      setSelectedPullFileIds(new Set(fileList.map((f) => f.id)))
    } catch (error) {
      setPullDialogOpen(false)
      toast({ title: "Error", description: "Failed to load project files.", variant: "destructive" })
    } finally {
      setPullListLoading(false)
    }
  }

  const togglePullFileSelection = (id: string) => {
    setSelectedPullFileIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectAllPullFiles = (checked: boolean) => {
    if (checked) setSelectedPullFileIds(new Set(filteredPullFiles.map((f) => f.id)))
    else setSelectedPullFileIds(new Set())
  }

  const handleConfirmPull = async () => {
    if (!pullDialogIntegration || selectedPullFileIds.size === 0) return
    const workspaceId = pullDialogWorkspaceId ?? undefined
    const projectId = pullDialogProjectId ?? undefined
    setPullButtonLoading(true)
    try {
      const files: File[] = []
      const sourceProjects: SourceProject[] = []
      for (const fileId of selectedPullFileIds) {
        const meta = pullDialogFiles.find((f) => f.id === fileId)
        const name = meta?.name ?? "download"
        const res = await fetch('http://127.0.0.1:5000/api/download-from-project', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            integration: pullDialogIntegration,
            workspace_id: workspaceId,
            project_id: projectId,
            file_id: fileId,
            file_name: name,
          }),
        })
        if (!res.ok) {
          const err = await res.json()
          toast({ title: "Download failed", description: err.error || name, variant: "destructive" })
          continue
        }
        const blob = await res.blob()
        files.push(new File([blob], name, { type: blob.type || "application/octet-stream" }))
        sourceProjects.push({
          integration: pullDialogIntegration,
          workspaceId,
          projectId,
          fileId,
        })
      }
      if (files.length > 0) {
        onFilesAdded(files, sourceProjects)
        setPullDialogOpen(false)
        toast({ title: "Files added", description: `${files.length} file(s) pulled into workspace` })
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to download some files.", variant: "destructive" })
    } finally {
      setPullButtonLoading(false)
    }
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Drag and Drop Section */}
      <Card
        className={`border-2 border-dashed ${isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/20"} transition-colors duration-200`}
      >
        <CardContent className="p-6">
          <div
            className="flex flex-col items-center justify-center py-6 text-center"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="mb-4 rounded-full bg-primary/10 p-4">
              <Upload className="h-8 w-8 text-primary" />
            </div>
            <h3 className="mb-2 text-lg font-semibold">Drag and drop your files</h3>
            <p className="mb-4 text-sm text-muted-foreground">Upload TMX, Excel, CSV, or XLIFF files</p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".tbx,.tmx,.xlsx,.xls,.csv,.xliff,.xlf,.zip"
              className="hidden"
              onChange={handleFileInputChange}
            />
            <Button onClick={handleButtonClick} variant="outline">
              <FileIcon className="mr-2 h-4 w-4" />
              Select Files
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Pull from Project Section */}
      <Card className="border-2 border-dashed border-muted-foreground/20 transition-colors duration-200">
        <CardContent className="p-6">
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <div className="mb-4 rounded-full bg-primary/10 p-4">
              <Download className="h-8 w-8 text-primary" />
            </div>
            <h3 className="mb-2 text-lg font-semibold">Pull from project</h3>
            <p className="mb-4 text-sm text-muted-foreground">
              {hasIntegration
                ? "Import files from your connected projects"
                : "Connect Okapi in Settings to pull files"}
            </p>
            <Button onClick={handlePullFromProject} variant="outline" disabled={!hasIntegration}>
              <Download className="mr-2 h-4 w-4" />
              Pull Files
            </Button>
          </div>
        </CardContent>
      </Card>

      <Dialog open={pullDialogOpen} onOpenChange={setPullDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Pull from project</DialogTitle>
            <DialogDescription>
              Select files to add to your workspace. They will appear in the workspace file list.
            </DialogDescription>
          </DialogHeader>
          {pullListLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <>
              <div className="px-2 py-2">
                <Input
                  placeholder="Search files..."
                  value={pullSearch}
                  onChange={(e) => setPullSearch(e.target.value)}
                  className="h-8 text-sm"
                />
              </div>
              {pullDialogFiles.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4">No files in this project.</p>
              ) : (
                <>
                  <div className="flex items-center gap-2 py-2 border-b">
                    <Checkbox
                      id="pull-select-all"
                      checked={
                        filteredPullFiles.length > 0 &&
                        filteredPullFiles.every((f) => selectedPullFileIds.has(f.id))
                      }
                      onCheckedChange={(c) => selectAllPullFiles(c === true)}
                    />
                    <label htmlFor="pull-select-all" className="text-sm font-medium cursor-pointer">
                      Select all
                    </label>
                  </div>
                  <ScrollArea className="max-h-[280px] rounded-md border">
                    <div className="p-2 space-y-1">
                      {filteredPullFiles.length === 0 ? (
                        <p className="text-sm text-muted-foreground px-2 py-2">
                          No files match your search.
                        </p>
                      ) : (
                        filteredPullFiles.map((f) => (
                          <div
                            key={f.id}
                            className="flex items-center gap-2 rounded-sm px-2 py-1.5 hover:bg-muted/50"
                          >
                            <Checkbox
                              id={`pull-${f.id}`}
                              checked={selectedPullFileIds.has(f.id)}
                              onCheckedChange={() => togglePullFileSelection(f.id)}
                            />
                            <label
                              htmlFor={`pull-${f.id}`}
                              className="flex-1 text-sm cursor-pointer truncate"
                              title={f.name}
                            >
                              {f.name}
                              {f.size != null && (
                                <span className="text-muted-foreground ml-1">
                                  ({(f.size / 1024).toFixed(1)} KB)
                                </span>
                              )}
                            </label>
                          </div>
                        ))
                      )}
                    </div>
                  </ScrollArea>
                </>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={() => setPullDialogOpen(false)}>
                  Cancel
                </Button>
                <Button
                  onClick={handleConfirmPull}
                  disabled={selectedPullFileIds.size === 0 || pullButtonLoading}
                >
                  {pullButtonLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Pulling...
                    </>
                  ) : (
                    <>Pull {selectedPullFileIds.size} file(s)</>
                  )}
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

