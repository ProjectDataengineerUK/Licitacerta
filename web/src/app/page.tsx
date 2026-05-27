import { Suspense } from "react";
import { DashboardHome } from "@/components/DashboardHome";

export default function HomePage() {
  return (
    <Suspense>
      <DashboardHome />
    </Suspense>
  );
}
