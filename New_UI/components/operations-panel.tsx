"use client"

import { WorkspaceFile, Operation } from "./tmx-workspace"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, GripVertical, Trash2, ArrowUp, ArrowDown } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"

export interface OperationsPanelProps {
  files: WorkspaceFile[]
  operations: Operation[]
  onProcess: (operationId: string, size?: number) => Promise<void>
  allFiles: WorkspaceFile[]
  onFileUpdate: (fileId: string, updates: Partial<WorkspaceFile>) => void
  queuedOperations: string[]
  onQueueUpdate: (operations: string[]) => void
}

export function OperationsPanel({
  files,
  operations,
  onProcess,
  allFiles,
  onFileUpdate,
  queuedOperations,
  onQueueUpdate,
}: OperationsPanelProps) {
  const [activeTab, setActiveTab] = useState("all")
  const [splitSize, setSplitSize] = useState<number>(1000)
  const [selectedOperations, setSelectedOperations] = useState<string[]>([])
  const isProcessing = files.length > 0 && files[0].status === "processing"

  // Group operations by category
  const conversionOps = operations.filter((op) => op.id.startsWith("convert_") || op.id.includes("merge"))
  const cleaningOps = operations.filter((op) => op.id.includes("clean") || op.id.includes("empty") || op.id.includes("duplicates"))
  const splitOps = operations.filter((op) => op.id.includes("split"))
  const batchOps = operations.filter((op) => op.id.includes("batch"))

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

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>TMX Operations</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid grid-cols-6 mb-4">
              <TabsTrigger value="all" disabled={isProcessing}>
                All
              </TabsTrigger>
              <TabsTrigger value="conversion" disabled={isProcessing}>
                Conversion
              </TabsTrigger>
              <TabsTrigger value="cleaning" disabled={isProcessing}>
                Cleaning
              </TabsTrigger>
              <TabsTrigger value="splitting" disabled={isProcessing}>
                Splitting
              </TabsTrigger>
              <TabsTrigger value="batch" disabled={isProcessing}>
                Batch
              </TabsTrigger>
              <TabsTrigger value="custom" disabled={isProcessing}>
                Custom
              </TabsTrigger>
            </TabsList>

            <TabsContent value="all" className="space-y-4">
              <OperationsList operations={operations} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} />
            </TabsContent>

            <TabsContent value="conversion" className="space-y-4">
              <OperationsList operations={conversionOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} />
            </TabsContent>

            <TabsContent value="cleaning" className="space-y-4">
              <OperationsList operations={cleaningOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} />
            </TabsContent>

            <TabsContent value="splitting" className="space-y-4">
              <OperationsList operations={splitOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} />
            </TabsContent>

            <TabsContent value="batch" className="space-y-4">
              <OperationsList operations={batchOps} onProcess={onProcess} isProcessing={isProcessing} files={files} splitSize={splitSize} setSplitSize={setSplitSize} />
            </TabsContent>

            <TabsContent value="custom" className="space-y-4">
              <div className="space-y-4">
                {operations.map((operation) => (
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
        </CardContent>
      </Card>
    </div>
  )
}

function OperationsList({
  operations,
  onProcess,
  isProcessing,
  files,
  splitSize,
  setSplitSize,
}: {
  operations: Operation[]
  onProcess: (operationId: string, size?: number) => Promise<void>
  isProcessing: boolean
  files: WorkspaceFile[]
  splitSize: number
  setSplitSize: (size: number) => void
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
          <Button
            onClick={() => onProcess(operation.id, operation.id === "split_size" ? splitSize : undefined)}
            disabled={files.length === 0 || isProcessing}
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
      return "Convert VATV CSV files to TMX format."
    case "convert_termweb":
      return "Convert TermWeb Excel files to TMX format."
    case "remove_empty":
      return "Remove translation units with empty target segments."
    case "find_duplicates":
      return "Identify and extract duplicate translation units."
    case "non_true_duplicates":
      return "Find segments that are similar but not exact duplicates."
    case "clean_mt":
      return "Clean TMX files for machine translation by removing metadata."
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

