import styles from "./Header.module.css";
import logo from "../assets/logo.png?url";

export function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <div className={styles.brand}>
          <img src={logo} alt="Guide logo" className={styles.logo} />
          <span>GUIDE</span>
        </div>
      </div>
    </header>
  );
}