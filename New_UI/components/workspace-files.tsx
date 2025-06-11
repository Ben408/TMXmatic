"use client"

import type { WorkspaceFile } from "./tmx-workspace"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Download, Trash2, CheckCircle, Clock, AlertCircle, FileIcon } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"

export interface WorkspaceFilesProps {
  files: WorkspaceFile[]
  selectedFileIds: string[]
  onSelectFile: (fileId: string, multiSelect?: boolean) => void
  onRemoveFile: (id: string) => void
  onDownloadFile: (fileId: string) => Promise<void>
}

export function WorkspaceFiles({
  files,
  selectedFileIds,
  onSelectFile,
  onRemoveFile,
  onDownloadFile,
}: WorkspaceFilesProps) {
  if (files.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Workspace Files</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-center text-muted-foreground">
            <p>No files in workspace yet. Upload files to get started.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Workspace Files ({files.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[250px] pr-4">
          <div className="space-y-2">
            {files.map((file) => (
              <div
                key={file.id}
                className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                  selectedFileIds.includes(file.id)
                    ? "bg-primary/10 border-primary"
                    : "hover:bg-muted/50"
                }`}
                onClick={(e) => {
                  // Use Ctrl/Cmd + Click for multi-select
                  const multiSelect = e.ctrlKey || e.metaKey
                  onSelectFile(file.id, multiSelect)
                }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">{file.name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {(file.size / 1024).toFixed(2)} KB • {getFileTypeLabel(file.name)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation()
                        onRemoveFile(file.id)
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                {file.status === "processing" && (
                  <div className="mt-2 text-sm text-muted-foreground">Processing...</div>
                )}
                {file.status === "error" && (
                  <div className="mt-2 text-sm text-destructive">
                    {file.operations[file.operations.length - 1]?.errorMessage || "An error occurred"}
                  </div>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}

function getFileTypeLabel(filename: string): string {
  const extension = filename.split(".").pop()?.toLowerCase()
  switch (extension) {
    case "tmx":
      return "TMX File"
    case "xlsx":
    case "xls":
      return "Excel File"
    case "xliff":
    case "xlf":
      return "XLIFF File"
    case "csv":
      return "CSV File"
    default:
      return extension ? `${extension.toUpperCase()} File` : "Unknown File"
  }
}

function StatusIcon({ status }: { status: WorkspaceFile["status"] }) {
  switch (status) {
    case "idle":
      return <Clock className="h-5 w-5 text-muted-foreground" />
    case "processing":
      return <Clock className="h-5 w-5 text-amber-500 animate-pulse" />
    case "processed":
      return <CheckCircle className="h-5 w-5 text-green-500" />
    case "error":
      return <AlertCircle className="h-5 w-5 text-red-500" />
    default:
      return null
  }
}

