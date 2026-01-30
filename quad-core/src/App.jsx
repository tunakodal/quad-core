import { Routes, Route } from "react-router-dom";
import { Header } from "./layout/Header";
import { Footer } from "./layout/Footer";

import { Landing } from "./pages/Landing";
import Planning from "./pages/Planning";
import RoutePage from "./pages/Route";
import Replanning from "./pages/Replanning";
import HowItWorks from "./pages/HowItWorks";
import Poi from "./pages/Poi";

export default function App() {
  return (
    <div className="app-root">
      <Header />

      <main className="app-content">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/planning" element={<Planning />} />
          <Route path="/route" element={<RoutePage />} />
          <Route path="/replanning" element={<Replanning />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/poi/:poiId" element={<Poi />} />
        </Routes>
      </main>

      <Footer />
    </div>
  );
}