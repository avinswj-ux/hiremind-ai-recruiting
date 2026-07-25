import { unzipSync } from "fflate";
import { extractText, getDocumentProxy } from "unpdf";

const xmlEntities: Record<string, string> = {
  amp: "&",
  lt: "<",
  gt: ">",
  quot: '"',
  apos: "'",
};

function decodeXml(value: string) {
  return value.replace(/&(?:amp|lt|gt|quot|apos);/g, (entity) => {
    return xmlEntities[entity.slice(1, -1)] || entity;
  });
}

async function extractDocx(buffer: Uint8Array) {
  const files = unzipSync(buffer);
  const xml = files["word/document.xml"];
  if (!xml) throw new Error("DOCX 中未找到正文");
  return decodeXml(
    new TextDecoder()
      .decode(xml)
      .replace(/<\/w:p>/g, "\n")
      .replace(/<w:tab\/>/g, "\t")
      .replace(/<[^>]+>/g, ""),
  );
}

export async function extractResumeText(file: File) {
  const suffix = file.name.toLowerCase().split(".").pop();
  const bytes = new Uint8Array(await file.arrayBuffer());
  if (suffix === "txt") return new TextDecoder().decode(bytes);
  if (suffix === "docx") return extractDocx(bytes);
  if (suffix === "pdf") {
    const pdf = await getDocumentProxy(bytes);
    const result = await extractText(pdf, { mergePages: true });
    return String(result.text || "");
  }
  throw new Error("仅支持 PDF、DOCX、TXT");
}

export async function sha256(value: Uint8Array) {
  const digest = await crypto.subtle.digest("SHA-256", value);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}
