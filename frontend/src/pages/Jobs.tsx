import { useEffect, useState } from "react";
import { api, getErrorMessage } from "../api/client";

interface Job {
  id: string;
  service_name: string;
  trigger_type: string;
  status: string;
  created_at: string;
}

const statusColors: Record<string, string> = {
  pending: "bg-yellow-50 text-yellow-700",
  running: "bg-blue-50 text-blue-700",
  done: "bg-green-50 text-green-700",
  failed: "bg-red-50 text-red-700",
};

export function Jobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [jql, setJql] = useState("");
  const [serviceName, setServiceName] = useState("description-enricher");

  const fetchJobs = async () => {
    try {
      const data = await api.gateway.jobs();
      setJobs(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRunJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      await api.gateway.runJob(serviceName, jql || undefined);
      await fetchJobs();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Jobs</h1>
      <p className="text-gray-600 mb-8">
        Trigger and monitor background jobs across services.
      </p>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="card lg:col-span-1">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Run Job</h2>
          <form onSubmit={handleRunJob} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Service
              </label>
              <select
                className="input"
                value={serviceName}
                onChange={(e) => setServiceName(e.target.value)}
              >
                <option value="description-enricher">Description Enricher</option>
                <option value="test-case-generator">Test Case Generator</option>
                <option value="sprint-summary">Sprint Summary</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                JQL
              </label>
              <input
                type="text"
                className="input"
                value={jql}
                onChange={(e) => setJql(e.target.value)}
                placeholder="project = PROJ AND status = 'Ready for QA'"
              />
            </div>
            <button type="submit" className="btn-primary w-full">
              Run Job
            </button>
          </form>

          {error && (
            <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}
        </div>

        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Recent Jobs</h2>
            <button onClick={fetchJobs} className="btn-secondary text-xs">
              Refresh
            </button>
          </div>

          {loading ? (
            <div className="text-sm text-gray-500">Loading...</div>
          ) : jobs.length === 0 ? (
            <div className="text-sm text-gray-500">No jobs yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-xs font-medium text-gray-500">
                    <th className="pb-2 pr-4">Service</th>
                    <th className="pb-2 pr-4">Trigger</th>
                    <th className="pb-2 pr-4">Status</th>
                    <th className="pb-2">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {jobs.map((job) => (
                    <tr key={job.id}>
                      <td className="py-3 pr-4 font-medium text-gray-900">
                        {job.service_name}
                      </td>
                      <td className="py-3 pr-4 text-gray-600">
                        {job.trigger_type}
                      </td>
                      <td className="py-3 pr-4">
                        <span
                          className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                            statusColors[job.status] || "bg-gray-50 text-gray-700"
                          }`}
                        >
                          {job.status}
                        </span>
                      </td>
                      <td className="py-3 text-gray-600">
                        {new Date(job.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
