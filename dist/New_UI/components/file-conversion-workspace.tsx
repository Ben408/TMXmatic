"use client"

import { useState } from "react"
import { FileUploader } from "./file-uploader"
import { WorkspaceFiles } from "./workspace-files"
import { ConversionPanel } from "./conversion-panel"
import { ConversionHistory } from "./conversion-history"
import { Button } from "@/components/ui/button"
import { Download } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

export type WorkspaceFile = {
  id: string
  name: string
  type: string
  size: number
  data: File
  status: "idle" | "processing" | "processed" | "error"
  operations: ProcessingOperation[]
  relatedFiles?: {
    tmxFile?: string
    xliffFile?: string
  }
}

export type ConversionStep = {
  id: string
  operation: string
  timestamp: Date
  params?: Record<string, any>
}

export function FileConversionWorkspace() {
  const [files, setFiles] = useState<WorkspaceFile[]>([])
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)
  const { toast } = useToast()

  const selectedFile = files.find((file) => file.id === selectedFileId)

  const handleFilesAdded = (newFiles: File[]) => {
    const workspaceFiles = newFiles.map((file) => ({
      id: crypto.randomUUID(),
      name: file.name,
      type: file.type,
      size: file.size,
      data: file,
      status: "idle" as const,
      operations: [],
      relatedFiles: {},
    }))

    setFiles((prev) => [...prev, ...workspaceFiles])

    if (workspaceFiles.length > 0 && !selectedFileId) {
      setSelectedFileId(workspaceFiles[0].id)
    }

    toast({
      title: "Files added",
      description: `${newFiles.length} file(s) added to workspace`,
    })
  }

  const handleFileRemove = (id: string) => {
    setFiles((prev) => prev.filter((file) => file.id !== id))

    if (selectedFileId === id) {
      setSelectedFileId(files.length > 1 ? files[0].id : null)
    }
  }

  const handleConversion = (operation: string, params?: Record<string, any>) => {
    if (!selectedFileId) return

    // Simulate conversion process
    setFiles((prev) =>
      prev.map((file) => {
        if (file.id === selectedFileId) {
          return {
            ...file,
            status: "processing",
          }
        }
        return file
      }),
    )

    // Simulate processing time
    setTimeout(() => {
      setFiles((prev) =>
        prev.map((file) => {
          if (file.id === selectedFileId) {
            const newStep: ConversionStep = {
              id: crypto.randomUUID(),
              operation,
              timestamp: new Date(),
              params,
            }

            return {
              ...file,
              status: "processed",
              operations: [...file.operations, newStep],
            }
          }
          return file
        }),
      )

      toast({
        title: "Conversion complete",
        description: `Applied ${operation} to ${selectedFile?.name}`,
      })
    }, 1500)
  }

  const handleDownload = (fileId: string) => {
    const file = files.find((f) => f.id === fileId)
    if (!file) return

    // In a real app, you would generate the converted file here
    // For this demo, we'll just download the original file
    const url = URL.createObjectURL(file.data)
    const a = document.createElement("a")
    a.href = url
    a.download = `converted_${file.name}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast({
      title: "File downloaded",
      description: `Downloaded converted version of ${file.name}`,
    })
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <FileUploader onFilesAdded={handleFilesAdded} />

        <WorkspaceFiles
          files={files}
          selectedFileId={selectedFileId}
          onSelectFile={setSelectedFileId}
          onRemoveFile={handleFileRemove}
          onDownloadFile={handleDownload}
        />

        {selectedFile && <ConversionPanel file={selectedFile} onConvert={handleConversion} />}
      </div>

      <div className="space-y-6">
        <div className="bg-card rounded-lg border shadow-sm p-4">
          <h2 className="text-xl font-semibold mb-4">Workspace Summary</h2>
          <div className="space-y-2">
            <p>Files in workspace: {files.length}</p>
            <p>Conversions applied: {files.reduce((acc, file) => acc + file.operations.length, 0)}</p>
            {selectedFile && (
              <div className="mt-4">
                <h3 className="font-medium">Selected file:</h3>
                <p className="text-sm text-muted-foreground">{selectedFile.name}</p>
                <p className="text-sm text-muted-foreground">
                  {(selectedFile.size / 1024).toFixed(2)} KB • {selectedFile.type || "Unknown type"}
                </p>
                <Button
                  className="mt-4 w-full"
                  onClick={() => handleDownload(selectedFile.id)}
                  disabled={selectedFile.operations.length === 0}
                >
                  <Download className="mr-2 h-4 w-4" />
                  Download Result
                </Button>
              </div>
            )}
          </div>
        </div>

        {selectedFile && <ConversionHistory file={selectedFile} />}
      </div>
    </div>
  )
}

