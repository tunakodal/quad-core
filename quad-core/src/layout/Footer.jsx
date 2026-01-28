import styles from "./Footer.module.css";

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <span>© {new Date().getFullYear()} GUIDE QUAD-CORE. All rights reserved.</span>
      </div>
    </footer>
  );
}