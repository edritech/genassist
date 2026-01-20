import { apiRequest } from "@/config/api";
import {
  Webhook,
  WebhookCreatePayload,
  WebhookUpdatePayload,
} from "@/interfaces/webhook.interface";

const BASE = "webhooks";

export const getAllWebhooks = async (): Promise<Webhook[]> => {
  const data = await apiRequest<Webhook[]>("GET", `${BASE}`);
  if (!data || !Array.isArray(data)) {
    return [];
  }
  return data;
};

export const getWebhook = async (id: string): Promise<Webhook | null> => {
  const data = await apiRequest<Webhook>("GET", `${BASE}/${id}`);
  return data ?? null;
};

export const createWebhook = async (
  webhookData: WebhookCreatePayload
): Promise<Webhook> => {
  const response = await apiRequest<Webhook>("POST", `${BASE}`, webhookData as unknown as Record<string, unknown>);
  if (!response) throw new Error("Failed to create webhook");
  return response;
};

export const updateWebhook = async (
  id: string,
  webhookData: WebhookUpdatePayload
): Promise<Webhook> => {
  const response = await apiRequest<Webhook>("PUT", `${BASE}/${id}`, webhookData as unknown as Record<string, unknown>);
  if (!response) throw new Error("Failed to update webhook");
  return response;
};

export const deleteWebhook = async (id: string): Promise<void> => {
  await apiRequest("DELETE", `${BASE}/${id}`);
};

export const executeWebhook = async (
  id: string,
  payload: Record<string, unknown>,
  method: "POST" | "GET" = "POST"
): Promise<unknown> => {
  const url = `${BASE}/${id}/execute-workflow`;
  if (method === "POST") {
    return await apiRequest("POST", url, payload);
  } else {
    return await apiRequest("GET", url, payload);
  }
};
