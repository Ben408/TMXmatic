"use client"

import { useState, useEffect } from "react"
import { format } from "date-fns"
import { FileUploader } from "./file-uploader"
import { WorkspaceFiles } from "./workspace-files"
import { OperationsPanel } from "./operations-panel"
import { OkapiPanel } from "./okapi-panel"
import { ProcessingHistory } from "./processing-history"
import { Button } from "@/components/ui/button"
import { Download, AlertCircle, Upload } from "lucide-react"
import { toast } from "@/components/ui/use-toast"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { XLIFFStatsDialog } from "./xliff-stats-dialog"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { ArrowUp, ArrowDown, Trash2 } from "lucide-react"
import { Loader2 } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import JSZip from "jszip"
import {
  DownloadFormat,
  getFileExtension,
  getFileTypeLabel,
  isTmxOrXliffFile,
  isZipBytes,
  preferredExtensionsForFormat,
} from "@/lib/download-utils"

export type XLIFFStats = {
  translations_found?: number
  updates_made?: number
  remaining_empty?: number
  total_segments?: number
  empty_segments?: number
  completion_rate?: number
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
  sourceProject?: {
    integration: "okapi"
    projectId?: string
    workspaceId?: string
    fileId?: string
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
    description: "Here you can select the MT cleaning steps you want to apply to the TMX files."
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
  { 
    id: "process_tbx", 
    name: "Process TBX",
    description: "Remove duplicate terms with less information."
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
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false)
  const [uploadedCount, setUploadedCount] = useState(0)
  const [uploadTargetFileIds, setUploadTargetFileIds] = useState<string[]>([])
  const [cutoffDate, setCutoffDate] = useState<Date>()
  const [batchMtSelectedSteps, setBatchMtSelectedSteps] = useState<string[]>([
    "remove_empty",
    "find_duplicates",
    "non_true_duplicates",
    "remove_sentence",
  ])

  const selectedFiles = files.filter(file => selectedFileIds.includes(file.id))

  // Keep a single workspace file selected so Okapi / TMX ops stay usable.
  useEffect(() => {
    if (files.length === 1 && selectedFileIds.length === 0) {
      setSelectedFileIds([files[0].id])
    }
  }, [files, selectedFileIds.length])

  const appendCutoffDateIfApplicable = (formData: FormData, primaryOperationId: string) => {
    const ops = queuedOperations.length > 0 ? queuedOperations : [primaryOperationId]
    const cutoffRaw = cutoffDate ? format(cutoffDate, "yyyy-MM-dd") : null
    if (!cutoffRaw) return

    const needsMandatoryCutoff = ops.some(
      (op) => op === "remove_old" || op === "find_date_duplicates",
    )
    if (needsMandatoryCutoff) {
      formData.append("cutoff_date", cutoffRaw)
      return
    }

    if (ops.some((op) => op === "batch_process_mt") && batchMtSelectedSteps.includes("remove_old")) {
      formData.append("use_batch_mt_cutoff", "1")
      formData.append("cutoff_date", cutoffRaw)
    }
  }

  const appendBatchMtOptionsIfApplicable = (formData: FormData, primaryOperationId: string) => {
    const ops = queuedOperations.length > 0 ? queuedOperations : [primaryOperationId]
    if (!ops.includes("batch_process_mt")) return
    formData.append("batch_mt_steps", JSON.stringify(batchMtSelectedSteps))
  }

  const handleFilesAdded = (
    newFiles: File[],
    sourceProject?:
      | {
          integration: "okapi"
          projectId?: string
          workspaceId?: string
          fileId?: string
        }
      | {
          integration: "okapi"
          projectId?: string
          workspaceId?: string
          fileId?: string
        }[]
  ) => {
    const workspaceFiles = newFiles.map((file, i) => ({
      id: crypto.randomUUID(),
      name: file.name,
      type: file.type,
      size: file.size,
      data: file,
      originalData: file,
      status: "idle" as const,
      operations: [],
      relatedFiles: {},
      sourceProject: Array.isArray(sourceProject) ? sourceProject[i] : sourceProject,
    }))

    setFiles((prev) => [...prev, ...workspaceFiles])

    if (workspaceFiles.length > 0 && selectedFileIds.length === 0) {
      setSelectedFileIds([workspaceFiles[0].id])
    }

    const sourceLabel = Array.isArray(sourceProject)
      ? sourceProject[0]?.integration
      : sourceProject?.integration

    toast({
      title: "Files added",
      description: `${newFiles.length} file(s) added to workspace${
        sourceLabel ? ` from ${sourceLabel}` : ""
      }`,
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
      if (operationId === "merge_tmx") {
        // Send all selected files in one request
        const formData = new FormData()
        for (const fileId of selectedFileIds) {
          const file = files.find(f => f.id === fileId)
          if (!file) continue
          formData.append('file', file.originalData, file.name)
        }
        console.log("formData files:", formData.getAll('files'))
        if (queuedOperations.length > 0) {
          formData.append('operations', JSON.stringify(queuedOperations))
        } else {
          formData.append('operation', operationId)
        }
        appendCutoffDateIfApplicable(formData, operationId)
        appendBatchMtOptionsIfApplicable(formData, operationId)
        console.log(`Sending merge_tmx request to /api/${operationId}`, {
          operations: queuedOperations.length > 0 ? queuedOperations : [operationId],
          files: selectedFileIds.map(id => files.find(f => f.id === id)?.name)
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
        const result = await response.blob()
        // Assign the merged file to the first selected file
        setFiles((prev) =>
          prev.map((f, idx) => {
            if (f.id === selectedFileIds[0]) {
              const processedFile = new File([result], f.name.replace(/\.[^/.]+$/, "_merged.tmx"), { type: f.type })
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
            // Mark other selected files as processed (but no processedData)
            if (selectedFileIds.includes(f.id) && f.id !== selectedFileIds[0]) {
              return {
                ...f,
                status: "processed",
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
        toast({
          title: "Operation complete",
          description: `Successfully merged ${selectedFileIds.length} TMX files`,
        })
        return
      }

      // ...existing code for other operations...
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
        appendCutoffDateIfApplicable(formData, operationId)
        appendBatchMtOptionsIfApplicable(formData, operationId)
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

  const triggerBlobDownload = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const extractPreferredFromZip = async (
    zipBlob: Blob,
    preferredExts: string[],
  ): Promise<{ blob: Blob; filename: string } | null> => {
    const zip = await JSZip.loadAsync(zipBlob)
    const entries = Object.keys(zip.files).filter((name) => !zip.files[name]?.dir)
    const preferred = entries.find((name) =>
      preferredExts.some((ext) => name.toLowerCase().endsWith(ext)),
    )
    if (!preferred) return null
    const content = await zip.files[preferred].async("blob")
    return { blob: content, filename: preferred.split("/").pop() || preferred }
  }

  const handleDownloadFile = async (fileId: string, format: DownloadFormat = "source") => {
    const file = files.find((f) => f.id === fileId)
    if (!file) return

    if (format === "source") {
      // Keep legacy behavior for non-TMX/XLIFF files: download processed output when available.
      if (!isTmxOrXliffFile(file.name) && file.processedData) {
        const arrayBuffer = await file.processedData.arrayBuffer()
        const uint8Array = new Uint8Array(arrayBuffer)
        const isZipFile = isZipBytes(uint8Array)
        if (isZipFile) {
          const baseName = file.name.replace(/\.[^/.]+$/, "")
          triggerBlobDownload(file.processedData, `${baseName}_processed.zip`)
        } else {
          triggerBlobDownload(file.processedData, file.name)
        }
      } else {
        triggerBlobDownload(file.originalData, file.name)
      }
      toast({
        title: "File downloaded",
        description: `Downloaded file ${file.name}`,
      })
      return
    }

    if (!file.processedData) return

    // Check if the processed data is actually a ZIP file by examining the first few bytes
    const arrayBuffer = await file.processedData.arrayBuffer()
    const uint8Array = new Uint8Array(arrayBuffer)
    
    // ZIP files start with PK\x03\x04 (0x504B0304)
    const isZipFile = isZipBytes(uint8Array)

    if (isZipFile) {
      const preferredExts = preferredExtensionsForFormat(format)
      const extracted = await extractPreferredFromZip(file.processedData, preferredExts)
      if (extracted) {
        triggerBlobDownload(extracted.blob, extracted.filename)
        toast({
          title: "File downloaded",
          description: `Downloaded ${format.toUpperCase()} file from processed archive of ${file.name}`,
        })
        return
      }
      const baseName = file.name.replace(/\.[^/.]+$/, "")
      triggerBlobDownload(file.processedData, `${baseName}_processed.zip`)
      toast({
        title: "Format not found in archive",
        description: `No ${format.toUpperCase()} file found in archive. Downloaded full ZIP instead.`,
      })
    } else {
      const desiredExt = format === "tmx" ? ".tmx" : ".xlf"
      const currentExt = `.${getFileExtension(file.name)}`
      if (format === "tmx" && currentExt !== ".tmx") {
        toast({
          title: "Download unavailable",
          description: "Processed output is not a TMX file.",
          variant: "destructive",
        })
        return
      }
      if (format === "xliff" && currentExt !== ".xlf" && currentExt !== ".xliff") {
        toast({
          title: "Download unavailable",
          description: "Processed output is not an XLIFF file.",
          variant: "destructive",
        })
        return
      }
      const outName =
        currentExt === desiredExt || (format === "xliff" && currentExt === ".xliff")
          ? file.name
          : `${file.name.replace(/\.[^/.]+$/, "")}${desiredExt}`
      triggerBlobDownload(file.processedData, outName)
      toast({
        title: "File downloaded",
        description: `Downloaded ${format.toUpperCase()} output for ${file.name}`,
      })
    }
  }

  const handleBulkDownload = async (format: DownloadFormat = "source") => {
    const targetFiles = format === "source" ? files : files.filter(file => file.processedData)
    if (targetFiles.length === 0) return

    const zip = new JSZip()
    for (const file of targetFiles) {
      if (format === "source") {
        zip.file(file.name, file.originalData)
        continue
      }
      if (!file.processedData) continue
      const arrayBuffer = await file.processedData.arrayBuffer()
      const uint8Array = new Uint8Array(arrayBuffer)
      const isZipFile = isZipBytes(uint8Array)

      if (isZipFile) {
        const preferredExts = preferredExtensionsForFormat(format)
        const extracted = await extractPreferredFromZip(file.processedData, preferredExts)
        if (extracted) {
          zip.file(extracted.filename, extracted.blob)
        } else {
          zip.file(`${file.name.replace(/\.[^/.]+$/, "")}_processed.zip`, file.processedData)
        }
      } else {
        const ext = `.${getFileExtension(file.name)}`
        if (format === "tmx" && ext === ".tmx") {
          zip.file(file.name, file.processedData)
        }
        if (format === "xliff" && (ext === ".xlf" || ext === ".xliff")) {
          zip.file(file.name, file.processedData)
        }
      }
    }
    const content = await zip.generateAsync({ type: "blob" })
    triggerBlobDownload(content, `download_${format}.zip`)

    toast({
      title: "Files downloaded",
      description: `Downloaded ${targetFiles.length} file(s) as ${format.toUpperCase()}.`,
    })
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
        appendCutoffDateIfApplicable(formData, queuedOperations[0] ?? "")
        appendBatchMtOptionsIfApplicable(formData, queuedOperations[0] ?? "")

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

  const handleUploadToProject = async (fileId: string) => {
    const file = files.find((f) => f.id === fileId)
    if (!file || !file.processedData || !file.sourceProject) {
      toast({
        title: "Error",
        description: "File is not ready for upload or missing source project information",
        variant: "destructive",
      })
      return
    }

    try {
      // Check if processedData is a ZIP file
      const arrayBuffer = await file.processedData.arrayBuffer()
      const uint8Array = new Uint8Array(arrayBuffer)
      const isZipFile = isZipBytes(uint8Array)

      let fileToUpload = file.processedData
      let fileName = file.name

      // If it's a ZIP file, we need to extract the "clean" file
      if (isZipFile) {
        const JSZip = (await import('jszip')).default
        const zip = await JSZip.loadAsync(file.processedData)
        const fileNames = Object.keys(zip.files)
        
        // Look for the clean file (usually has "clean" or "processed" in the name, or is the non-duplicate file)
        // Priority: files with "clean" > files with "processed" > first file that's not a duplicate/garbage file
        let cleanFileName = fileNames.find(name => 
          name.toLowerCase().includes('clean') && !name.toLowerCase().includes('duplicate')
        ) || fileNames.find(name => 
          name.toLowerCase().includes('processed') && !name.toLowerCase().includes('duplicate')
        ) || fileNames.find(name => 
          !name.toLowerCase().includes('duplicate') && 
          !name.toLowerCase().includes('garbage') &&
          !name.toLowerCase().includes('old')
        ) || fileNames[0]

        if (cleanFileName) {
          const cleanFile = zip.files[cleanFileName]
          if (cleanFile && !cleanFile.dir) {
            const cleanFileData = await cleanFile.async('blob')
            fileToUpload = new File([cleanFileData], cleanFileName, { type: 'application/octet-stream' })
            fileName = cleanFileName
          }
        }
      }

      const formData = new FormData()
      formData.append('file', fileToUpload, fileName)
      formData.append('integration', file.sourceProject.integration)
      if (file.sourceProject.projectId) {
        formData.append('project_id', file.sourceProject.projectId)
      }
      if (file.sourceProject.workspaceId) {
        formData.append('workspace_id', file.sourceProject.workspaceId)
      }
      if (file.sourceProject.fileId) {
        formData.append('original_file_id', file.sourceProject.fileId)
      }

      const response = await fetch('http://127.0.0.1:5000/api/upload-to-project', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to upload file to project')
      }

      const result = await response.json()

      setUploadedCount((prev) => prev + 1)
    } catch (error) {
      console.error("Error uploading file to project:", error)
      toast({
        title: "Upload failed",
        description: error instanceof Error ? error.message : "Failed to upload file to project",
        variant: "destructive",
      })
    }
  }

  const filesWithUpload = files.filter((f) => f.processedData && f.sourceProject)
  const runUploadWithModal = async (fileIds: string[]) => {
    if (fileIds.length === 0) return
    setUploadedCount(0)
    setUploadTargetFileIds(fileIds)
    setUploadDialogOpen(true)
    for (const fileId of fileIds) {
      await handleUploadToProject(fileId)
    }
  }
  const handleBulkUploadToProject = async () => {
    await runUploadWithModal(filesWithUpload.map((f) => f.id))
  }
  const handleSingleUploadToProject = async (fileId: string) => {
    await runUploadWithModal([fileId])
  }

  const queueNeedsMandatoryCutoff =
    (queuedOperations.includes("remove_old") || queuedOperations.includes("find_date_duplicates")) &&
    !cutoffDate

  const queueBatchCutoffIncomplete =
    queuedOperations.includes("batch_process_mt") &&
    batchMtSelectedSteps.includes("remove_old") &&
    !cutoffDate

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
            onClearSelection={() => setSelectedFileIds([])}
            cutoffDate={cutoffDate}
            onCutoffDateChange={setCutoffDate}
            batchMtSelectedSteps={batchMtSelectedSteps}
            onBatchMtSelectedStepsChange={setBatchMtSelectedSteps}
          />
        )}

        <OkapiPanel files={selectedFiles} workspaceFileCount={files.length} />
      </div>

      <div className="space-y-6">
        <div className="bg-card rounded-lg border shadow-sm p-4">
          <h2 className="text-xl font-semibold mb-4">Workspace Summary</h2>
          <div className="space-y-2">
            <p>Files in workspace: {files.length}</p>
            <p>Selected files: {selectedFileIds.length}</p>
            <p>Operations applied: {files.reduce((acc, file) => acc + file.operations.length, 0)}</p>
            {files.some(file => file.processedData) && (
              <div className="flex gap-2 mt-4">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button className="flex-1">
                      <Download className="mr-2 h-4 w-4" />
                      Download All
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuItem onClick={() => handleBulkDownload("source")}>
                      Download as Source
                    </DropdownMenuItem>
                    {files.every((f) => isTmxOrXliffFile(f.name)) ? (
                      <>
                        <DropdownMenuItem onClick={() => handleBulkDownload("tmx")}>
                          Download as TMX
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleBulkDownload("xliff")}>
                          Download as XLIFF
                        </DropdownMenuItem>
                      </>
                    ) : null}
                  </DropdownMenuContent>
                </DropdownMenu>
                {filesWithUpload.length > 0 && (
                  <Button
                    className="flex-1"
                    variant="outline"
                    onClick={handleBulkUploadToProject}
                  >
                    <Upload className="mr-2 h-4 w-4" />
                    Upload All
                  </Button>
                )}
              </div>
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
                    <div className="flex gap-2 mt-2">
                      {isTmxOrXliffFile(file.name) ? (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              className="flex-1"
                              size="sm"
                              disabled={!file.processedData && !file.originalData}
                            >
                              <Download className="mr-1 h-3 w-3" />
                              Download
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="start">
                            <DropdownMenuItem onClick={() => handleDownloadFile(file.id, "tmx")}>
                              Download as TMX
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleDownloadFile(file.id, "xliff")}>
                              Download as XLIFF
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleDownloadFile(file.id, "source")}>
                              Download as Source
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      ) : (
                        <Button
                          className="flex-1"
                          size="sm"
                          onClick={() => handleDownloadFile(file.id, "source")}
                          disabled={!file.processedData}
                        >
                          <Download className="mr-1 h-3 w-3" />
                          Download
                        </Button>
                      )}
                      {file.processedData && file.sourceProject && (
                        <Button
                          className="flex-1"
                          size="sm"
                          variant="outline"
                          onClick={() => handleSingleUploadToProject(file.id)}
                        >
                          <Upload className="mr-1 h-3 w-3" />
                          Upload
                        </Button>
                      )}
                    </div>
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
              disabled={
                isProcessing || queueNeedsMandatoryCutoff || queueBatchCutoffIncomplete
              }
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

      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Uploading to project</DialogTitle>
            <DialogDescription>
              {uploadTargetFileIds.length > 0
                ? `Uploaded ${uploadedCount} of ${uploadTargetFileIds.length} file(s).`
                : "No files available for upload."}
            </DialogDescription>
          </DialogHeader>
          {uploadTargetFileIds.length > 0 && uploadedCount >= uploadTargetFileIds.length && (
            <p className="text-sm text-muted-foreground mt-2">
              {uploadedCount} file(s) uploaded.
            </p>
          )}
          <div className="flex justify-end mt-4">
            <Button
              variant="outline"
              onClick={() => setUploadDialogOpen(false)}
              disabled={uploadTargetFileIds.length > 0 && uploadedCount < uploadTargetFileIds.length}
            >
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}


