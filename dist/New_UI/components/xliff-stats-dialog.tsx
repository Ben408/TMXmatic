import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "./ui/dialog"
import { Progress } from "./ui/progress"

interface XLIFFStats {
  translations_found?: number
  updates_made?: number
  remaining_empty?: number
  total_segments?: number
  empty_segments?: number
  completion_rate?: number
}

interface XLIFFStatsDialogProps {
  isOpen: boolean
  onClose: () => void
  stats: XLIFFStats
  operation: "leverage" | "check"
}

export function XLIFFStatsDialog({ isOpen, onClose, stats, operation }: XLIFFStatsDialogProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>
            {operation === "leverage" ? "TMX Leverage Results" : "XLIFF Status Check"}
          </DialogTitle>
          <DialogDescription>
            {operation === "leverage" 
              ? "Results of leveraging TMX translations into XLIFF"
              : "Current translation status of XLIFF file"
            }
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          {operation === "leverage" && (
            <>
              <div className="grid grid-cols-2 items-center gap-4">
                <span className="text-sm">Translations Found:</span>
                <span className="text-sm font-medium">{stats.translations_found}</span>
              </div>
              <div className="grid grid-cols-2 items-center gap-4">
                <span className="text-sm">Updates Made:</span>
                <span className="text-sm font-medium">{stats.updates_made}</span>
              </div>
              <div className="grid grid-cols-2 items-center gap-4">
                <span className="text-sm">Remaining Empty:</span>
                <span className="text-sm font-medium">{stats.remaining_empty}</span>
              </div>
            </>
          )}
          {operation === "check" && (
            <>
              <div className="grid grid-cols-2 items-center gap-4">
                <span className="text-sm">Total Segments:</span>
                <span className="text-sm font-medium">{stats.total_segments}</span>
              </div>
              <div className="grid grid-cols-2 items-center gap-4">
                <span className="text-sm">Empty Segments:</span>
                <span className="text-sm font-medium">{stats.empty_segments}</span>
              </div>
              <div className="flex flex-col gap-2">
                <span className="text-sm">Completion Rate:</span>
                <Progress value={stats.completion_rate} className="w-full" />
                <span className="text-sm text-right">{stats.completion_rate}%</span>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
} 