import { notFound } from "next/navigation";
import { VoiceMascotPreview } from "@/components/voice/dev/VoiceMascotPreview";

export default function VoiceMascotPreviewPage() {
  if (process.env.NODE_ENV !== "development") {
    notFound();
  }

  return <VoiceMascotPreview />;
}
