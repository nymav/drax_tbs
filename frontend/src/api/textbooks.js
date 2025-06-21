const BASE = import.meta.env.VITE_API_URL

export async function fetchTextbooks() {
  const res = await fetch(`${BASE}/textbooks/`)
  if (!res.ok) {
    throw new Error(`Failed to load textbooks: ${res.status}`)
  }
  return res.json()  // expecting array of { filename, title, pages, … }
}