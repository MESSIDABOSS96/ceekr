import { ResultCard } from "@/components/result-card";
import { MOCK_ACCOUNTS } from "./mock-data";

export default function PreviewPage() {
  return (
    <div className="min-h-screen bg-background pb-16">
      <div className="mx-auto max-w-2xl px-4">
        <div className="flex flex-col items-center pt-10 pb-8">
          <h1 className="font-mono-display text-2xl font-bold text-text-primary">
            Card Preview
          </h1>
          <p className="mt-2 text-sm text-text-muted">
            5 mock accounts — design iteration page
          </p>
        </div>

        <div className="space-y-4">
          {MOCK_ACCOUNTS.map((account) => (
            <ResultCard key={account.user_id} account={account} />
          ))}
        </div>
      </div>
    </div>
  );
}
