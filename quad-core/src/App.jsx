import { Header } from "./layout/Header";
import { Footer } from "./layout/Footer";
import { Landing } from "./pages/Landing";

export default function App() {
  return (
    <div className="app-root">
      <Header />

      <main className="app-content">
        <Landing />
      </main>

      <Footer />
    </div>
  );
}