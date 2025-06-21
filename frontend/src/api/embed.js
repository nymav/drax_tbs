// src/api/embed.js
const BASE = import.meta.env.VITE_API_URL;

export async function embedPdf(pdfId) {
  try {
    const response = await fetch(`${BASE}/embed/${pdfId}`, {
      method: "POST",
    });

    if (!response.ok) {
      const errorDetails = await response.text();
      throw new Error(`Embed failed: ${response.status} ${response.statusText}\n${errorDetails}`);
    }

    return await response.json();
  } catch (error) {
    console.error("❌ embedPdf error:", error);
    throw error;
  }
}