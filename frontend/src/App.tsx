import { Navigate, Route, Routes } from "react-router-dom";
import { DEFAULT_PROJECT_SLUG } from "./api";
import Layout from "./Layout";
import ErrorsPage from "./pages/ErrorsPage";
import LoginPage from "./pages/LoginPage";
import NewProjectPage from "./pages/NewProjectPage";
import NotFoundPage from "./pages/NotFoundPage";
import OverviewPage from "./pages/OverviewPage";
import ProjectSettingsPage from "./pages/ProjectSettingsPage";
import ProjectsPage from "./pages/ProjectsPage";
import RegisterPage from "./pages/RegisterPage";
import TestsPage from "./pages/TestsPage";
import RequireAuth from "./components/RequireAuth";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route
        path="/projects"
        element={
          <RequireAuth>
            <ProjectsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/new"
        element={
          <RequireAuth>
            <NewProjectPage />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/:slug/settings"
        element={
          <RequireAuth>
            <ProjectSettingsPage />
          </RequireAuth>
        }
      />

      <Route path="/p/:slug" element={<Layout />}>
        <Route index element={<OverviewPage />} />
        <Route path="tests" element={<TestsPage />} />
        <Route path="tests/:id" element={<TestsPage />} />
        <Route path="errors" element={<ErrorsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      <Route path="/" element={<Navigate to={`/p/${DEFAULT_PROJECT_SLUG}`} replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}