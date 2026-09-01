export type DownloadFormat = "tmx" | "xliff" | "source"

export function getFileExtension(filename: string): string {
  return filename.split(".").pop()?.toLowerCase() || ""
}

export function isTmxOrXliffFile(filename: string): boolean {
  const ext = getFileExtension(filename)
  return ext === "tmx" || ext === "xlf" || ext === "xliff"
}

export function isZipBytes(bytes: Uint8Array): boolean {
  // ZIP files start with PK\x03\x04
  return (
    bytes.length >= 4 &&
    bytes[0] === 0x50 &&
    bytes[1] === 0x4B &&
    bytes[2] === 0x03 &&
    bytes[3] === 0x04
  )
}

export function preferredExtensionsForFormat(format: Exclude<DownloadFormat, "source">): string[] {
  return format === "tmx" ? [".tmx"] : [".xlf", ".xliff"]
}

export function getFileTypeLabel(filename: string): string {
  const extension = getFileExtension(filename)
  switch (extension) {
    case "tmx":
      return "TMX File"
    case "xlsx":
    case "xls":
      return "Excel File"
    case "xliff":
    case "xlf":
      return "XLIFF File"
    case "csv":
      return "CSV File"
    default:
      return extension ? `${extension.toUpperCase()} File` : "Unknown File"
  }
}
