"use client"

import { useState } from "react"
import type { WorkspaceFile } from "./file-conversion-workspace"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { ImageIcon, FileText, FileCode, FileAudio } from "lucide-react"

interface ConversionPanelProps {
  file: WorkspaceFile
  onConvert: (operation: string, params?: Record<string, any>) => void
}

export function ConversionPanel({ file, onConvert }: ConversionPanelProps) {
  const [activeTab, setActiveTab] = useState("image")
  const isProcessing = file.status === "processing"

  // Determine which tab to show based on file type
  const getInitialTab = () => {
    if (file.type.startsWith("image/")) return "image"
    if (file.type.startsWith("text/")) return "text"
    if (file.type.startsWith("audio/")) return "audio"
    return "general"
  }

  // Set the initial tab when file changes
  useState(() => {
    setActiveTab(getInitialTab())
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Conversion Operations</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid grid-cols-4 mb-4">
            <TabsTrigger value="image" disabled={isProcessing}>
              <ImageIcon className="h-4 w-4 mr-2" />
              <span className="hidden sm:inline">Image</span>
            </TabsTrigger>
            <TabsTrigger value="text" disabled={isProcessing}>
              <FileText className="h-4 w-4 mr-2" />
              <span className="hidden sm:inline">Text</span>
            </TabsTrigger>
            <TabsTrigger value="code" disabled={isProcessing}>
              <FileCode className="h-4 w-4 mr-2" />
              <span className="hidden sm:inline">Code</span>
            </TabsTrigger>
            <TabsTrigger value="audio" disabled={isProcessing}>
              <FileAudio className="h-4 w-4 mr-2" />
              <span className="hidden sm:inline">Audio</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="image" className="space-y-4">
            <ImageConversionOptions file={file} onConvert={onConvert} isProcessing={isProcessing} />
          </TabsContent>

          <TabsContent value="text" className="space-y-4">
            <TextConversionOptions file={file} onConvert={onConvert} isProcessing={isProcessing} />
          </TabsContent>

          <TabsContent value="code" className="space-y-4">
            <CodeConversionOptions file={file} onConvert={onConvert} isProcessing={isProcessing} />
          </TabsContent>

          <TabsContent value="audio" className="space-y-4">
            <AudioConversionOptions file={file} onConvert={onConvert} isProcessing={isProcessing} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

function ImageConversionOptions({
  file,
  onConvert,
  isProcessing,
}: {
  file: WorkspaceFile
  onConvert: (operation: string, params?: Record<string, any>) => void
  isProcessing: boolean
}) {
  const [format, setFormat] = useState("png")
  const [quality, setQuality] = useState([80])
  const [resize, setResize] = useState({ width: 800, height: 600 })

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="format">Format</Label>
          <Select value={format} onValueChange={setFormat} disabled={isProcessing}>
            <SelectTrigger id="format">
              <SelectValue placeholder="Select format" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="png">PNG</SelectItem>
              <SelectItem value="jpg">JPG</SelectItem>
              <SelectItem value="webp">WebP</SelectItem>
              <SelectItem value="gif">GIF</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="quality">Quality: {quality}%</Label>
          <Slider
            id="quality"
            min={1}
            max={100}
            step={1}
            value={quality}
            onValueChange={setQuality}
            disabled={isProcessing}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="width">Width (px)</Label>
          <Input
            id="width"
            type="number"
            value={resize.width}
            onChange={(e) => setResize({ ...resize, width: Number.parseInt(e.target.value) || 0 })}
            disabled={isProcessing}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="height">Height (px)</Label>
          <Input
            id="height"
            type="number"
            value={resize.height}
            onChange={(e) => setResize({ ...resize, height: Number.parseInt(e.target.value) || 0 })}
            disabled={isProcessing}
          />
        </div>
      </div>

      <div className="flex justify-between pt-2">
        <Button
          variant="outline"
          onClick={() => onConvert("resize", { width: resize.width, height: resize.height })}
          disabled={isProcessing}
        >
          Resize Image
        </Button>
        <Button onClick={() => onConvert("convert", { format, quality: quality[0] })} disabled={isProcessing}>
          {isProcessing ? "Processing..." : "Convert Format"}
        </Button>
      </div>
    </div>
  )
}

function TextConversionOptions({
  file,
  onConvert,
  isProcessing,
}: {
  file: WorkspaceFile
  onConvert: (operation: string, params?: Record<string, any>) => void
  isProcessing: boolean
}) {
  const [format, setFormat] = useState("txt")
  const [encoding, setEncoding] = useState("utf8")

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="text-format">Format</Label>
          <Select value={format} onValueChange={setFormat} disabled={isProcessing}>
            <SelectTrigger id="text-format">
              <SelectValue placeholder="Select format" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="txt">Plain Text (.txt)</SelectItem>
              <SelectItem value="md">Markdown (.md)</SelectItem>
              <SelectItem value="html">HTML (.html)</SelectItem>
              <SelectItem value="csv">CSV (.csv)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="encoding">Encoding</Label>
          <Select value={encoding} onValueChange={setEncoding} disabled={isProcessing}>
            <SelectTrigger id="encoding">
              <SelectValue placeholder="Select encoding" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="utf8">UTF-8</SelectItem>
              <SelectItem value="ascii">ASCII</SelectItem>
              <SelectItem value="latin1">Latin-1</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex items-center space-x-2 pt-2">
        <Switch id="normalize" disabled={isProcessing} />
        <Label htmlFor="normalize">Normalize line endings</Label>
      </div>

      <div className="flex justify-between pt-2">
        <Button variant="outline" onClick={() => onConvert("minify", {})} disabled={isProcessing}>
          Minify
        </Button>
        <Button onClick={() => onConvert("convert-text", { format, encoding })} disabled={isProcessing}>
          {isProcessing ? "Processing..." : "Convert Format"}
        </Button>
      </div>
    </div>
  )
}

function CodeConversionOptions({
  file,
  onConvert,
  isProcessing,
}: {
  file: WorkspaceFile
  onConvert: (operation: string, params?: Record<string, any>) => void
  isProcessing: boolean
}) {
  const [language, setLanguage] = useState("javascript")

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="language">Target Language</Label>
        <Select value={language} onValueChange={setLanguage} disabled={isProcessing}>
          <SelectTrigger id="language">
            <SelectValue placeholder="Select language" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="javascript">JavaScript</SelectItem>
            <SelectItem value="typescript">TypeScript</SelectItem>
            <SelectItem value="python">Python</SelectItem>
            <SelectItem value="java">Java</SelectItem>
            <SelectItem value="csharp">C#</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center space-x-2">
        <Switch id="prettify" disabled={isProcessing} />
        <Label htmlFor="prettify">Prettify code</Label>
      </div>

      <div className="flex justify-between pt-2">
        <Button variant="outline" onClick={() => onConvert("minify-code", {})} disabled={isProcessing}>
          Minify
        </Button>
        <Button onClick={() => onConvert("transpile", { language })} disabled={isProcessing}>
          {isProcessing ? "Processing..." : "Transpile"}
        </Button>
      </div>
    </div>
  )
}

function AudioConversionOptions({
  file,
  onConvert,
  isProcessing,
}: {
  file: WorkspaceFile
  onConvert: (operation: string, params?: Record<string, any>) => void
  isProcessing: boolean
}) {
  const [format, setFormat] = useState("mp3")
  const [bitrate, setBitrate] = useState([192])

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="audio-format">Format</Label>
          <Select value={format} onValueChange={setFormat} disabled={isProcessing}>
            <SelectTrigger id="audio-format">
              <SelectValue placeholder="Select format" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="mp3">MP3</SelectItem>
              <SelectItem value="wav">WAV</SelectItem>
              <SelectItem value="ogg">OGG</SelectItem>
              <SelectItem value="flac">FLAC</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="bitrate">Bitrate: {bitrate} kbps</Label>
          <Slider
            id="bitrate"
            min={64}
            max={320}
            step={32}
            value={bitrate}
            onValueChange={setBitrate}
            disabled={isProcessing}
          />
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <Switch id="normalize-audio" disabled={isProcessing} />
        <Label htmlFor="normalize-audio">Normalize audio levels</Label>
      </div>

      <div className="flex justify-between pt-2">
        <Button variant="outline" onClick={() => onConvert("trim", {})} disabled={isProcessing}>
          Trim Silence
        </Button>
        <Button onClick={() => onConvert("convert-audio", { format, bitrate: bitrate[0] })} disabled={isProcessing}>
          {isProcessing ? "Processing..." : "Convert Format"}
        </Button>
      </div>
    </div>
  )
}

