import { ReactNode } from 'react';
import Head from 'next/head';
import styles from './Layout.module.css';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className={styles.layout}>
      <Head>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0"/>
        <meta name="description" content="Dayak Kenyah Translator - Online Translation Engine" />
        <meta name="keywords" content="Dayak Kenyah, Translator, Online, Language" />
        <meta name="author" content="Muhammad Rizky Saputra" />
      </Head>
      {children}
    </div>
  );
}
