import styles from "./Landing.module.css";
import logo from "../assets/logo.png";
import { Button } from "../ui/Button";

const letters = ["G", "U", "I", "D", "E"];

export function Landing() {
  return (
    <div className={styles.page}>
      <div className={styles.hero}>

        <div className={styles.brandRow} aria-label="GUIDE brand">
          <img className={styles.logo} src={logo} alt="GUIDE logo" />

          <h1 className={styles.title} aria-label="GUIDE">
            {letters.map((ch, i) => (
              <span
                key={`${ch}-${i}`}
                className={styles.letter}
                style={{ animationDelay: `${300 * i}ms` }}
              >
                {ch}
              </span>
            ))}
          </h1>
        </div>

        <p className={styles.subtitle}>
            Welcome to the Guided User Itinerary & Destination Explorer
        </p>

        <div className={styles.actions}>
          <Button className={styles.primaryBtn}>Start Planning</Button>
          <Button variant="ghost" className={styles.ghostBtn}>How it works</Button>
        </div>

      </div>
    </div>
  );
}