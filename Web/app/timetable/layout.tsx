import type { Metadata } from "next";

const TITLE = "จัดตารางเรียน";
const DESCRIPTION =
  "จัดตารางเรียน ม.กรุงเทพ แบบลากวาง — เลือกเซคชัน เช็กเวลาเรียนชนกันอัตโนมัติ หรือเติมตารางจากแผนการเรียนของสาขาในคลิกเดียว ครบทุกคณะ อัปเดตตามเทอมจริง บันทึกให้อัตโนมัติ";
const OG_IMAGE = {
  url: "/banner.png",
  width: 2400,
  height: 1260,
  type: "image/png",
  alt: "OneDegree — จัดตารางเรียน ม.กรุงเทพ"
};

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/timetable/" },
  openGraph: {
    type: "website",
    locale: "th_TH",
    url: "/timetable/",
    siteName: "OneDegree",
    title: `${TITLE} ม.กรุงเทพ · OneDegree`,
    description: DESCRIPTION,
    images: [OG_IMAGE]
  },
  twitter: {
    card: "summary_large_image",
    title: `${TITLE} ม.กรุงเทพ · OneDegree`,
    description: DESCRIPTION,
    images: ["/banner.png"]
  }
};

export default function TimetableLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return children;
}
