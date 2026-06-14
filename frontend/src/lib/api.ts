import axios from "axios";
import { getMockResponse } from "./mockRouter";

export const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

if (import.meta.env.VITE_MOCK_MODE === "true") {
  api.interceptors.response.use(
    // When real backend responds, replace with mock data
    (response) => {
      const url = response.config?.url ?? "";
      const method = response.config?.method ?? "get";
      const mock = getMockResponse(url, method, response.config?.data);
      if (mock !== undefined) return { ...response, data: mock };
      return response;
    },
    // When no backend (network error), return mock data
    (error) => {
      if (error.config?.url === "/auth/login") {
        return Promise.reject(error); // Let login page handle auth errors
      }
      const url = (error.config?.url as string | undefined) ?? "";
      const method = (error.config?.method as string | undefined) ?? "get";
      const mock = getMockResponse(url, method, error.config?.data);
      if (mock !== undefined) {
        return Promise.resolve({
          data: mock,
          status: 200,
          headers: {},
          config: error.config,
        });
      }
      return Promise.reject(error);
    },
  );
}
