import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";

export const dynamic = "force-dynamic";

export async function GET() {
  const p = path.join(process.cwd(), "data", "cases.json");
  if (!fs.existsSync(p)) {
    return NextResponse.json(
      { error: "cases.json not found. Run `make cases` in the repo root." },
      { status: 404 }
    );
  }
  return new NextResponse(fs.readFileSync(p, "utf8"), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}
