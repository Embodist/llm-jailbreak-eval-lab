import Dashboard from "@/components/Dashboard";
import type { Results } from "@/lib/types";
import results from "../data/results.json";

export default function Page() {
  return <Dashboard data={results as unknown as Results} />;
}
