import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./Layout";
import ErrorsPage from "./pages/ErrorsPage";
import NotFoundPage from "./pages/NotFoundPage";
import OverviewPage from "./pages/OverviewPage";
import TestsPage from "./pages/TestsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<OverviewPage />} />
          <Route path="tests" element={<TestsPage />} />
          <Route path="tests/:id" element={<TestsPage />} />
          <Route path="errors" element={<ErrorsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}