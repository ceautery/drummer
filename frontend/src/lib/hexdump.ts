export interface HexRow {
  offset: string;
  hex: string;
  ascii: string;
}

export function hexdump(text: string): HexRow[] {
  const bytes = new TextEncoder().encode(text);
  const rows: HexRow[] = [];
  for (let i = 0; i < bytes.length; i += 16) {
    const chunk = Array.from(bytes.slice(i, i + 16));
    const offset = i.toString(16).padStart(8, "0");
    const hex = chunk
      .map((b) => b.toString(16).padStart(2, "0"))
      .join(" ")
      .padEnd(47, " ");
    const ascii = chunk
      .map((b) => (b >= 32 && b < 127 ? String.fromCharCode(b) : "."))
      .join("");
    rows.push({ offset, hex, ascii });
  }
  return rows;
}
