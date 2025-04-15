"use client"

import type { WorkspaceFile } from "./tmx-workspace"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Download, Trash2, CheckCircle, Clock, AlertCircle, FileIcon } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"

interface WorkspaceFilesProps {
  files: WorkspaceFile[]
  selectedFileId: string | null
  onSelectFile: (id: string) => void
  onRemoveFile: (id: string) => void
  onDownloadFile: (id: string) => void
}

export function WorkspaceFiles({
  files,
  selectedFileId,
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
                className={`flex items-center justify-between p-3 rounded-md cursor-pointer transition-colors ${
                  selectedFileId === file.id ? "bg-primary/10 border border-primary/20" : "hover:bg-muted"
                }`}
                onClick={() => onSelectFile(file.id)}
              >
                <div className="flex items-center space-x-3">
                  <FileIcon className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium truncate max-w-[200px] md:max-w-[300px]">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(file.size / 1024).toFixed(2)} KB • {file.operations.length} operations
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-1">
                  <StatusIcon status={file.status} />
                  <div className="flex space-x-1">
                    {file.operations.length > 0 && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation()
                          onDownloadFile(file.id)
                        }}
                      >
                        <Download className="h-4 w-4" />
                        <span className="sr-only">Download</span>
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation()
                        onRemoveFile(file.id)
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                      <span className="sr-only">Remove</span>
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
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

