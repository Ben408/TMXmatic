"use client"

import { useState } from "react"
import type { WorkspaceFile, OPERATIONS } from "./tmx-workspace"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2 } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface OperationsPanelProps {
  file: WorkspaceFile
  operations: typeof OPERATIONS
  onProcess: (operationId: string) => void
}

export function OperationsPanel({ file, operations, onProcess }: OperationsPanelProps) {
  const [activeTab, setActiveTab] = useState("all")
  const isProcessing = file.status === "processing"

  // Group operations by category
  const conversionOps = operations.filter((op) => op.id.startsWith("convert_") || op.id.includes("merge"))

  const cleaningOps = operations.filter(
    (op) => op.id.includes("clean") || op.id.includes("empty") || op.id.includes("duplicates"),
  )

  const splitOps = operations.filter((op) => op.id.includes("split"))

  const batchOps = operations.filter((op) => op.id.includes("batch"))

  return (
    <Card>
      <CardHeader>
        <CardTitle>TMX Operations</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid grid-cols-5 mb-4">
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
          </TabsList>

          <TabsContent value="all" className="space-y-4">
            <OperationsList operations={operations} onProcess={onProcess} isProcessing={isProcessing} file={file} />
          </TabsContent>

          <TabsContent value="conversion" className="space-y-4">
            <OperationsList operations={conversionOps} onProcess={onProcess} isProcessing={isProcessing} file={file} />
          </TabsContent>

          <TabsContent value="cleaning" className="space-y-4">
            <OperationsList operations={cleaningOps} onProcess={onProcess} isProcessing={isProcessing} file={file} />
          </TabsContent>

          <TabsContent value="splitting" className="space-y-4">
            <OperationsList operations={splitOps} onProcess={onProcess} isProcessing={isProcessing} file={file} />
          </TabsContent>

          <TabsContent value="batch" className="space-y-4">
            <OperationsList operations={batchOps} onProcess={onProcess} isProcessing={isProcessing} file={file} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

function OperationsList({
  operations,
  onProcess,
  isProcessing,
  file,
}: {
  operations: typeof OPERATIONS
  onProcess: (operationId: string) => void
  isProcessing: boolean
  file: WorkspaceFile
}) {
  // Check if operation has already been applied to this file
  const isOperationApplied = (opId: string) => {
    return file.operations.some((op) => op.name === operations.find((o) => o.id === opId)?.name)
  }

  const needsTMXFile = (opId: string) => opId === "xliff_tmx_leverage"

  return (
    <Accordion type="single" collapsible className="w-full">
      {operations.map((op) => (
        <AccordionItem key={op.id} value={op.id}>
          <AccordionTrigger className="hover:bg-muted/50 px-4 rounded-md">
            <div className="flex items-center justify-between w-full pr-4">
              <span>{op.name}</span>
              {isOperationApplied(op.id) && (
                <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">Applied</span>
              )}
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-4 pt-2">
            <p className="text-sm text-muted-foreground mb-4">{getOperationDescription(op.id)}</p>
            {needsTMXFile(op.id) && (
              <div className="mb-4">
                <Select
                  onValueChange={(tmxId) => {
                    setFiles((prev) =>
                      prev.map((f) =>
                        f.id === file.id
                          ? { ...f, relatedFiles: { ...f.relatedFiles, tmxFile: tmxId } }
                          : f
                      )
                    )
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select TMX file" />
                  </SelectTrigger>
                  <SelectContent>
                    {files
                      .filter((f) => f.name.toLowerCase().endsWith('.tmx'))
                      .map((f) => (
                        <SelectItem key={f.id} value={f.id}>
                          {f.name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <Button onClick={() => onProcess(op.id)} disabled={isProcessing} className="w-full">
              {isProcessing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>Apply {op.name}</>
              )}
            </Button>
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
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

export const OPERATIONS = [
  // ... existing operations ...
  {
    id: "xliff_tmx_leverage",
    name: "Leverage TMX into XLIFF",
    description: "Apply translations from a TMX file to an XLIFF file",
    requiresFiles: ["xliff", "tmx"],
  },
  {
    id: "xliff_check",
    name: "Check XLIFF Status",
    description: "Check the translation status of an XLIFF file",
    requiresFiles: ["xliff"],
  },
] as const

const isValidFileType = (file: File, operation: typeof OPERATIONS[number]) => {
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

