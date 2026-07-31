import axios from "axios";

const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      delete api.defaults.headers.common["Authorization"];
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// Upload helper
export async function uploadMedia(
  questionId: number,
  file: File
): Promise<{
  id: number;
  public_url: string;
  original_filename: string;
  content_type: string;
  file_size: number;
}> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await api.post(
    `/api/v1/media/upload/${questionId}`,
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    }
  );
  return res.data;
}

export async function deleteMedia(mediaId: number): Promise<void> {
  await api.delete(`/api/v1/media/${mediaId}`);
}