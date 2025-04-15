"use client"

import type { WorkspaceFile } from "./tmx-workspace"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { CheckCircle, XCircle } from "lucide-react"

interface ProcessingHistoryProps {
  file: WorkspaceFile
}

export function ProcessingHistory({ file }: ProcessingHistoryProps) {
  if (file.operations.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Processing History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-center text-muted-foreground">
            <p>No operations have been applied to this file yet.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Processing History</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[250px] pr-4">
          <div className="space-y-4">
            {file.operations.map((operation, index) => (
              <div key={operation.id} className="relative pl-6 pb-4">
                {index < file.operations.length - 1 && (
                  <div className="absolute left-2 top-3 bottom-0 w-0.5 bg-muted-foreground/20" />
                )}
                <div className="absolute left-0 top-2 h-4 w-4 rounded-full border border-primary bg-background" />
                <div className="space-y-1">
                  <div className="flex items-center">
                    <h4 className="font-medium flex items-center">
                      {operation.status === "completed" ? (
                        <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-500 mr-2" />
                      )}
                      {operation.name}
                    </h4>
                    <Badge variant="outline" className="ml-2 text-xs">
                      {formatTimestamp(operation.timestamp)}
                    </Badge>
                  </div>
                  {operation.errorMessage && (
                    <p className="text-sm text-red-500 mt-1">Error: {operation.errorMessage}</p>
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

function formatTimestamp(date: Date): string {
  return new Date(date).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

