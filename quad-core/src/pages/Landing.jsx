import styles from "./Landing.module.css";
import logo from "/logo.png";
import { Button } from "../ui/Button";
import { useNavigate } from "react-router-dom";

const letters = ["G", "U", "I", "D", "E"];

export function Landing() {
  const navigate = useNavigate();
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
          <Button
              className={styles.primaryBtn}
              onClick={() => navigate("/planning")}
            >
              Start Planning
          </Button>
          <Button
            variant="ghost"
            className={styles.ghostBtn}
            onClick={() => navigate("/how-it-works")}
          >
            How GUIDE Works
        </Button>
        </div>

      </div>
    </div>
  );
}