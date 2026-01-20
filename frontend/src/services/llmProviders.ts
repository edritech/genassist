import { apiRequest } from "@/config/api";
import { LLMProvider } from "@/interfaces/llmProvider.interface";
import { DynamicFormSchema } from "@/interfaces/dynamicFormSchemas.interface";

export const getAllLLMProviders = async (): Promise<LLMProvider[]> => {
  return await apiRequest<LLMProvider[]>("GET", "llm-providers/");
};

export const getLLMProvider = async (
  id: string
): Promise<LLMProvider | null> => {
  return await apiRequest<LLMProvider>("GET", `llm-providers/${id}`);
};

export const createLLMProvider = async (
  providerData: Omit<LLMProvider, "id" | "created_at" | "updated_at">
): Promise<LLMProvider> => {
  return await apiRequest<LLMProvider>(
    "POST",
    "llm-providers",
    JSON.parse(JSON.stringify(providerData))
  );
};

export const updateLLMProvider = async (
  id: string,
  providerData: Partial<Omit<LLMProvider, "id" | "created_at" | "updated_at">>
): Promise<LLMProvider> => {
  return await apiRequest<LLMProvider>(
    "PATCH",
    `llm-providers/${id}`,
    JSON.parse(JSON.stringify(providerData))
  );
};

export const deleteLLMProvider = async (id: string): Promise<void> => {
  await apiRequest<void>("DELETE", `llm-providers/${id}`);
};

export async function getLLMProvidersFormSchemas(): Promise<DynamicFormSchema> {
  return apiRequest<DynamicFormSchema>("GET", "llm-providers/form_schemas");
}
