import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "破甲评测看板 | Jailbreak Eval",
  description: "跨模型破甲提示词评测：配合率、手法矩阵、多轮漂移与规模对照",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
