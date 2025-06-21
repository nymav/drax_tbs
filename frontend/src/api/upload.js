import axios from "axios";
const BASE = import.meta.env.VITE_API_URL;

export async function uploadPdf(file) {
  const form = new FormData();
  form.append("file", file);

  const res = await axios.post(`${BASE}/uploads`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return res.data;
}