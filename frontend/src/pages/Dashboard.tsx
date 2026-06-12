import { Link } from "react-router-dom";

const services = [
  {
    title: "Enrich Description",
    description: "Generate structured descriptions for Jira tickets using AI.",
    path: "/enrich",
    color: "bg-blue-50 text-blue-700",
  },
  {
    title: "Test Cases",
    description: "Generate positive, negative, edge case and integration tests.",
    path: "/test-cases",
    color: "bg-green-50 text-green-700",
  },
  {
    title: "Sprint Summary",
    description: "Generate sprint reports and health check analysis.",
    path: "/sprint-summary",
    color: "bg-purple-50 text-purple-700",
  },
  {
    title: "Job History",
    description: "View and trigger background jobs across services.",
    path: "/jobs",
    color: "bg-orange-50 text-orange-700",
  },
];

export function Dashboard() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Dashboard</h1>
      <p className="text-gray-600 mb-8">Choose a tool to work with your Jira tickets.</p>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {services.map((service) => (
          <Link
            key={service.path}
            to={service.path}
            className="card hover:shadow-md transition-shadow group"
          >
            <div
              className={`inline-flex rounded-lg px-3 py-1 text-xs font-semibold mb-4 ${service.color}`}
            >
              {service.title}
            </div>
            <p className="text-sm text-gray-600">{service.description}</p>
            <div className="mt-4 flex items-center text-sm font-medium text-primary-600 group-hover:text-primary-700">
              Open
              <svg
                className="ml-1 h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </div>
          </Link>
        ))}
      </div>

      <div className="mt-12 card">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">How it works</h2>
        <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
          <li>Enter a Jira issue key or JQL query.</li>
          <li>AI analyzes the ticket context (summary, description, epic).</li>
          <li>Get a structured result: description, test cases, or sprint report.</li>
          <li>Results can be applied back to Jira or copied for manual use.</li>
        </ol>
      </div>
    </div>
  );
}
