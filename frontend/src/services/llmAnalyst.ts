import { apiRequest } from "@/config/api";
import { LLMAnalyst, LLMProvider } from "@/interfaces/llmAnalyst.interface";

export const getAllLLMAnalysts = async (): Promise<LLMAnalyst[]> => {
  return await apiRequest<LLMAnalyst[]>("GET", "llm-analyst/");
};

export const getLLMAnalyst = async (id: string): Promise<LLMAnalyst | null> => {
  return await apiRequest<LLMAnalyst>("GET", `llm-analyst/${id}`);
};

export const createLLMAnalyst = async (
  llmAnalystData: LLMAnalyst
): Promise<LLMAnalyst> => {
  const response = await apiRequest<LLMAnalyst>(
    "POST",
    "llm-analyst",
    JSON.parse(JSON.stringify(llmAnalystData))
  );
  return response;
};

export const updateLLMAnalyst = async (
  id: string,
  llmAnalystData: Partial<LLMAnalyst>
): Promise<LLMAnalyst> => {
  const response = await apiRequest<LLMAnalyst>(
    "PATCH",
    `llm-analyst/${id}`,
    JSON.parse(JSON.stringify(llmAnalystData))
  );
  return response;
};

export const deleteLLMAnalyst = async (id: string): Promise<void> => {
  await apiRequest<void>("DELETE", `llm-analyst/${id}`);
};

export const getAllLLMProviders = async (): Promise<LLMProvider[]> => {
  const response = await apiRequest<LLMProvider[]>("GET", "llm-providers/");
  return response;
};
