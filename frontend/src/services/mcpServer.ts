import { apiRequest } from "@/config/api";
import {
  MCPServer,
  MCPServerCreatePayload,
  MCPServerUpdatePayload,
} from "@/interfaces/mcp-server.interface";

const BASE = "mcp-servers";

export const getAllMCPServers = async (): Promise<MCPServer[]> => {
  const data = await apiRequest<MCPServer[]>("GET", `${BASE}`);
  if (!data || !Array.isArray(data)) {
    return [];
  }
  return data;
};

export const getMCPServer = async (id: string): Promise<MCPServer | null> => {
  const data = await apiRequest<MCPServer>("GET", `${BASE}/${id}`);
  return data ?? null;
};

export const createMCPServer = async (
  serverData: MCPServerCreatePayload
): Promise<MCPServer> => {
  const response = await apiRequest<MCPServer>(
    "POST",
    `${BASE}`,
    serverData as unknown as Record<string, unknown>
  );
  if (!response) throw new Error("Failed to create MCP server");
  return response;
};

export const updateMCPServer = async (
  id: string,
  serverData: MCPServerUpdatePayload
): Promise<MCPServer> => {
  const response = await apiRequest<MCPServer>(
    "PUT",
    `${BASE}/${id}`,
    serverData as unknown as Record<string, unknown>
  );
  if (!response) throw new Error("Failed to update MCP server");
  return response;
};

export const deleteMCPServer = async (id: string): Promise<void> => {
  await apiRequest("DELETE", `${BASE}/${id}`);
};

