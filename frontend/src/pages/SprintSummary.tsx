import { useState } from "react";
import { api, getErrorMessage } from "../api/client";

export function SprintSummary() {
  const [sprintId, setSprintId] = useState("");
  const [healthDays, setHealthDays] = useState("14");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState("");

  const handleSprintReport = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const data = await api.sprintSummary.report(Number(sprintId));
      setResult(data.report);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleHealthCheck = async () => {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const data = await api.sprintSummary.health(Number(healthDays));
      setResult(data.report);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Sprint Summary</h1>
      <p className="text-gray-600 mb-8">
        Generate sprint reports or analyze stuck issues.
      </p>

      <div className="grid gap-8 lg:grid-cols-2">
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Sprint Report
            </h2>
            <form onSubmit={handleSprintReport} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Sprint ID
                </label>
                <input
                  type="number"
                  required
                  className="input"
                  value={sprintId}
                  onChange={(e) => setSprintId(e.target.value)}
                  placeholder="123"
                />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? "Generating..." : "Generate Sprint Report"}
              </button>
            </form>
          </div>

          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Health Check
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Days in progress
                </label>
                <input
                  type="number"
                  className="input"
                  value={healthDays}
                  onChange={(e) => setHealthDays(e.target.value)}
                  placeholder="14"
                />
              </div>
              <button
                onClick={handleHealthCheck}
                disabled={loading}
                className="btn-secondary w-full"
              >
                {loading ? "Generating..." : "Generate Health Check"}
              </button>
            </div>
          </div>

          {error && (
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}
        </div>

        <div className="card min-h-[300px]">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Report</h2>
          {result ? (
            <pre className="whitespace-pre-wrap text-sm text-gray-800 bg-gray-50 p-4 rounded-lg">
              {result}
            </pre>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-gray-400">
              Generated report will appear here
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
