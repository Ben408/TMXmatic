/** Extensions accepted in the LDW workspace upload drop zone. */
export const WORKSPACE_UPLOAD_EXTENSIONS = [
  // LDW native processing
  "tbx",
  "tmx",
  "xlsx",
  "xls",
  "csv",
  "xliff",
  "xlf",
  "zip",
  // Okapi / tikal document formats (Phase 2)
  "docx",
  "doc",
  "pptx",
  "ppt",
  "html",
  "htm",
  "xml",
  "json",
  "idml",
  "po",
  "properties",
  "srt",
  "vtt",
  "tsv",
  "txt",
  "md",
  "yaml",
  "yml",
] as const

export const WORKSPACE_UPLOAD_ACCEPT = WORKSPACE_UPLOAD_EXTENSIONS.map((ext) => `.${ext}`).join(
  ",",
)

export function isWorkspaceUploadFile(filename: string): boolean {
  const extension = filename.split(".").pop()?.toLowerCase() ?? ""
  return WORKSPACE_UPLOAD_EXTENSIONS.includes(
    extension as (typeof WORKSPACE_UPLOAD_EXTENSIONS)[number],
  )
}

export function filterWorkspaceUploadFiles(files: File[]): {
  accepted: File[]
  rejected: File[]
} {
  const accepted: File[] = []
  const rejected: File[] = []
  for (const file of files) {
    if (isWorkspaceUploadFile(file.name)) accepted.push(file)
    else rejected.push(file)
  }
  return { accepted, rejected }
}
