import { TMXWorkspace } from "@/components/tmx-workspace"

export default function Home() {
  return (
    <main className="container mx-auto py-6 px-4 md:px-6 min-h-screen">
      <h1 className="text-3xl font-bold mb-2">Language Data Workbench</h1>
      <p className="text-muted-foreground mb-6">
        Upload TMX, Excel, and XLIFF files and apply multiple operations before downloading
      </p>
      <TMXWorkspace />
    </main>
  )
}

