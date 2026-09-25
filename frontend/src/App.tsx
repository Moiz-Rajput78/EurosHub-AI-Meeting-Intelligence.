import {
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import {
  AppLayout,
} from "./components/AppLayout";

import {
  DashboardPage,
} from "./pages/DashboardPage";

import {
  MeetingDetailPage,
} from "./pages/MeetingDetailPage";

import {
  UploadPage,
} from "./pages/UploadPage";


function App() {
  return (
    <Routes>
      <Route
        element={
          <AppLayout />
        }
      >
        <Route
          index
          element={
            <DashboardPage />
          }
        />

        <Route
          path="meetings"
          element={
            <Navigate
              to="/"
              replace
            />
          }
        />

        <Route
          path="meetings/:meetingId"
          element={
            <MeetingDetailPage />
          }
        />

        <Route
          path="upload"
          element={
            <UploadPage />
          }
        />

        <Route
          path="*"
          element={
            <Navigate
              to="/"
              replace
            />
          }
        />
      </Route>
    </Routes>
  );
}


export default App;
