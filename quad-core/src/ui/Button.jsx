import styles from "./Button.module.css";

export function Button({ variant = "primary", fullWidth, className = "", ...rest }) {
  const cn = [
    styles.btn,
    styles[variant],
    fullWidth ? styles.full : "",
    className,
  ].join(" ");

  return <button type="button" className={cn} {...rest} />;
}