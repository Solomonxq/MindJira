import { useState } from "react";
import { api, getErrorMessage } from "../api/client";

export function TestCases() {
  const [issueKey, setIssueKey] = useState("");
  const [language, setLanguage] = useState("uk");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const data = await api.testCases.generate(issueKey, language);
      setResult(data.test_cases_markdown);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Test Cases</h1>
      <p className="text-gray-600 mb-8">
        Generate a full set of test cases for a Jira ticket.
      </p>

      <div className="grid gap-8 lg:grid-cols-2">
        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Issue Key
              </label>
              <input
                type="text"
                required
                className="input"
                value={issueKey}
                onChange={(e) => setIssueKey(e.target.value.toUpperCase())}
                placeholder="PROJ-123"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Language
              </label>
              <select
                className="input"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              >
                <option value="uk">Ukrainian</option>
                <option value="en">English</option>
              </select>
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? "Generating..." : "Generate Test Cases"}
            </button>
          </form>

          {error && (
            <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}
        </div>

        <div className="card min-h-[300px]">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Result</h2>
          {result ? (
            <pre className="whitespace-pre-wrap text-sm text-gray-800 bg-gray-50 p-4 rounded-lg">
              {result}
            </pre>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-gray-400">
              Generated test cases will appear here
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
