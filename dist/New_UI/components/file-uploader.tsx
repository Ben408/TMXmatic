"use client"

import type React from "react"

import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Upload, FileIcon } from "lucide-react"

interface FileUploaderProps {
  onFilesAdded: (files: File[]) => void
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

  return (
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
  )
}

