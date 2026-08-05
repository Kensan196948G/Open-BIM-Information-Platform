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
  async (error) => {
    if (error.response?.status === 401) {
      const original = error.config as (typeof error.config & { _retried?: boolean }) | undefined;
      const url = original?.url ?? "";
      const isAuthCall = url.includes("/auth/login") || url.includes("/auth/refresh");
      const refreshToken = localStorage.getItem("refresh_token");
      if (
        original &&
        !original._retried &&
        !isAuthCall &&
        refreshToken
      ) {
        original._retried = true;
        try {
          const refreshRes = await api.post<{
            access_token: string;
            refresh_token: string;
          }>("/auth/refresh", { refresh_token: refreshToken });
          localStorage.setItem("access_token", refreshRes.data.access_token);
          localStorage.setItem("refresh_token", refreshRes.data.refresh_token);
          original.headers = {
            ...original.headers,
            Authorization: `Bearer ${refreshRes.data.access_token}`,
          };
          return api(original);
        } catch {
          // fall through to logout redirect
        }
      }
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
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
