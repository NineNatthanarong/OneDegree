import type { Metadata, Viewport } from "next";
import "./globals.css";

const SITE_URL = "https://onedegree.wiki";
const TITLE = "OneDegree — แผนที่หลักสูตร & ตารางเรียน ม.กรุงเทพ";
const DESCRIPTION =
  "วางแผนการเรียน ม.กรุงเทพ ครบในที่เดียว — แผนที่หลักสูตรอินเทอร์แอกทีฟ เห็นวิชาตัวก่อน–ตัวตามทั้งเส้นทาง ลองถอนหรือย้ายวิชาแล้วเห็นผลทันที พร้อมจัดตารางเรียนอัตโนมัติ เช็กเวลาชนก่อนลงทะเบียน ใช้ฟรีทุกคณะ";
const OG_IMAGE = {
  url: "/banner.png",
  width: 2400,
  height: 1260,
  type: "image/png",
  alt: "OneDegree — เห็นทั้งเส้นทางการเรียน จากปี 1 สู่วันรับปริญญา"
};

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: TITLE,
    template: "%s · OneDegree"
  },
  description: DESCRIPTION,
  applicationName: "OneDegree",
  category: "education",
  keywords: [
    "OneDegree",
    "แผนที่หลักสูตร",
    "แผนการเรียน",
    "ตารางเรียน",
    "จัดตารางเรียน",
    "วางแผนการเรียน",
    "วิชาตัวก่อน–ตัวตาม",
    "ลงทะเบียนเรียน",
    "มหาวิทยาลัยกรุงเทพ",
    "ม.กรุงเทพ",
    "Bangkok University",
    "BU",
    "degree plan",
    "curriculum map",
    "timetable planner"
  ],
  authors: [{ name: "OneDegree" }],
  creator: "OneDegree",
  publisher: "OneDegree",
  alternates: { canonical: "/" },
  icons: {
    // Tab icon: ICO only — a giant detailed PNG here makes browsers render
    // an unreadable 16px smudge instead of the hand-tuned small sizes.
    icon: [{ url: "/logo.ico", sizes: "any" }],
    shortcut: "/logo.ico",
    apple: "/logo.png"
  },
  openGraph: {
    type: "website",
    locale: "th_TH",
    url: "/",
    siteName: "OneDegree",
    title: TITLE,
    description: DESCRIPTION,
    images: [OG_IMAGE]
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

const JSON_LD = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "OneDegree",
  url: SITE_URL,
  description: DESCRIPTION,
  applicationCategory: "EducationalApplication",
  operatingSystem: "Web",
  inLanguage: "th",
  isAccessibleForFree: true,
  about: {
    "@type": "CollegeOrUniversity",
    name: "มหาวิทยาลัยกรุงเทพ",
    alternateName: "Bangkok University"
  }
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
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
