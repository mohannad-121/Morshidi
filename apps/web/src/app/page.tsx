import { MorshidiSketchbookLandingPage } from "@/components/home/MorshidiSketchbookLandingPage";
import styles from "./home.module.css";

export default function Home() {
  return (
    <main className={styles.page} data-home-sketchbook>
      <MorshidiSketchbookLandingPage className={styles.frame} />
    </main>
  );
}
