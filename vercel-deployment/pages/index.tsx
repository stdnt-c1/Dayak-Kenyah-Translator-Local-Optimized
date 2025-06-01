import { useEffect, useState } from 'react';
import Head from 'next/head';
import Image from 'next/image';
import Layout from '../components/Layout';
import Preloader from '../components/Preloader';
import styles from '../styles/Home.module.css';

export default function Home() {
  const [theme, setTheme] = useState('light');
  const [currentLang, setCurrentLang] = useState('Bahasa Indonesia');
  const [targetLang, setTargetLang] = useState('Dayak Kenyah');
  const [inputText, setInputText] = useState('');
  const [outputText, setOutputText] = useState('Hasil terjemahan akan muncul di sini.');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Initialize theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
  };

  const swapLanguage = () => {
    setCurrentLang(targetLang);
    setTargetLang(currentLang);
    if (outputText !== 'Hasil terjemahan akan muncul di sini.') {
      setInputText(outputText);
      setOutputText(inputText);
    }
  };

  const translateText = async () => {
    if (!inputText.trim()) return;
    
    setIsLoading(true);
    try {      const sourceLang = currentLang === 'Bahasa Indonesia' ? 'id' : 'dyk';
      const targetLang = sourceLang === 'id' ? 'dyk' : 'id';
      
      const response = await fetch('/api/translate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          client: "web",
          requestId: Date.now().toString(),
          timestamp: new Date().toISOString(),
          payload: {
            sourceLang,
            targetLang,
            text: inputText.trim(),
            options: {
              preserveFormatting: true,
              preservePunctuation: true,
              caseSensitive: false
            }
          }
        }),
      });      const data = await response.json();
      if (data.status === 'error' || data.error) {
        throw new Error(data.error?.message || 'Translation failed');
      }
      if (data.payload?.translatedText) {
        setOutputText(data.payload.translatedText);
      } else {
        throw new Error('Invalid response format');
      }
    } catch (error) {
      console.error('Translation error:', error);
      setOutputText('Terjadi kesalahan saat menerjemahkan.');
    } finally {
      setIsLoading(false);
    }
  };

  const selectTranslatedText = () => {
    const selection = window.getSelection();
    const range = document.createRange();
    const outputElement = document.getElementById('outputText');
    if (outputElement) {
      range.selectNodeContents(outputElement);
      selection?.removeAllRanges();
      selection?.addRange(range);
      try {
        document.execCommand('copy');
        const btn = document.querySelector('.select-text-btn');
        const originalText = btn?.innerHTML || '';
        if (btn) {
          btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg> Tersalin!';
          setTimeout(() => btn.innerHTML = originalText, 2000);
        }
      } catch (err) {
        console.log('Copy not supported');
      }
    }
  }; 
    return (
    <>
      <Preloader />
      <Layout>
        <div className={styles.container}>
          <Head>          <title>Translator & Engine Dayak Kenyah - Online</title>
          <meta name="description" content="Dayak Kenyah Translator - Online Translation Engine" />
          <meta name="keywords" content="Dayak Kenyah, Translator, Online, Language" />
          <meta name="author" content="Muhammad Rizky Saputra" />          <link rel="icon" href="/favicon.ico" />
          <link rel="apple-touch-icon" sizes="180x180" href="/icon.png" as="image" />
          <link rel="preload" href="/icon.png" as="image" />
          <link rel="icon" type="image/png" sizes="32x32" href="/icon.png" />
          </Head>

          <div className={styles.themeToggle} onClick={toggleTheme} title="Ganti Tema">
            <span>{theme === 'dark' ? '☀️' : '🌙'}</span>
          </div>

          <main className={styles.main}>          <header className={styles.header}>
            <div className={styles.logoContainer}>
              <Image
                src="/icon.png"
                alt="DKT Logo"
                width={48}
                height={48}
                className={styles.logo}
                priority
              />
              <div className={styles.textLogo}>DKT</div>
            </div>
            <h1 className={styles.headerTitle}>Dayak Kenyah Translator Pro</h1>
            <p className={styles.description}>Translator Antarmuka Online.</p>
          </header>

            <section className={styles.card}>
              <h2><span aria-hidden="true">🔄</span> Translator</h2>
              <div className={styles.translatorContainer}>
                <div className={styles.inputArea}>
                  <p><strong>Translate dari:</strong> <span>{currentLang}</span></p>
                  <textarea
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Tulis teks di sini untuk diterjemahkan..."
                    rows={1}
                  />
                </div>
                
                <div className={styles.swapButtonContainer}>
                  <button onClick={swapLanguage} className={styles.swapButton} title="Ganti Bahasa">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24px" height="24px">
                      <path d="M8.99991 5.00006V9.00006L1.99991 9.00006L1.99991 11.0001L8.99991 11.0001V15.0001L14.9999 10.0001L8.99991 5.00006zM15.9999 19.0001V15.0001L22.9999 15.0001V13.0001L15.9999 13.0001L15.9999 9.00006L9.99991 14.0001L15.9999 19.0001z"/>
                    </svg>
                  </button>
                </div>

                <div className={styles.outputArea}>
                  <p><strong>Terjemahan ke:</strong> <span>{targetLang}</span></p>                  <div className={styles.output} id="outputText" tabIndex={0} style={{ whiteSpace: 'pre-wrap' }}>
                    {outputText}
                  </div>
                  <button onClick={selectTranslatedText} className={`${styles.selectTextBtn} select-text-btn`} title="Pilih semua teks">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                      <path d="M9 9V5.5C9 3.57 10.57 2 12.5 2H16.5C18.43 2 20 3.57 20 5.5V9H9ZM7 9H4.5C2.57 9 1 10.57 1 12.5V16.5C1 18.43 2.57 20 4.5 20H8V9H7ZM20 11V16.5C20 18.43 18.43 20 16.5 20H12.5C10.57 20 9 18.43 9 16.5V11H20Z"/>
                    </svg>
                    Pilih Semua Teks
                  </button>
                </div>
              </div>
              
              <div className={styles.buttonGroup}>
                <button onClick={translateText} className={styles.primary}>
                  Terjemahkan
                </button>
              </div>
              
              {isLoading && <div className={styles.loader} />}
            </section>

            <footer className={styles.footer}>
              <div className={styles.footerContent}>
                <div className={styles.footerSection}>
                  <h3 className={styles.footerTitle}>Tentang Proyek</h3>
                  <p className={styles.footerText}>Dayak Kenyah Translator Pro adalah proyek open source untuk melestarikan bahasa Dayak Kenyah melalui teknologi modern.</p>
                </div>
                <div className={styles.footerSection}>
                  <h3 className={styles.footerTitle}>Pengembang</h3>
                  <p className={styles.footerText}>© ESP32 Ver. Author: Muhammad Rizky Saputra <a className={styles.footerLink} href="https://github.com/RyuHiiragi/Dayak-Kenyah-Translator-ESP-32.git">GitHub Repository</a></p>
                  <p className={styles.footerText}>© Local Host Ver. Author: Muhammad Bilal Maulida <a className={styles.footerLink} href="https://github.com/stdnt-c1/Dayak-Kenyah-Translator-Local-Optimized.git">GitHub Repository</a></p>
                </div>
                <div className={styles.footerSection}>
                  <h3 className={styles.footerTitle}>Institusi</h3>
                  <p className={styles.footerText}>XI TJKT 2, 2025</p>
                  <p className={styles.footerText}>SMK Negeri 7 Samarinda</p>
                </div>
                <div className={`${styles.footerSection} ${styles.social}`}>
                  <h3 className={styles.footerTitle}>Sosial Media</h3>
                  <a href="#" className={styles.instagramLink}>
                    <svg className={styles.instagramIcon} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 2c2.717 0 3.056.01 4.122.06 1.065.05 1.79.217 2.428.465.66.254 1.216.598 1.772 1.153.509.5.902 1.105 1.153 1.772.247.637.415 1.363.465 2.428.047 1.066.06 1.405.06 4.122 0 2.717-.01 3.056-.06 4.122-.05 1.065-.218 1.79-.465 2.428a4.883 4.883 0 0 1-1.153 1.772c-.5.508-1.105.902-1.772 1.153-.637.247-1.363.415-2.428.465-1.066.047-1.405.06-4.122.06-2.717 0-3.056-.01-4.122-.06-1.065-.05-1.79-.218-2.428-.465a4.89 4.89 0 0 1-1.772-1.153 4.904 4.904 0 0 1-1.153-1.772c-.248-.637-.415-1.363-.465-2.428C2.013 15.056 2 14.717 2 12c0-2.717.01-3.056.06-4.122.05-1.066.217-1.79.465-2.428a4.88 4.88 0 0 1 1.153-1.772A4.897 4.897 0 0 1 5.45 2.525c.638-.248 1.362-.415 2.428-.465C8.944 2.013 9.283 2 12 2zm0 5a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm6.5-.25a1.25 1.25 0 1 0-2.5 0 1.25 1.25 0 0 0 2.5 0zM12 9a3 3 0 1 1 0 6 3 3 0 0 1 0-6z"/>
                    </svg>
                    <span className={styles.instagramText}>@kysukamieayam</span>
                  </a>
                </div>
              </div>
              <div className={styles.footerBottom}>
                <p className={styles.footerText}>© 2025 Dayak Kenyah Translator Pro. Licensed under MIT License.</p>
              </div>
            </footer>
          </main>
        </div>
      </Layout>
    </>
  );
}
