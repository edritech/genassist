import { apiRequest } from "@/config/api";
import { UserType } from "@/interfaces/userType.interface";

export const getAllUserTypes = async (): Promise<UserType[]> => {
  const data = await apiRequest<UserType[]>("GET", "user-type/");
  return data || [];
};

export const getUserType = async (id: string): Promise<UserType | null> => {
  return await apiRequest<UserType>("GET", `user-type/${id}`);
};

export const createUserType = async (userTypeData: Partial<UserType>): Promise<UserType> => {
  const response = await apiRequest<UserType>("POST", "user-type", userTypeData);
  if (!response) throw new Error("Failed to create user type");
  return response;
};

export const deleteUserType = async (id: string): Promise<void> => {
  await apiRequest("DELETE", `user-type/${id}`);
};

export const updateUserType = async (id: string, userTypeData: Partial<UserType>): Promise<UserType> => {
  const response = await apiRequest<UserType>("PATCH", `user-type/${id}`, userTypeData);
  if (!response) throw new Error("Failed to update user type");
  return response;
};
