import { Outlet } from "react-router-dom";
import styles from "./AppShell.module.css";
import { Header } from "./Header";
import { Footer } from "./Footer";

export function AppShell() {
  return (
    <div className={styles.shell}>
      <Header />
      <main className={styles.main}>
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}