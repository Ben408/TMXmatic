"use client"

import { WorkspaceFile, Operation } from "./tmx-workspace"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2 } from "lucide-react"
import { format } from "date-fns"
import { cn } from "@/lib/utils"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
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

function parseIsoDateToLocal(iso: string): Date | undefined {
  const [y, m, d] = iso.split("-").map((n) => parseInt(n, 10))
  if (!Number.isFinite(y) || !Number.isFinite(m) || !Number.isFinite(d)) return undefined
  return new Date(y, m - 1, d)
}

/** Native date input (browser picker + keyboard). Optional toggle for batch MT only. */
function CutoffDateControl({
  selectedDate,
  setSelectedDate,
}: {
  selectedDate?: Date
  setSelectedDate: (date?: Date) => void
}) {
  return (
    <div className="flex flex-col items-start gap-2">
      <Input
        type="date"
        value={selectedDate ? format(selectedDate, "yyyy-MM-dd") : ""}
        onChange={(e) => {
          const v = e.target.value
          if (!v) setSelectedDate(undefined)
          else {
            const parsed = parseIsoDateToLocal(v)
            if (parsed) setSelectedDate(parsed)
          }
        }}
        className="w-[155px] font-mono text-sm"
      />
    </div>
  )
}

export interface OperationsPanelProps {
  files: WorkspaceFile[]
  operations: Operation[]
  onProcess: (operationId: string, size?: number) => Promise<void>
  allFiles: WorkspaceFile[]
  onFileUpdate: (fileId: string, updates: Partial<WorkspaceFile>) => void
  queuedOperations: string[]
  onQueueUpdate: (operations: string[]) => void
  onClearSelection?: () => void
  cutoffDate?: Date
  onCutoffDateChange: (date?: Date) => void
  batchMtSelectedSteps: string[]
  onBatchMtSelectedStepsChange: (steps: string[]) => void
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
  cutoffDate,
  onCutoffDateChange,
  batchMtSelectedSteps,
  onBatchMtSelectedStepsChange,
}: OperationsPanelProps) {
  const [fileTypeTab, setFileTypeTab] = useState("tmx")
  const [activeTab, setActiveTab] = useState("all")
  const [splitSize, setSplitSize] = useState<number>(1000)
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
  const mtCleaningOps = tmxOperations.filter((op) => op.id === "batch_process_mt")
  const batchOps = tmxOperations.filter((op) => op.id.includes("batch") && op.id !== "batch_process_mt")
  const analysisOps = tmxOperations.filter((op) => op.id.includes("count") || op.id.includes("extract") || op.id.includes("find"))
  const tmxAllOps = tmxOperations.filter((op) => op.id !== "batch_process_mt")

  // Group operations by category (for TBX)
  const tbxConversionOps = tbxOperations.filter((op) => op.id.startsWith("convert_") || op.id.includes("merge"))
  const tbxCleaningOps = tbxOperations.filter((op) => op.id.includes("clean") || op.id.includes("empty") || op.id.includes("duplicates") || op.id.includes("remove") || op.id.includes("count") || op.id.includes("extract") || op.id.includes("process"))
  const tbxSplitOps = tbxOperations.filter((op) => op.id.includes("split"))
  const tbxBatchOps = tbxOperations.filter((op) => op.id.includes("batch"))
  const tbxAnalysisOps = tbxOperations.filter((op) => op.id.includes("count") || op.id.includes("extract") || op.id.includes("find"))

  const handleAddToQueue = (operationId: string) => {
    onQueueUpdate([...queuedOperations, operationId])
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

  const renderOperationsContent = (
    ops: Operation[],
    conversionOps: Operation[],
    cleaningOps: Operation[],
    analysisOps: Operation[],
    splitOps: Operation[],
    batchOps: Operation[],
    mtCleaningOps: Operation[]
  ) => (
    <Tabs value={activeTab} onValueChange={setActiveTab}>
      <TabsList
        className="grid mb-4"
        style={{ gridTemplateColumns: `repeat(${mtCleaningOps.length > 0 ? 8 : 7}, minmax(0, 1fr))` }}
      >
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
        {mtCleaningOps.length > 0 ? (
          <TabsTrigger value="mt-cleaning" disabled={isProcessing}>
            MT Cleaning
          </TabsTrigger>
        ) : null}
        <TabsTrigger value="custom" disabled={isProcessing}>
          Queuing
        </TabsTrigger>
      </TabsList>

      <TabsContent value="all" className="space-y-4">
        <OperationsList operations={ops} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} selectedDate={cutoffDate} setSelectedDate={onCutoffDateChange} batchMtSelectedSteps={batchMtSelectedSteps} onBatchMtSelectedStepsChange={onBatchMtSelectedStepsChange} />
      </TabsContent>

      <TabsContent value="conversion" className="space-y-4">
        <OperationsList operations={conversionOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} selectedDate={cutoffDate} setSelectedDate={onCutoffDateChange} batchMtSelectedSteps={batchMtSelectedSteps} onBatchMtSelectedStepsChange={onBatchMtSelectedStepsChange} />
      </TabsContent>

      <TabsContent value="cleaning" className="space-y-4">
        <OperationsList operations={cleaningOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} selectedDate={cutoffDate} setSelectedDate={onCutoffDateChange} batchMtSelectedSteps={batchMtSelectedSteps} onBatchMtSelectedStepsChange={onBatchMtSelectedStepsChange} />
      </TabsContent>

      <TabsContent value="analysis" className="space-y-4">
        <OperationsList operations={analysisOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} selectedDate={cutoffDate} setSelectedDate={onCutoffDateChange} batchMtSelectedSteps={batchMtSelectedSteps} onBatchMtSelectedStepsChange={onBatchMtSelectedStepsChange} />
      </TabsContent>

      <TabsContent value="splitting" className="space-y-4">
        <OperationsList operations={splitOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} selectedDate={cutoffDate} setSelectedDate={onCutoffDateChange} batchMtSelectedSteps={batchMtSelectedSteps} onBatchMtSelectedStepsChange={onBatchMtSelectedStepsChange} />
      </TabsContent>

      <TabsContent value="batch" className="space-y-4">
        <OperationsList operations={batchOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} selectedDate={cutoffDate} setSelectedDate={onCutoffDateChange} batchMtSelectedSteps={batchMtSelectedSteps} onBatchMtSelectedStepsChange={onBatchMtSelectedStepsChange} />
      </TabsContent>

      <TabsContent value="mt-cleaning" className="space-y-4">
        <OperationsList operations={mtCleaningOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} selectedDate={cutoffDate} setSelectedDate={onCutoffDateChange} batchMtSelectedSteps={batchMtSelectedSteps} onBatchMtSelectedStepsChange={onBatchMtSelectedStepsChange} />
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
              {(operation.id === "remove_old" || operation.id === "find_date_duplicates" || (operation.id === "batch_process_mt" && batchMtSelectedSteps.includes("remove_old"))) && (
                <CutoffDateControl
                  selectedDate={cutoffDate}
                  setSelectedDate={onCutoffDateChange}
                />
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
              {renderOperationsContent(tmxAllOps, conversionOps, cleaningOps, analysisOps, splitOps, batchOps, mtCleaningOps)}
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
                renderOperationsContent(tbxOperations, tbxConversionOps, tbxCleaningOps, tbxAnalysisOps, tbxSplitOps, tbxBatchOps, [])
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
                  {renderOperationsContent(tmxAllOps, conversionOps, cleaningOps, analysisOps, splitOps, batchOps, mtCleaningOps)}
                </TabsContent>
              )}

              {showTbxTab && (
                <TabsContent value="tbx" className="space-y-4">
                  {tbxOperations.length > 0 ? (
                    renderOperationsContent(tbxOperations, tbxConversionOps, tbxCleaningOps, tbxAnalysisOps, tbxSplitOps, tbxBatchOps, [])
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
  batchMtSelectedSteps,
  onBatchMtSelectedStepsChange,
}: {
  operations: Operation[]
  onProcess: (operationId: string, size?: number) => Promise<void>
  isProcessing: boolean
  files: WorkspaceFile[]
  splitSize: number
  setSplitSize: (size: number) => void
  selectedDate?: Date
  setSelectedDate: (date?: Date) => void
  batchMtSelectedSteps: string[]
  onBatchMtSelectedStepsChange: (steps: string[]) => void
}) {
  const batchMtStepOptions = [
    { id: "remove_empty", label: "Remove empty targets" },
    { id: "find_duplicates", label: "Remove true duplicates" },
    { id: "non_true_duplicates", label: "Extract non-true duplicates" },
    { id: "remove_sentence", label: "Remove sentence-level segments" },
    { id: "remove_old", label: "Remove old TUs (requires cutoff date)" },
  ] as const

  const toggleBatchMtStep = (stepId: string, checked: boolean) => {
    if (checked) {
      if (!batchMtSelectedSteps.includes(stepId)) {
        onBatchMtSelectedStepsChange([...batchMtSelectedSteps, stepId])
      }
      return
    }
    onBatchMtSelectedStepsChange(batchMtSelectedSteps.filter((id) => id !== stepId))
  }

  const batchMtRemoveOldEnabled = batchMtSelectedSteps.includes("remove_old")

  return (
    <div className="space-y-4">
      {operations.map((operation) => (
        <div key={operation.id} className="flex items-center gap-4">
          <div className="flex-1">
            <h3 className="font-medium">{operation.name}</h3>
            <p className="text-sm text-muted-foreground">{operation.description}</p>
            {operation.id === "batch_process_mt" ? (
              <div className="mt-3 space-y-3">
                <div className="space-y-2">
                  {batchMtStepOptions.map((step) => (
                    <div key={step.id} className="space-y-2">
                      <div className="flex items-center gap-2">
                        <Checkbox
                          id={`batch-mt-step-${step.id}`}
                          checked={batchMtSelectedSteps.includes(step.id)}
                          onCheckedChange={(v) => toggleBatchMtStep(step.id, v === true)}
                        />
                        <Label htmlFor={`batch-mt-step-${step.id}`} className="text-sm font-normal cursor-pointer">
                          {step.label}
                        </Label>
                      </div>
                      {step.id === "remove_old" && batchMtSelectedSteps.includes("remove_old") ? (
                        <div className="ml-6">
                          <CutoffDateControl
                            selectedDate={selectedDate}
                            setSelectedDate={setSelectedDate}
                          />
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <Checkbox id="batch-mt-step-clean-for-mt" checked={true} disabled />
                  <Label htmlFor="batch-mt-step-clean-for-mt" className="text-sm font-normal text-muted-foreground">
                    MT Cleaning (this includes numbering and other MT-oriented filters)
                  </Label>
                </div>
              </div>
            ) : null}
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
            <CutoffDateControl
              selectedDate={selectedDate}
              setSelectedDate={setSelectedDate}
            />
          )}
          <Button
            onClick={() =>
              onProcess(operation.id, operation.id === "split_size" ? splitSize : undefined)
            }
            disabled={
              files.length === 0 ||
              isProcessing ||
              ((operation.id === "remove_old" || operation.id === "find_date_duplicates") &&
                !selectedDate) ||
              (operation.id === "batch_process_mt" &&
                batchMtRemoveOldEnabled &&
                !selectedDate)
            }
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


