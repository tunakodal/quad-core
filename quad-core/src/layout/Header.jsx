import styles from "../styles/Header.module.css";
import logo from "/logo.png?url";
import { Link } from "react-router-dom";

export function Header() {
    return (
        <header className={styles.header}>
            <div className={styles.inner}>

                <Link to="/" className={styles.brand}>
                    <img className={styles.logo} src={logo} alt="GUIDE logo" />
                    <span className={styles.brandText}>GUIDE</span>
                </Link>

                <nav className={styles.nav}>
                    <Link to="/planning">Plan</Link>
                    <Link to="/how-it-works">How GUIDE works</Link>
                </nav>

            </div>
        </header>
    );
}