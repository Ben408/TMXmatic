"use client"

import { useState, useRef, useEffect } from "react"
import type { WorkspaceFile } from "./tmx-workspace"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Download, Trash2, CheckCircle, Clock, AlertCircle, FileIcon } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { DownloadFormat, getFileTypeLabel, isTmxOrXliffFile } from "@/lib/download-utils"

export interface WorkspaceFilesProps {
  files: WorkspaceFile[]
  selectedFileIds: string[]
  onSelectFile: (fileId: string, multiSelect?: boolean) => void
  onRemoveFile: (id: string) => void
  onDownloadFile: (fileId: string, format: DownloadFormat) => Promise<void>
}

export function WorkspaceFiles({
  files,
  selectedFileIds,
  onSelectFile,
  onRemoveFile,
  onDownloadFile,
}: WorkspaceFilesProps) {
  const [height, setHeight] = useState(250)
  const [isResizing, setIsResizing] = useState(false)
  const resizeRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return
      
      const newHeight = e.clientY - (resizeRef.current?.getBoundingClientRect().top || 0)
      if (newHeight > 150 && newHeight < 600) {
        setHeight(newHeight)
      }
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing])

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
        <p className="text-sm text-muted-foreground font-normal">
          Click a file to select it for TMX operations and Okapi pipelines.
        </p>
      </CardHeader>
      <CardContent className="relative">
        <ScrollArea className="pr-4" style={{ height: `${height}px` }}>
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
                    {file.processedData &&
                      (isTmxOrXliffFile(file.name) ? (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={(e) => e.stopPropagation()}
                              title="Download file"
                            >
                              <Download className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                            <DropdownMenuItem onClick={() => onDownloadFile(file.id, "tmx")}>
                              Download as TMX
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => onDownloadFile(file.id, "xliff")}>
                              Download as XLIFF
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => onDownloadFile(file.id, "source")}>
                              Download as Source
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      ) : (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={async (e) => {
                            e.stopPropagation()
                            await onDownloadFile(file.id, "source")
                          }}
                          title="Download processed file"
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                      ))}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation()
                        onRemoveFile(file.id)
                      }}
                      title="Remove file"
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
        {/* Resize handle */}
        <div
          ref={resizeRef}
          className="absolute bottom-0 left-0 right-0 h-2 cursor-ns-resize bg-transparent hover:bg-muted/20 transition-colors"
          onMouseDown={() => setIsResizing(true)}
          style={{ cursor: 'ns-resize' }}
        >
          <div className="absolute bottom-1 left-1/2 transform -translate-x-1/2 w-8 h-0.5 bg-muted-foreground/30 rounded"></div>
        </div>
      </CardContent>
    </Card>
  )
}

