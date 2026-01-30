import styles from "./Header.module.css";
import logo from "/logo.png?url";
import { Link } from "react-router-dom";

export function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link to="/" className={styles.brand} aria-label="Go to landing page">
          <img className={styles.logo} src={logo} alt="GUIDE logo" />
          <span className={styles.brandText}>GUIDE</span>
        </Link>
      </div>
    </header>
  );
}