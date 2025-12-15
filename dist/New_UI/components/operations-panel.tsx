"use client"

import { WorkspaceFile, Operation } from "./tmx-workspace"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, GripVertical, Trash2, ArrowUp, ArrowDown, Calendar } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { Calendar as CalendarIcon } from "lucide-react"
import { format } from "date-fns"
import { Calendar as CalendarComponent } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { cn } from "@/lib/utils"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

export interface OperationsPanelProps {
  files: WorkspaceFile[]
  operations: Operation[]
  onProcess: (operationId: string, size?: number, date?: Date) => Promise<void>
  allFiles: WorkspaceFile[]
  onFileUpdate: (fileId: string, updates: Partial<WorkspaceFile>) => void
  queuedOperations: string[]
  onQueueUpdate: (operations: string[]) => void
  onClearSelection?: () => void
}

export function OperationsPanel({
  files,
  operations,
  onProcess,
  allFiles,
  onFileUpdate,
  queuedOperations,
  onQueueUpdate,
  onClearSelection,
}: OperationsPanelProps) {
  const [fileTypeTab, setFileTypeTab] = useState("tmx")
  const [activeTab, setActiveTab] = useState("all")
  const [splitSize, setSplitSize] = useState<number>(1000)
  const [selectedOperations, setSelectedOperations] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState<Date>()
  const [showWarningDialog, setShowWarningDialog] = useState(false)
  const [userConfirmed, setUserConfirmed] = useState(false)
  const isProcessing = files.length > 0 && files[0].status === "processing"

  // Determine file types from selected files
  const getFileExtension = (fileName: string): string => {
    return fileName.split('.').pop()?.toLowerCase() || ''
  }

  const hasTbxFiles = files.some(file => getFileExtension(file.name) === 'tbx')
  const hasZipFiles = files.some(file => getFileExtension(file.name) === 'zip')
  const hasOtherFiles = files.some(file => {
    const ext = getFileExtension(file.name)
    return ext !== 'tbx' && ext !== 'zip'
  })

  // Check if both TBX and other file types are selected (excluding ZIP)
  const hasMixedFileTypes = hasTbxFiles && hasOtherFiles && !hasZipFiles

  // Show warning dialog when mixed file types are detected and user hasn't confirmed
  useEffect(() => {
    if (hasMixedFileTypes && !userConfirmed && files.length > 0) {
      setShowWarningDialog(true)
    } else if (!hasMixedFileTypes) {
      // Reset confirmation when selection changes to non-mixed types
      setUserConfirmed(false)
    }
  }, [hasMixedFileTypes, userConfirmed, files.length])

  // Determine which tabs to show based on selected file types
  // - TBX tab only: when selected file is TBX and not ZIP
  // - TMX tab only: when selected file is other types (non-TBX, non-ZIP) and not ZIP
  // - Both tabs: when selected file is ZIP OR when mixed file types are selected (with user confirmation) OR when no files are selected (default state)
  const showTmxTab = files.length === 0 || hasZipFiles || (hasOtherFiles && !hasTbxFiles && !hasZipFiles) || (hasMixedFileTypes && userConfirmed)
  const showTbxTab = files.length === 0 || hasZipFiles || (hasTbxFiles && !hasZipFiles) || (hasMixedFileTypes && userConfirmed)

  // Auto-select appropriate tab when selected files change
  useEffect(() => {
    if (showTmxTab && !showTbxTab && fileTypeTab === "tbx") {
      setFileTypeTab("tmx")
    } else if (showTbxTab && !showTmxTab && fileTypeTab === "tmx") {
      setFileTypeTab("tbx")
    } else if (!showTmxTab && !showTbxTab) {
      // No files selected, default to tmx
      setFileTypeTab("tmx")
    } else if (showTmxTab && showTbxTab && !fileTypeTab) {
      // Both tabs available, default to tmx
      setFileTypeTab("tmx")
    }
  }, [showTmxTab, showTbxTab, fileTypeTab, files])

  // Filter operations by file type
  const tmxOperations = operations.filter((op) => {
    // Exclude XLIFF-specific operations, include all others as TMX operations
    return !op.id.startsWith("xliff_") && !op.id.endsWith("_tbx")
  })
  
  const tbxOperations = operations.filter((op) => {
    // Filter for TBX operations (currently empty, ready for future TBX operations)
    return op.id.endsWith("_tbx")
  })

  // Group operations by category (for TMX)
  const conversionOps = tmxOperations.filter((op) => op.id.startsWith("convert_") || op.id.includes("merge"))
  const cleaningOps = tmxOperations.filter((op) => op.id.includes("clean") || op.id.includes("empty") || op.id.includes("duplicates") || op.id.includes("remove") || op.id.includes("count") || op.id.includes("extract"))
  const splitOps = tmxOperations.filter((op) => op.id.includes("split"))
  const batchOps = tmxOperations.filter((op) => op.id.includes("batch"))
  const analysisOps = tmxOperations.filter((op) => op.id.includes("count") || op.id.includes("extract") || op.id.includes("find"))

  // Group operations by category (for TBX)
  const tbxConversionOps = tbxOperations.filter((op) => op.id.startsWith("convert_") || op.id.includes("merge"))
  const tbxCleaningOps = tbxOperations.filter((op) => op.id.includes("clean") || op.id.includes("empty") || op.id.includes("duplicates") || op.id.includes("remove") || op.id.includes("count") || op.id.includes("extract") || op.id.includes("process"))
  const tbxSplitOps = tbxOperations.filter((op) => op.id.includes("split"))
  const tbxBatchOps = tbxOperations.filter((op) => op.id.includes("batch"))
  const tbxAnalysisOps = tbxOperations.filter((op) => op.id.includes("count") || op.id.includes("extract") || op.id.includes("find"))

  const handleOperationSelect = (operationId: string) => {
    setSelectedOperations(prev => {
      if (prev.includes(operationId)) {
        return prev.filter(id => id !== operationId)
      }
      return [...prev, operationId]
    })
  }

  const handleAddToQueue = (operationId: string) => {
    onQueueUpdate([...queuedOperations, operationId])
  }

  const handleMoveOperation = (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1
    if (newIndex < 0 || newIndex >= queuedOperations.length) return

    const newQueue = [...queuedOperations]
    const [movedItem] = newQueue.splice(index, 1)
    newQueue.splice(newIndex, 0, movedItem)
    onQueueUpdate(newQueue)
  }

  const handleRemoveFromQueue = (index: number) => {
    const newQueue = [...queuedOperations]
    newQueue.splice(index, 1)
    onQueueUpdate(newQueue)
  }

  const handleProcessQueue = async () => {
    for (const operationId of queuedOperations) {
      await onProcess(operationId, operationId === "split_size" ? splitSize : undefined)
    }
  }

  const handleContinue = () => {
    setUserConfirmed(true)
    setShowWarningDialog(false)
  }

  const handleGoBack = () => {
    setShowWarningDialog(false)
    if (onClearSelection) {
      onClearSelection()
    }
  }

  const renderOperationsContent = (ops: Operation[], conversionOps: Operation[], cleaningOps: Operation[], analysisOps: Operation[], splitOps: Operation[], batchOps: Operation[]) => (
    <Tabs value={activeTab} onValueChange={setActiveTab}>
      <TabsList className="grid grid-cols-7 mb-4">
        <TabsTrigger value="all" disabled={isProcessing}>
          All
        </TabsTrigger>
        <TabsTrigger value="conversion" disabled={isProcessing}>
          Conversion
        </TabsTrigger>
        <TabsTrigger value="cleaning" disabled={isProcessing}>
          Cleaning
        </TabsTrigger>
        <TabsTrigger value="analysis" disabled={isProcessing}>
          Analysis
        </TabsTrigger>
        <TabsTrigger value="splitting" disabled={isProcessing}>
          Splitting
        </TabsTrigger>
        <TabsTrigger value="batch" disabled={isProcessing}>
          Batch
        </TabsTrigger>
        <TabsTrigger value="custom" disabled={isProcessing}>
          Queuing
        </TabsTrigger>
      </TabsList>

      <TabsContent value="all" className="space-y-4">
        <OperationsList operations={ops} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} selectedDate={selectedDate} setSelectedDate={setSelectedDate} />
      </TabsContent>

      <TabsContent value="conversion" className="space-y-4">
        <OperationsList operations={conversionOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} selectedDate={selectedDate} setSelectedDate={setSelectedDate} />
      </TabsContent>

      <TabsContent value="cleaning" className="space-y-4">
        <OperationsList operations={cleaningOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} selectedDate={selectedDate} setSelectedDate={setSelectedDate} />
      </TabsContent>

      <TabsContent value="analysis" className="space-y-4">
        <OperationsList operations={analysisOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} selectedDate={selectedDate} setSelectedDate={setSelectedDate} />
      </TabsContent>

      <TabsContent value="splitting" className="space-y-4">
        <OperationsList operations={splitOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} selectedDate={selectedDate} setSelectedDate={setSelectedDate} />
      </TabsContent>

      <TabsContent value="batch" className="space-y-4">
        <OperationsList operations={batchOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} selectedDate={selectedDate} setSelectedDate={setSelectedDate} />
      </TabsContent>

      <TabsContent value="custom" className="space-y-4">
        <div className="space-y-4">
          {ops.map((operation) => (
            <div
              key={operation.id}
              className="flex items-center justify-between p-4 border rounded-lg"
            >
              <div className="space-y-1">
                <h3 className="font-medium">{operation.name}</h3>
                <p className="text-sm text-muted-foreground">
                  {operation.description}
                </p>
              </div>
              {operation.id === "split_size" && (
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    value={splitSize}
                    onChange={(e) => setSplitSize(Number(e.target.value))}
                    className="w-24"
                    min={1}
                  />
                  <span className="text-sm text-muted-foreground">segments</span>
                </div>
              )}
              {(operation.id === "remove_old" || operation.id === "find_date_duplicates") && (
                <div className="flex items-center gap-2">
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant={"outline"}
                        className={cn(
                          "w-[200px] justify-start text-left font-normal",
                          !selectedDate && "text-muted-foreground"
                        )}
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {selectedDate ? format(selectedDate, "PPP") : <span>Pick a date</span>}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0">
                      <CalendarComponent
                        mode="single"
                        selected={selectedDate}
                        onSelect={setSelectedDate}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleAddToQueue(operation.id)}
              >
                Add to Queue
              </Button>
            </div>
          ))}
        </div>
      </TabsContent>
    </Tabs>
  )

  // Render the warning dialog
  const renderWarningDialog = () => (
    <AlertDialog open={showWarningDialog} onOpenChange={setShowWarningDialog}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Caution</AlertDialogTitle>
          <AlertDialogDescription>
            Caution: you're selecting different file types. This is not recommended.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleGoBack}>Go Back</AlertDialogCancel>
          <AlertDialogAction onClick={handleContinue}>Continue</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )

  // If dialog is open and user hasn't confirmed, only show the dialog
  if (showWarningDialog && !userConfirmed) {
    return (
      <>
        {renderWarningDialog()}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Operations</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-muted-foreground">
                <p>Please confirm your selection to proceed.</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </>
    )
  }

  // If only one tab should be shown, render it directly without tabs
  if (showTmxTab && !showTbxTab) {
    return (
      <>
        {renderWarningDialog()}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>TMX Operations</CardTitle>
            </CardHeader>
            <CardContent>
              {renderOperationsContent(tmxOperations, conversionOps, cleaningOps, analysisOps, splitOps, batchOps)}
            </CardContent>
          </Card>
        </div>
      </>
    )
  }

  if (showTbxTab && !showTmxTab) {
    return (
      <>
        {renderWarningDialog()}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>TBX Operations</CardTitle>
            </CardHeader>
            <CardContent>
              {tbxOperations.length > 0 ? (
                renderOperationsContent(tbxOperations, tbxConversionOps, tbxCleaningOps, tbxAnalysisOps, tbxSplitOps, tbxBatchOps)
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No TBX operations available yet.</p>
                  <p className="text-sm mt-2">TBX operations will appear here when added.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </>
    )
  }

  // Show both tabs (for ZIP files or when both file types are present)
  return (
    <>
      {renderWarningDialog()}
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Operations</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs value={fileTypeTab} onValueChange={setFileTypeTab} className="w-full">
              <TabsList className={cn("mb-6", showTmxTab && showTbxTab ? "grid grid-cols-2" : "grid grid-cols-1")}>
                {showTmxTab && (
                  <TabsTrigger value="tmx" disabled={isProcessing}>
                    TMX Operations
                  </TabsTrigger>
                )}
                {showTbxTab && (
                  <TabsTrigger value="tbx" disabled={isProcessing}>
                    TBX Operations
                  </TabsTrigger>
                )}
              </TabsList>

              {showTmxTab && (
                <TabsContent value="tmx" className="space-y-4">
                  {renderOperationsContent(tmxOperations, conversionOps, cleaningOps, analysisOps, splitOps, batchOps)}
                </TabsContent>
              )}

              {showTbxTab && (
                <TabsContent value="tbx" className="space-y-4">
                  {tbxOperations.length > 0 ? (
                    renderOperationsContent(tbxOperations, tbxConversionOps, tbxCleaningOps, tbxAnalysisOps, tbxSplitOps, tbxBatchOps)
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <p>No TBX operations available yet.</p>
                      <p className="text-sm mt-2">TBX operations will appear here when added.</p>
                    </div>
                  )}
                </TabsContent>
              )}
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </>
  )
}

function OperationsList({
  operations,
  onProcess,
  isProcessing,
  files,
  splitSize,
  setSplitSize,
  selectedDate,
  setSelectedDate,
}: {
  operations: Operation[]
  onProcess: (operationId: string, size?: number, date?: Date) => Promise<void>
  isProcessing: boolean
  files: WorkspaceFile[]
  splitSize: number
  setSplitSize: (size: number) => void
  selectedDate?: Date
  setSelectedDate: (date?: Date) => void
}) {
  return (
    <div className="space-y-4">
      {operations.map((operation) => (
        <div key={operation.id} className="flex items-center gap-4">
          <div className="flex-1">
            <h3 className="font-medium">{operation.name}</h3>
            <p className="text-sm text-muted-foreground">{operation.description}</p>
          </div>
          {operation.id === "split_size" && (
            <div className="flex items-center gap-2">
              <Input
                type="number"
                value={splitSize}
                onChange={(e) => setSplitSize(Number(e.target.value))}
                className="w-24"
                min={1}
              />
              <span className="text-sm text-muted-foreground">segments</span>
            </div>
          )}
          {(operation.id === "remove_old" || operation.id === "find_date_duplicates") && (
            <div className="flex items-center gap-2">
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant={"outline"}
                    className={cn(
                      "w-[200px] justify-start text-left font-normal",
                      !selectedDate && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {selectedDate ? format(selectedDate, "PPP") : <span>Pick a date</span>}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <CalendarComponent
                    mode="single"
                    selected={selectedDate}
                    onSelect={setSelectedDate}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>
          )}
          <Button
            onClick={() => onProcess(
              operation.id,
              operation.id === "split_size" ? splitSize : undefined,
              (operation.id === "remove_old" || operation.id === "find_date_duplicates") ? selectedDate : undefined
            )}
            disabled={files.length === 0 || isProcessing || ((operation.id === "remove_old" || operation.id === "find_date_duplicates") && !selectedDate)}
          >
            {isProcessing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : (
              "Process"
            )}
          </Button>
        </div>
      ))}
    </div>
  )
}

function getOperationDescription(opId: string): string {
  switch (opId) {
    case "convert_vatv":
      return "Convert Termweb CSV files to TMX format."
    case "convert_termweb":
      return "Convert TermWeb Excel files to TMX format."
    case "remove_empty":
      return "Remove translation units with empty target segments."
    case "find_duplicates":
      return "Identify and extract duplicate translation units."
    case "non_true_duplicates":
      return "Find segments that are similar but not exact duplicates."
    case "remove_sentence":
      return "Extract sentence-level segments from TMX files."
    case "remove_old":
      return "Remove translation units older than a specified date."
    case "clean_mt":
      return "Clean TMX files for machine translation by removing metadata."
    case "remove_context_props":
      return "Remove context properties from TMX files."
    case "count_last_usage":
      return "Count translation units by their last usage dates."
    case "count_creation_dates":
      return "Count translation units by their creation dates."
    case "extract_translations":
      return "Extract all translations to CSV format with metadata."
    case "find_date_duplicates":
      return "Find duplicates based on creation and change dates."
    case "merge_tmx":
      return "Combine multiple TMX files into a single file."
    case "split_language":
      return "Split a TMX file into separate files by language pair."
    case "split_size":
      return "Split a large TMX file into smaller files by segment count."
    case "batch_process_tms":
      return "Apply multiple cleaning operations for TMS compatibility."
    case "batch_process_mt":
      return "Apply multiple cleaning operations for machine translation."
    case "xliff_tmx_leverage":
      return "Leverage TMX into XLIFF"
    case "xliff_cleanup":
      return "Clean XLIFF"
    case "xliff_validate":
      return "Validate XLIFF"
    case "process_tbx":
      return "Remove duplicate terms with less information."
    default:
      return "Apply this operation to the selected file."
  }
}

const isValidFileType = (file: File, operation: Operation) => {
  const extension = file.name.split('.').pop()?.toLowerCase()

  if (operation.requiresFiles?.includes("xliff")) {
    return extension === "xlf" || extension === "xliff"
  }
  if (operation.requiresFiles?.includes("tmx")) {
    return extension === "tmx"
  }
  // ... other file type checks ...
  return true
}

