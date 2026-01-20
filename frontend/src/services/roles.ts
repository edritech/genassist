import { apiRequest } from "@/config/api";
import { Role } from "@/interfaces/role.interface";

export const getAllRoles = async (): Promise<Role[]> => {
  const data = await apiRequest<Role[]>("GET", "roles/");
  return data || [];
};

export const getRole = async (id: string): Promise<Role | null> => {
  return await apiRequest<Role>("GET", `roles/${id}`);
};

export const createRole = async (roleData: Partial<Role>): Promise<Role> => {
  const response = await apiRequest<Role>("POST", "roles", roleData);
  if (!response) throw new Error("Failed to create role");
  return response;
};

export const deleteRole = async (id: string): Promise<void> => {
  await apiRequest("DELETE", `roles/${id}`);
};

export const updateRole = async (id: string, roleData: Partial<Role>): Promise<Role> => {
  const response = await apiRequest<Role>("PATCH", `roles/${id}`, roleData);
  if (!response) throw new Error("Failed to update role");
  return response;
};
