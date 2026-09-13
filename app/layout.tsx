import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Summer 27 · AutoApply',
  description: 'A personal workspace for AI, software and machine learning internships.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
