import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/auth";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Enrich } from "./pages/Enrich";
import { TestCases } from "./pages/TestCases";
import { SprintSummary } from "./pages/SprintSummary";
import { Jobs } from "./pages/Jobs";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated() ? <>{children}</> : <Navigate to="/login" replace />;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="enrich" element={<Enrich />} />
        <Route path="test-cases" element={<TestCases />} />
        <Route path="sprint-summary" element={<SprintSummary />} />
        <Route path="jobs" element={<Jobs />} />
      </Route>
    </Routes>
  );
}

export default App;
