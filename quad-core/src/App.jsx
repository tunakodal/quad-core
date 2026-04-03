import { Routes, Route, useLocation } from "react-router-dom";
import { useEffect } from "react";

import { Header } from "./layout/Header";
import { Footer } from "./layout/Footer";

import { Landing } from "./pages/Landing";
import Planning from "./pages/Planning";
import RoutePage from "./pages/Route";
import Replanning from "./pages/Replanning";
import HowItWorks from "./pages/HowItWorks";
import Poi from "./pages/Poi";
import Journey from "./pages/Journey";

/* 🔥 Scroll Component */
function ScrollToTop() {
    const { pathname } = useLocation();

    useEffect(() => {
        window.scrollTo(0, 0);
    }, [pathname]);

    return null;
}

/* App */
export default function App() {
    return (
        <div className="app-root">
            <Header />

            <ScrollToTop />

            <main className="app-content">
                <Routes>
                    <Route path="/" element={<Landing />} />
                    <Route path="/planning" element={<Planning />} />
                    <Route path="/journey" element={<Journey />} />
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