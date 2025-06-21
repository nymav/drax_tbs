import axios from "axios";

const BASE = import.meta.env.VITE_API_URL; // should be http://localhost:8000/api

export const sendChatQuery = async ({ query, role, pdf_id }) => {
  const res = await axios.post(`${BASE}/chat/`, {
    query,
    role,
    pdf_id
  });
  return res.data;
};