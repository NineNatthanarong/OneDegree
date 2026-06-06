import type { Metadata, Viewport } from "next";
import "./globals.css";

const SITE_URL = "https://bu.need.cat";
const TITLE = "OneDegree · แผนที่หลักสูตร";
const DESCRIPTION =
  "OneDegree — แผนที่หลักสูตรแบบโต้ตอบได้ เห็นเส้นทางการเรียนทั้งหมด ลากปรับได้ ถอนวิชาแล้วเห็นผลกระทบทันที";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: TITLE,
    template: "%s · OneDegree"
  },
  description: DESCRIPTION,
  applicationName: "OneDegree",
  keywords: [
    "OneDegree",
    "แผนที่หลักสูตร",
    "หลักสูตร",
    "วิชาก่อนหลัง",
    "Bangkok University",
    "มหาวิทยาลัยกรุงเทพ",
    "degree plan",
    "curriculum map"
  ],
  authors: [{ name: "OneDegree" }],
  icons: {
    icon: [
      { url: "/logo.ico", sizes: "any" },
      { url: "/logo.png", type: "image/png", sizes: "1254x1254" }
    ],
    shortcut: "/logo.ico",
    apple: "/logo.png"
  },
  openGraph: {
    type: "website",
    locale: "th_TH",
    url: SITE_URL,
    siteName: "OneDegree",
    title: TITLE,
    description: DESCRIPTION,
    images: [
      {
        url: "/banner.png",
        width: 1448,
        height: 1086,
        alt: "OneDegree — แผนที่หลักสูตร"
      }
    ]
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
    images: ["/banner.png"]
  }
};

export const viewport: Viewport = {
  themeColor: "#3F194B",
  colorScheme: "light",
  width: "device-width",
  initialScale: 1
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="th">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin=""
        />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@100;200;300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
