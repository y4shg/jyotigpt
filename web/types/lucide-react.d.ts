// Type shim for lucide-react.
//
// The published 1.30.0 package points `types` at dist/lucide-react.d.ts but
// does not ship the file, so TS falls back to implicit-any. This shim types
// the icon subset the app imports; add icons here as they are introduced.

declare module "lucide-react" {
  import type { ForwardRefExoticComponent, RefAttributes, SVGProps } from "react";

  export interface LucideProps extends SVGProps<SVGSVGElement> {
    size?: number | string;
    absoluteStrokeWidth?: boolean;
  }

  export type LucideIcon = ForwardRefExoticComponent<
    LucideProps & RefAttributes<SVGSVGElement>
  >;

  export const PanelLeft: LucideIcon;
  export const Plus: LucideIcon;
  export const Search: LucideIcon;
  export const MessageSquare: LucideIcon;
  export const Pencil: LucideIcon;
  export const Trash2: LucideIcon;
  export const ChevronDown: LucideIcon;
  export const Loader2: LucideIcon;
  export const Mic: LucideIcon;
  export const Paperclip: LucideIcon;
  export const Send: LucideIcon;
  export const Square: LucideIcon;
  export const Check: LucideIcon;
  export const Copy: LucideIcon;
  export const RefreshCw: LucideIcon;
  export const LogOut: LucideIcon;
  export const Settings: LucideIcon;
  export const Archive: LucideIcon;
  export const ArchiveRestore: LucideIcon;
  export const ChevronRight: LucideIcon;
  export const Folder: LucideIcon;
  export const FolderPlus: LucideIcon;
  export const Link2: LucideIcon;
  export const X: LucideIcon;
  export const Sparkles: LucideIcon;
  export const Download: LucideIcon;
  export const Upload: LucideIcon;
  export const Cable: LucideIcon;
  export const Minus: LucideIcon;
  export const Wrench: LucideIcon;
  export const Info: LucideIcon;
  export const KeyRound: LucideIcon;
  export const UserRound: LucideIcon;
  export const Monitor: LucideIcon;
  export const AudioLines: LucideIcon;
  export const BrainCircuit: LucideIcon;
  export const MessagesSquare: LucideIcon;
  export const Cpu: LucideIcon;
  export const BookOpen: LucideIcon;
  export const Command: LucideIcon;
  export const Code2: LucideIcon;
  export const Play: LucideIcon;
  export const ArrowLeft: LucideIcon;
  export const EllipsisVertical: LucideIcon;
  export const FileText: LucideIcon;
  export const CheckCircle2: LucideIcon;
  export const XCircle: LucideIcon;
  export const Photo: LucideIcon;
  export const Users: LucideIcon;
  export const ShieldCheck: LucideIcon;
  export const ChartColumn: LucideIcon;
  export const Settings2: LucideIcon;
  export const ImageIcon: LucideIcon;
  export const Workflow: LucideIcon;
  export const ChevronUp: LucideIcon;
  export const Sun: LucideIcon;
  export const PencilLine: LucideIcon;
  export const Hash: LucideIcon;
  export const Crown: LucideIcon;
  export const UserPlus: LucideIcon;
  export const UserMinus: LucideIcon;
  export const Globe: LucideIcon;
  export const Lock: LucideIcon;
  export const FlaskConical: LucideIcon;
  export const NotebookPen: LucideIcon;
  export const Volume2: LucideIcon;
  export const VolumeX: LucideIcon;
  export const ArrowUp: LucideIcon;
}
