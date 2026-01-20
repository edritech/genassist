import { apiRequest } from "@/config/api";
import { AppSetting } from "@/interfaces/app-setting.interface";
import { DynamicFormSchema } from "@/interfaces/dynamicFormSchemas.interface";

export const getAllAppSettings = async (): Promise<AppSetting[]> => {
  const data = await apiRequest<AppSetting[]>("GET", "app-settings/");
  if (!data) {
    return [];
  }

  if (!Array.isArray(data)) {
    return [];
  }

  return data;
};

export const getAppSetting = async (id: string): Promise<AppSetting | null> => {
  const data = await apiRequest<AppSetting>("GET", `app-settings/${id}`);
  if (!data) {
    return null;
  }
  return data;
};

export const createAppSetting = async (appSettingData: Partial<AppSetting>): Promise<AppSetting> => {
  const requestData = {
    name: appSettingData.name,
    type: appSettingData.type,
    values: appSettingData.values,
    description: appSettingData.description,
    is_active: appSettingData.is_active,
  };

  const response = await apiRequest<AppSetting>("POST", "app-settings", requestData);
  if (!response) throw new Error("Failed to create app setting");
  return response;
};

export const updateAppSetting = async (id: string, appSettingData: Partial<AppSetting>): Promise<AppSetting> => {
  const requestData: Record<string, unknown> = {};

  if (appSettingData.name !== undefined) requestData.name = appSettingData.name;
  if (appSettingData.type !== undefined) requestData.type = appSettingData.type;
  if (appSettingData.values !== undefined) requestData.values = appSettingData.values;
  if (appSettingData.description !== undefined) requestData.description = appSettingData.description;
  if (appSettingData.is_active !== undefined) requestData.is_active = appSettingData.is_active;

  const response = await apiRequest<AppSetting>("PATCH", `app-settings/${id}`, requestData);
  if (!response) {
    throw new Error("Failed to update app setting");
  }
  return response;
};

export const deleteAppSetting = async (id: string): Promise<void> => {
  await apiRequest("DELETE", `app-settings/${id}`);
};

export const getAppSettingsFormSchemas = async (): Promise<DynamicFormSchema> => {
  return await apiRequest<DynamicFormSchema>("GET", "/app-settings/form_schemas");
};
