import { Suspense } from "react";
import { Cockpit } from "@/components/Cockpit";

export default function HomePage() {
  return (
    <Suspense>
      <Cockpit />
    </Suspense>
  );
}
