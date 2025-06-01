import { useEffect, useState } from 'react';
import styles from './Preloader.module.css';

export default function Preloader() {
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setHidden(true);
      document.body.classList.add('loaded');
    }, 3000);

    return () => clearTimeout(timer);
  }, []);

  if (hidden) return null;

  return (
    <div id="interactive-preloader" className={styles.preloader}>
      <div className={styles.preloaderCanvasContainer}>
        <canvas id="preloader-canvas"></canvas>
      </div>
      <div className={styles.preloaderContent}>
        <div className={styles.preloaderTitle}>Dayak Kenyah Translator Pro</div>
        <div className={styles.preloaderMessage}>Dari ide kecil lahirlah dampak besar bagi banyak orang.</div>
        <div className={styles.loadingDots}>
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>
  );
}
