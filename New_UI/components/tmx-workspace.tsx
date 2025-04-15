"use client"

import { useState } from "react"
import { FileUploader } from "./file-uploader"
import { WorkspaceFiles } from "./workspace-files"
import { OperationsPanel } from "./operations-panel"
import { ProcessingHistory } from "./processing-history"
import { Button } from "@/components/ui/button"
import { Download, AlertCircle } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { XLIFFStatsDialog } from "./xliff-stats-dialog"

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

export type ProcessingOperation = {
  id: string
  name: string
  timestamp: Date
  status: "completed" | "failed"
  errorMessage?: string
}

// List of available operations from the original app
export const OPERATIONS = [
  { id: "convert_vatv", name: "Convert VATV CSV" },
  { id: "convert_termweb", name: "Convert TermWeb Excel" },
  { id: "remove_empty", name: "Remove Empty Targets" },
  { id: "find_duplicates", name: "Find True Duplicates" },
  { id: "non_true_duplicates", name: "Find Non-True Duplicates" },
  { id: "clean_mt", name: "Clean TMX for MT" },
  { id: "merge_tmx", name: "Merge TMX Files" },
  { id: "split_language", name: "Split TMX by Language" },
  { id: "split_size", name: "Split TMX by Size" },
  { id: "batch_process_tms", name: "Batch Clean TMX for TMS" },
  { id: "batch_process_mt", name: "Batch Clean TMX for MT" },
  { id: "xliff_tmx_leverage", name: "Leverage TMX into XLIFF" },
  { id: "xliff_cleanup", name: "Clean XLIFF" },
  { id: "xliff_validate", name: "Validate XLIFF" },
] as const

export function TMXWorkspace() {
  const [files, setFiles] = useState<WorkspaceFile[]>([])
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)
  const [processingError, setProcessingError] = useState<string | null>(null)
  const { toast } = useToast()
  const [stats, setStats] = useState<XLIFFStats | null>(null)
  const [showStats, setShowStats] = useState(false)
  const [currentOperation, setCurrentOperation] = useState<"leverage" | "check" | null>(null)

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
      const remainingFiles = files.filter((f) => f.id !== id)
      setSelectedFileId(remainingFiles.length > 0 ? remainingFiles[0].id : null)
    }
  }

  const handleProcessOperation = async (operationId: string) => {
    if (!selectedFileId) return
    setProcessingError(null)
    setCurrentOperation(operationId === "xliff_tmx_leverage" ? "leverage" : "check")

    setFiles((prev) =>
      prev.map((file) =>
        file.id === selectedFileId ? { ...file, status: "processing" } : file
      )
    )

    try {
      const file = files.find((f) => f.id === selectedFileId)
      if (!file) throw new Error("File not found")

      const formData = new FormData()
      formData.append('file', file.data)

      if (operationId === 'xliff_tmx_leverage' && file.relatedFiles?.tmxFile) {
        const tmxFile = files.find((f) => f.id === file.relatedFiles.tmxFile)
        if (tmxFile) {
          formData.append('tmx_file', tmxFile.data)
        }
      }

      const response = await fetch(`/api/${operationId}`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`Operation failed: ${response.statusText}`)
      }

      if (operationId === 'xliff_check') {
        const statsData = await response.json()
        setStats(statsData)
        setShowStats(true)
      } else {
        const result = await response.blob()
        
        if (operationId === 'xliff_tmx_leverage') {
          const statsResponse = await fetch('/api/xliff_check', {
            method: 'POST',
            body: formData,
          })
          if (statsResponse.ok) {
            const statsData = await statsResponse.json()
            setStats(statsData)
            setShowStats(true)
          }
        }

        setFiles((prev) =>
          prev.map((file) => {
            if (file.id === selectedFileId) {
              return {
                ...file,
                status: "processed",
                operations: [
                  ...file.operations,
                  {
                    id: crypto.randomUUID(),
                    name: OPERATIONS.find((op) => op.id === operationId)?.name || operationId,
                    timestamp: new Date(),
                    status: "completed",
                  },
                ],
                data: new File([result], file.name, { type: file.type }),
              }
            }
            return file
          })
        )
      }

      toast({
        title: "Operation complete",
        description: `Successfully applied ${operationId} to ${file.name}`,
      })
    } catch (error) {
      console.error("Error processing file:", error)
      setProcessingError(error instanceof Error ? error.message : "An error occurred")

      // Update file status to error
      setFiles((prev) =>
        prev.map((file) => {
          if (file.id === selectedFileId) {
            return {
              ...file,
              status: "error",
            }
          }
          return file
        }),
      )

      toast({
        title: "Processing failed",
        description: "An error occurred while processing the file",
        variant: "destructive",
      })
    }
  }

  const handleDownloadFile = async (fileId: string) => {
    const file = files.find((f) => f.id === fileId)
    if (!file) return

    // Create download URL from the processed file data
    const url = URL.createObjectURL(file.data)
    const a = document.createElement("a")
    a.href = url
    a.download = `processed_${file.name}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast({
      title: "File downloaded",
      description: `Downloaded processed version of ${file.name}`,
    })
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <FileUploader onFilesAdded={handleFilesAdded} />

        {processingError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{processingError}</AlertDescription>
          </Alert>
        )}

        <WorkspaceFiles
          files={files}
          selectedFileId={selectedFileId}
          onSelectFile={setSelectedFileId}
          onRemoveFile={handleFileRemove}
          onDownloadFile={handleDownloadFile}
        />

        {selectedFile && (
          <OperationsPanel file={selectedFile} operations={OPERATIONS} onProcess={handleProcessOperation} />
        )}
      </div>

      <div className="space-y-6">
        <div className="bg-card rounded-lg border shadow-sm p-4">
          <h2 className="text-xl font-semibold mb-4">Workspace Summary</h2>
          <div className="space-y-2">
            <p>Files in workspace: {files.length}</p>
            <p>Operations applied: {files.reduce((acc, file) => acc + file.operations.length, 0)}</p>
            {selectedFile && (
              <div className="mt-4">
                <h3 className="font-medium">Selected file:</h3>
                <p className="text-sm text-muted-foreground">{selectedFile.name}</p>
                <p className="text-sm text-muted-foreground">
                  {(selectedFile.size / 1024).toFixed(2)} KB • {getFileTypeLabel(selectedFile.name)}
                </p>
                <Button
                  className="mt-4 w-full"
                  onClick={() => handleDownloadFile(selectedFile.id)}
                  disabled={selectedFile.operations.length === 0}
                >
                  <Download className="mr-2 h-4 w-4" />
                  Download Processed File
                </Button>
              </div>
            )}
          </div>
        </div>

        {selectedFile && <ProcessingHistory file={selectedFile} />}
      </div>

      <XLIFFStatsDialog
        isOpen={showStats}
        onClose={() => setShowStats(false)}
        stats={stats || {}}
        operation={currentOperation || "check"}
      />
    </div>
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

