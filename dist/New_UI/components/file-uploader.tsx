"use client"

import type React from "react"

import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Upload, FileIcon, Download } from "lucide-react"

interface FileUploaderProps {
  onFilesAdded: (files: File[], sourceProject?: {
    integration: "blackbird" | "okapi"
    projectId?: string
    workspaceId?: string
    fileId?: string
  }) => void
}

export function FileUploader({ onFilesAdded }: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    if (e.dataTransfer.files.length > 0) {
      const filesArray = Array.from(e.dataTransfer.files)
      const validFiles = filesArray.filter((file) => {
        const extension = file.name.split(".").pop()?.toLowerCase()
        return ["tbx", "tmx", "xlsx", "xls", "csv", "xliff", "xlf", "zip"].includes(extension || "")
      })

      if (validFiles.length > 0) {
        onFilesAdded(validFiles)
      }
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files)
      const validFiles = filesArray.filter((file) => {
        const extension = file.name.split(".").pop()?.toLowerCase()
        return ["tbx", "tmx", "xlsx", "xls", "csv", "xliff", "xlf", "zip"].includes(extension || "")
      })

      if (validFiles.length > 0) {
        onFilesAdded(validFiles)
      }

      // Reset the input so the same file can be uploaded again if needed
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    }
  }

  const handleButtonClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click()
    }
  }

  const handlePullFromProject = async () => {
    // TODO: Show a dialog to select integration and project/workspace
    // For now, we'll use a simple approach - check settings and use the first enabled integration
    try {
      const settingsResponse = await fetch('http://127.0.0.1:5000/api/settings')
      if (!settingsResponse.ok) {
        alert('Failed to load settings. Please configure your integrations first.')
        return
      }
      
      const settings = await settingsResponse.json()
      
      // Check which integrations are enabled
      let integration: "blackbird" | "okapi" | null = null
      let projectId: string | undefined
      let workspaceId: string | undefined
      
      if (settings.blackbird?.enabled && settings.blackbird?.api_key && settings.blackbird?.project_id) {
        integration = "blackbird"
        projectId = settings.blackbird.project_id
      } else if (settings.okapi?.enabled && settings.okapi?.api_key && settings.okapi?.workspace_id) {
        integration = "okapi"
        workspaceId = settings.okapi.workspace_id
      } else {
        alert('No integrations are configured and enabled. Please configure Blackbird or Okapi in Settings first.')
        return
      }
      
      // Pull files from project
      const pullResponse = await fetch('http://127.0.0.1:5000/api/pull-from-project', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          integration,
          project_id: projectId,
          workspace_id: workspaceId,
        }),
      })
      
      if (!pullResponse.ok) {
        const error = await pullResponse.json()
        alert(`Failed to pull files: ${error.error || 'Unknown error'}`)
        return
      }
      
      const result = await pullResponse.json()
      const fileList = result.files || []
      
      if (fileList.length === 0) {
        alert('No files found in the project.')
        return
      }
      
      // For now, we'll download the first file as an example
      // In a full implementation, you'd show a dialog to select files
      // This is a placeholder - you'll need to implement file download from the API
      alert(`Found ${fileList.length} file(s) in project. Full file selection dialog coming soon.`)
      
    } catch (error) {
      console.error("Error pulling from project:", error)
      alert('Failed to pull files from project. Please check your connection settings.')
    }
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Drag and Drop Section */}
      <Card
        className={`border-2 border-dashed ${isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/20"} transition-colors duration-200`}
      >
        <CardContent className="p-6">
          <div
            className="flex flex-col items-center justify-center py-6 text-center"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="mb-4 rounded-full bg-primary/10 p-4">
              <Upload className="h-8 w-8 text-primary" />
            </div>
            <h3 className="mb-2 text-lg font-semibold">Drag and drop your files</h3>
            <p className="mb-4 text-sm text-muted-foreground">Upload TMX, Excel, CSV, or XLIFF files</p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".tbx,.tmx,.xlsx,.xls,.csv,.xliff,.xlf,.zip"
              className="hidden"
              onChange={handleFileInputChange}
            />
            <Button onClick={handleButtonClick} variant="outline">
              <FileIcon className="mr-2 h-4 w-4" />
              Select Files
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Pull from Project Section */}
      <Card className="border-2 border-dashed border-muted-foreground/20 transition-colors duration-200">
        <CardContent className="p-6">
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <div className="mb-4 rounded-full bg-primary/10 p-4">
              <Download className="h-8 w-8 text-primary" />
            </div>
            <h3 className="mb-2 text-lg font-semibold">Pull from project</h3>
            <p className="mb-4 text-sm text-muted-foreground">Import files from your connected projects</p>
            <Button onClick={handlePullFromProject} variant="outline">
              <Download className="mr-2 h-4 w-4" />
              Pull Files
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

