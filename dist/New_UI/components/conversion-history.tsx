"use client"

import type { WorkspaceFile } from "./file-conversion-workspace"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"

interface ConversionHistoryProps {
  file: WorkspaceFile
}

export function ConversionHistory({ file }: ConversionHistoryProps) {
  if (file.history.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Conversion History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-center text-muted-foreground">
            <p>No conversions applied yet.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Conversion History</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[250px] pr-4">
          <div className="space-y-4">
            {file.history.map((step, index) => (
              <div key={step.id} className="relative pl-6 pb-4">
                {index < file.history.length - 1 && (
                  <div className="absolute left-2 top-3 bottom-0 w-0.5 bg-muted-foreground/20" />
                )}
                <div className="absolute left-0 top-2 h-4 w-4 rounded-full border border-primary bg-background" />
                <div className="space-y-1">
                  <div className="flex items-center">
                    <h4 className="font-medium">{formatOperationName(step.operation)}</h4>
                    <Badge variant="outline" className="ml-2 text-xs">
                      {formatTimestamp(step.timestamp)}
                    </Badge>
                  </div>
                  {step.params && Object.keys(step.params).length > 0 && (
                    <div className="text-sm text-muted-foreground">
                      {Object.entries(step.params).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between">
                          <span className="capitalize">{key}:</span>
                          <span className="font-mono">{formatParamValue(value)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}

function formatOperationName(operation: string): string {
  return operation
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

function formatTimestamp(date: Date): string {
  return new Date(date).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function formatParamValue(value: any): string {
  if (typeof value === "object") {
    return JSON.stringify(value)
  }
  return String(value)
}

