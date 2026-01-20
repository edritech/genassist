import { apiRequest } from "@/config/api";
import { Role } from "@/interfaces/role.interface";
import { User } from "@/interfaces/user.interface";
import { UserType } from "@/interfaces/userType.interface";

export const getAllUsers = async (): Promise<User[]> => {
  const data = await apiRequest<User[]>("GET", "user/");
  return data || [];
};

export const getUser = async (id: string): Promise<User | null> => {
  return await apiRequest<User>("GET", `user/${id}`);
};

export const createUser = async (userData: User): Promise<User> => {
  const requestData = {
    username: userData.username,
    email: userData.email,
    password: userData.password,
    is_active: userData.is_active,
    user_type_id: userData.user_type_id,
    role_ids: userData.role_ids
  };

  const response = await apiRequest<User>("POST", "user", requestData);
  if (!response) throw new Error("Failed to create user");
  return response;
};

export const updateUser = async (id: string, userData: Partial<User>): Promise<User> => {
  const response = await apiRequest<User>("PUT", `user/${id}`, userData);
  if (!response) throw new Error("Failed to update user");
  return response;
};
