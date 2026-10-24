import type { Metadata } from "next";
import { ChaptersClient } from "./ChaptersClient";

export const metadata: Metadata = {
  title: "شبّاتِر المواد | مرشدي",
  description: "المواد التعليمية المصرّح بها لخطة الطالب الحالية.",
};

export default function ChaptersPage() {
  return <ChaptersClient />;
}
