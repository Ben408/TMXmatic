"use client"

import { useState, useCallback } from "react"
import { FileUploader } from "./file-uploader"
import { WorkspaceFiles } from "./workspace-files"
import { OperationsPanel } from "./operations-panel"
import { ProcessingHistory } from "./processing-history"
import { Button } from "@/components/ui/button"
import { Download, AlertCircle } from "lucide-react"
import { toast } from "@/components/ui/use-toast"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { XLIFFStatsDialog } from "./xliff-stats-dialog"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { ArrowUp, ArrowDown, Trash2 } from "lucide-react"
import { Loader2 } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export type XLIFFStats = {
  totalSegments: number
  emptyTargets: number
  percentage: number
}

export type WorkspaceFile = {
  id: string
  name: string
  type: string
  size: number
  data: File
  originalData: File
  processedData?: File
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

// Define the operation type
export type Operation = {
  id: string
  name: string
  description: string
  requiresFiles?: ("xliff" | "tmx")[]
}

// Update OPERATIONS to be mutable
export const OPERATIONS: Operation[] = [
  { 
    id: "convert_vatv", 
    name: "Convert VATV CSV",
    description: "Convert VATV CSV files to TMX format."
  },
  { 
    id: "convert_termweb", 
    name: "Convert TermWeb Excel",
    description: "Convert TermWeb Excel files to TMX format."
  },
  { 
    id: "remove_empty", 
    name: "Remove Empty Targets",
    description: "Remove translation units with empty target segments."
  },
  { 
    id: "find_duplicates", 
    name: "Find True Duplicates",
    description: "Identify and extract duplicate translation units."
  },
  { 
    id: "non_true_duplicates", 
    name: "Find Non-True Duplicates",
    description: "Find segments that are similar but not exact duplicates."
  },
  { 
    id: "clean_mt", 
    name: "Clean TMX for MT",
    description: "Clean TMX files for machine translation by removing metadata."
  },
  { 
    id: "merge_tmx", 
    name: "Merge TMX Files",
    description: "Combine multiple TMX files into a single file."
  },
  { 
    id: "split_language", 
    name: "Split TMX by Language",
    description: "Split a TMX file into separate files by language pair."
  },
  { 
    id: "split_size", 
    name: "Split TMX by Size",
    description: "Split a large TMX file into smaller files by segment count."
  },
  { 
    id: "batch_process_tms", 
    name: "Batch Clean TMX for TMS",
    description: "Apply multiple cleaning operations for TMS compatibility."
  },
  { 
    id: "batch_process_mt", 
    name: "Batch Clean TMX for MT",
    description: "Apply multiple cleaning operations for machine translation."
  },
  { 
    id: "xliff_tmx_leverage", 
    name: "Leverage TMX into XLIFF",
    description: "Apply translations from a TMX file to an XLIFF file",
    requiresFiles: ["xliff", "tmx"]
  },
  { 
    id: "xliff_cleanup", 
    name: "Clean XLIFF",
    description: "Clean XLIFF files for better compatibility."
  },
  { 
    id: "xliff_validate", 
    name: "Validate XLIFF",
    description: "Validate XLIFF files for errors and warnings."
  },
]

export function TMXWorkspace() {
  const [files, setFiles] = useState<WorkspaceFile[]>([])
  const [selectedFileIds, setSelectedFileIds] = useState<string[]>([])
  const [processingError, setProcessingError] = useState<string | null>(null)
  const [stats, setStats] = useState<XLIFFStats | null>(null)
  const [showStats, setShowStats] = useState(false)
  const [currentOperation, setCurrentOperation] = useState<"leverage" | "check" | null>(null)
  const [queuedOperations, setQueuedOperations] = useState<string[]>([])
  const [isProcessing, setIsProcessing] = useState(false)

  const selectedFiles = files.filter(file => selectedFileIds.includes(file.id))

  const handleFilesAdded = (newFiles: File[]) => {
    const workspaceFiles = newFiles.map((file) => ({
      id: crypto.randomUUID(),
      name: file.name,
      type: file.type,
      size: file.size,
      data: file,
      originalData: file,
      status: "idle" as const,
      operations: [],
      relatedFiles: {},
    }))

    setFiles((prev) => [...prev, ...workspaceFiles])

    if (workspaceFiles.length > 0 && selectedFileIds.length === 0) {
      setSelectedFileIds([workspaceFiles[0].id])
    }

    toast({
      title: "Files added",
      description: `${newFiles.length} file(s) added to workspace`,
    })
  }

  const handleFileSelect = (fileId: string, multiSelect: boolean = false) => {
    setSelectedFileIds(prev => {
      if (multiSelect) {
        return prev.includes(fileId) 
          ? prev.filter(id => id !== fileId)
          : [...prev, fileId]
      } else {
        return [fileId]
      }
    })
  }

  const handleFileRemove = (id: string) => {
    setFiles((prev) => prev.filter((file) => file.id !== id))
    setSelectedFileIds(prev => prev.filter(fileId => fileId !== id))
  }

  const handleProcessOperation = async (operationId: string, size?: number) => {
    if (selectedFileIds.length === 0) return
    setProcessingError(null)
    setCurrentOperation(operationId === "xliff_tmx_leverage" ? "leverage" : "check")

    // Update status for all selected files
    setFiles((prev) =>
      prev.map((file) =>
        selectedFileIds.includes(file.id)
          ? { ...file, status: "processing" }
          : file
      )
    )

    try {
      // Process each file
      for (const fileId of selectedFileIds) {
        const file = files.find(f => f.id === fileId)
        if (!file) continue

        const formData = new FormData()
        formData.append('file', file.originalData)
        
        // If this is a queue operation, send all operations in order
        if (queuedOperations.length > 0) {
          formData.append('operations', JSON.stringify(queuedOperations))
        } else {
          formData.append('operation', operationId)
        }

        if (operationId === 'xliff_tmx_leverage' && file.relatedFiles?.tmxFile) {
          const tmxFile = files.find((f) => f.id === file.relatedFiles?.tmxFile)
          if (tmxFile) {
            formData.append('tmx_file', tmxFile.originalData)
          } else {
            throw new Error("TMX file not found")
          }
        }

        if (operationId === 'split_size' && size) {
          formData.append('size', size.toString())
        }

        console.log(`Sending request to /api/${operationId}`, {
          operations: queuedOperations.length > 0 ? queuedOperations : [operationId],
          file: file.name,
          hasTmxFile: operationId === 'xliff_tmx_leverage' && !!file.relatedFiles?.tmxFile,
          size: size
        })

        const response = await fetch(
          queuedOperations.length > 0 
            ? `http://127.0.0.1:5000/queue/`
            : `http://127.0.0.1:5000/`,
          {
            method: 'POST',
            body: formData,
          }
        )

        if (!response.ok) {
          const errorText = await response.text()
          console.error(`API Error: ${response.status} ${response.statusText}`, errorText)
          throw new Error(`Operation failed: ${response.statusText} - ${errorText}`)
        }

        if (operationId === 'xliff_check') {
          const statsData = await response.json() as XLIFFStats
          setStats(statsData)
          setShowStats(true)
        } else {
          const result = await response.blob()
          
          if (operationId === 'xliff_tmx_leverage') {
            try {
              const statsResponse = await fetch('http://127.0.0.1:5000/api/xliff_check', {
                method: 'POST',
                body: formData,
              })
              if (statsResponse.ok) {
                const statsData = await statsResponse.json() as XLIFFStats
                setStats(statsData)
                setShowStats(true)
              } else {
                console.warn('Failed to get XLIFF stats after leverage operation')
              }
            } catch (statsError) {
              console.warn('Error getting XLIFF stats:', statsError)
            }
          }

          setFiles((prev) =>
            prev.map((f) => {
              if (f.id === fileId) {
                const processedFile = new File([result], f.name, { type: f.type })
                return {
                  ...f,
                  status: "processed",
                  processedData: processedFile,
                  operations: [
                    ...f.operations,
                    {
                      id: crypto.randomUUID(),
                      name: queuedOperations.length > 0 
                        ? `Queue: ${queuedOperations.map(op => OPERATIONS.find(o => o.id === op)?.name).join(' → ')}`
                        : OPERATIONS.find((op) => op.id === operationId)?.name || operationId,
                      timestamp: new Date(),
                      status: "completed",
                    },
                  ],
                }
              }
              return f
            })
          )
        }
      }

      toast({
        title: "Operation complete",
        description: queuedOperations.length > 0
          ? `Successfully processed queue of ${queuedOperations.length} operation(s)`
          : `Successfully processed ${selectedFileIds.length} file(s)`,
      })
    } catch (error) {
      console.error("Error processing files:", error)
      const errorMessage = error instanceof Error ? error.message : "An error occurred"
      setProcessingError(errorMessage)

      // Update status for all selected files
      setFiles((prev) =>
        prev.map((file) => {
          if (selectedFileIds.includes(file.id)) {
            return {
              ...file,
              status: "error",
              operations: [
                ...file.operations,
                {
                  id: crypto.randomUUID(),
                  name: queuedOperations.length > 0 
                    ? `Queue: ${queuedOperations.map(op => OPERATIONS.find(o => o.id === op)?.name).join(' → ')}`
                    : OPERATIONS.find((op) => op.id === operationId)?.name || operationId,
                  timestamp: new Date(),
                  status: "failed",
                  errorMessage,
                },
              ],
            }
          }
          return file
        }),
      )

      toast({
        title: "Processing failed",
        description: errorMessage,
        variant: "destructive",
      })
    }
  }

  const handleDownloadFile = async (fileId: string) => {
    const file = files.find((f) => f.id === fileId)
    if (!file || !file.processedData) return

    // Create download URL from the processed file data
    const url = URL.createObjectURL(file.processedData)
    const a = document.createElement("a")
    a.href = url
    a.download = `processed_files.zip`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast({
      title: "File downloaded",
      description: `Downloaded processed version of ${file.name}`,
    })
  }

  const handleBulkDownload = async () => {
    const processedFiles = files.filter(file => file.processedData)
    if (processedFiles.length === 0) return

    // Create a zip file using the browser's built-in capabilities
    const zip = new Blob(
      processedFiles.map(file => file.processedData as Blob).filter(Boolean),
      { type: 'application/zip' }
    )

    // Download the zip file
    const url = URL.createObjectURL(zip)
    const a = document.createElement("a")
    a.href = url
    a.download = "processed_files.zip"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast({
      title: "Files downloaded",
      description: `Downloaded ${processedFiles.length} processed file(s)`,
    })
  }

  const handleDownloadAll = async () => {
    const zip = new Blob(
      files.map(file => file.processedData || file.data),
      { type: 'application/zip' }
    )
    const url = URL.createObjectURL(zip)
    const a = document.createElement("a")
    a.href = url
    a.download = "all_files.zip"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleMoveOperation = (index: number, direction: 'up' | 'down') => {
    const newQueue = [...queuedOperations]
    if (direction === 'up') {
      if (index > 0) {
        [newQueue[index], newQueue[index - 1]] = [newQueue[index - 1], newQueue[index]]
      }
    } else {
      if (index < queuedOperations.length - 1) {
        [newQueue[index], newQueue[index + 1]] = [newQueue[index + 1], newQueue[index]]
      }
    }
    setQueuedOperations(newQueue)
  }

  const handleRemoveFromQueue = (index: number) => {
    setQueuedOperations(prev => {
      const newQueue = [...prev]
      newQueue.splice(index, 1)
      return newQueue
    })
  }

  const handleProcessQueue = async () => {
    if (queuedOperations.length === 0) return
    setIsProcessing(true)
    setProcessingError(null)

    try {
      // Process each file with the entire queue
      for (const fileId of selectedFileIds) {
        const file = files.find(f => f.id === fileId)
        if (!file) continue

        const formData = new FormData()
        formData.append('file', file.originalData)
        formData.append('operations', JSON.stringify(queuedOperations))

        console.log(`Sending queue request to /queue/`, {
          operations: queuedOperations,
          file: file.name
        })

        const response = await fetch(`http://127.0.0.1:5000/queue/`, {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          const errorText = await response.text()
          console.error(`API Error: ${response.status} ${response.statusText}`, errorText)
          throw new Error(`Queue processing failed: ${response.statusText} - ${errorText}`)
        }

        const result = await response.blob()
        
        setFiles((prev) =>
          prev.map((f) => {
            if (f.id === fileId) {
              const processedFile = new File([result], f.name, { type: f.type })
              return {
                ...f,
                status: "processed",
                processedData: processedFile,
                operations: [
                  ...f.operations,
                  {
                    id: crypto.randomUUID(),
                    name: `Queue: ${queuedOperations.map(op => OPERATIONS.find(o => o.id === op)?.name).join(' → ')}`,
                    timestamp: new Date(),
                    status: "completed",
                  },
                ],
              }
            }
            return f
          })
        )
      }

      toast({
        title: "Queue processed",
        description: `Successfully processed queue of ${queuedOperations.length} operation(s)`,
      })
    } catch (error) {
      console.error("Error processing queue:", error)
      const errorMessage = error instanceof Error ? error.message : "An error occurred"
      setProcessingError(errorMessage)

      // Update status for all selected files
      setFiles((prev) =>
        prev.map((file) => {
          if (selectedFileIds.includes(file.id)) {
            return {
              ...file,
              status: "error",
              operations: [
                ...file.operations,
                {
                  id: crypto.randomUUID(),
                  name: `Queue: ${queuedOperations.map(op => OPERATIONS.find(o => o.id === op)?.name).join(' → ')}`,
                  timestamp: new Date(),
                  status: "failed",
                  errorMessage,
                },
              ],
            }
          }
          return file
        }),
      )

      toast({
        title: "Processing failed",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setIsProcessing(false)
    }
  }

  const handleFileUpdate = (fileId: string, updates: Partial<WorkspaceFile>) => {
    setFiles(prev => prev.map(f => 
      f.id === fileId ? { ...f, ...updates } : f
    ))
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
          selectedFileIds={selectedFileIds}
          onSelectFile={handleFileSelect}
          onRemoveFile={handleFileRemove}
          onDownloadFile={handleDownloadFile}
        />

        {selectedFiles.length > 0 && (
          <OperationsPanel
            files={selectedFiles}
            operations={OPERATIONS}
            onProcess={handleProcessOperation}
            allFiles={files}
            onFileUpdate={handleFileUpdate}
            queuedOperations={queuedOperations}
            onQueueUpdate={setQueuedOperations}
          />
        )}
      </div>

      <div className="space-y-6">
        <div className="bg-card rounded-lg border shadow-sm p-4">
          <h2 className="text-xl font-semibold mb-4">Workspace Summary</h2>
          <div className="space-y-2">
            <p>Files in workspace: {files.length}</p>
            <p>Selected files: {selectedFileIds.length}</p>
            <p>Operations applied: {files.reduce((acc, file) => acc + file.operations.length, 0)}</p>
            {files.some(file => file.processedData) && (
              <Button
                className="w-full mt-4"
                onClick={handleBulkDownload}
              >
                <Download className="mr-2 h-4 w-4" />
                Download All Processed Files
              </Button>
            )}
            {selectedFiles.length > 0 && (
              <div className="mt-4">
                <h3 className="font-medium">Selected files:</h3>
                {selectedFiles.map(file => (
                  <div key={file.id} className="mt-2">
                    <p className="text-sm text-muted-foreground">{file.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {(file.size / 1024).toFixed(2)} KB • {getFileTypeLabel(file.name)}
                    </p>
                    <Button
                      className="mt-2 w-full"
                      onClick={() => handleDownloadFile(file.id)}
                      disabled={!file.processedData}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Download Processed File
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {selectedFiles.length > 0 && selectedFiles.map(file => (
          <ProcessingHistory key={file.id} file={file} />
        ))}

        {queuedOperations.length > 0 && (
          <div className="bg-card rounded-lg border shadow-sm p-4">
            <h2 className="text-xl font-semibold mb-4">Operation Queue</h2>
            <div className="space-y-2">
              {queuedOperations.map((operationId, index) => {
                const operation = OPERATIONS.find(op => op.id === operationId)
                if (!operation) return null

                return (
                  <div
                    key={`${operationId}-${index}`}
                    className="flex items-center gap-2 p-2 rounded-lg border bg-card"
                  >
                    <div className="flex flex-col gap-0">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => handleMoveOperation(index, 'up')}
                        disabled={index === 0}
                      >
                        <ArrowUp className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => handleMoveOperation(index, 'down')}
                        disabled={index === queuedOperations.length - 1}
                      >
                        <ArrowDown className="h-3 w-3" />
                      </Button>
                    </div>
                    <div className="flex-1">
                      <h3 
                        className="font-medium text-red-600 hover:text-red-700 cursor-help text-sm"
                        title={operation.description}
                      >
                        {operation.name}
                      </h3>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => handleRemoveFromQueue(index)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                )
              })}
            </div>
            <Button
              onClick={handleProcessQueue}
              disabled={isProcessing}
              className="w-full mt-4"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                "Process Queue"
              )}
            </Button>
          </div>
        )}
      </div>

      {showStats && stats && (
        <XLIFFStatsDialog
          isOpen={showStats}
          onClose={() => {
            setShowStats(false)
            setStats(null)
          }}
          stats={stats}
          operation={currentOperation || "check"}
        />
      )}
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

