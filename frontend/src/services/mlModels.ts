import { apiRequest, getApiUrl } from "@/config/api";
import { MLModel, MLModelFormData } from "@/interfaces/ml-model.interface";

const BASE = "ml-models";

export const getAllMLModels = async (): Promise<MLModel[]> => {
  const data = await apiRequest<MLModel[]>("GET", `${BASE}`);
  if (!data || !Array.isArray(data)) {
    return [];
  }
  return data;
};

export const getMLModel = async (id: string): Promise<MLModel | null> => {
  const data = await apiRequest<MLModel>("GET", `${BASE}/${id}`);
  return data ?? null;
};

export const createMLModel = async (
  modelData: MLModelFormData
): Promise<MLModel> => {
  const response = await apiRequest<MLModel>("POST", `${BASE}`, modelData as unknown as Record<string, unknown>);
  if (!response) throw new Error("Failed to create ML model");
  return response;
};

export const updateMLModel = async (
  id: string,
  modelData: Partial<MLModelFormData>
): Promise<MLModel> => {
  const response = await apiRequest<MLModel>("PUT", `${BASE}/${id}`, modelData as unknown as Record<string, unknown>);
  if (!response) throw new Error("Failed to update ML model");
  return response;
};

export const deleteMLModel = async (id: string): Promise<void> => {
  await apiRequest("DELETE", `${BASE}/${id}`);
};

export const uploadModelFile = async (file: File): Promise<{ file_path: string; original_filename: string }> => {
  const formData = new FormData();
  formData.append("file", file);

  const baseURL = await getApiUrl();
  const token = localStorage.getItem("access_token");
  const tokenType = localStorage.getItem("token_type");

  const headers: Record<string, string> = {};

  if (token && tokenType) {
    headers["Authorization"] = `${tokenType} ${token}`;
  }

  const response = await fetch(`${baseURL}${BASE}/upload`, {
    method: "POST",
    body: formData,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API error: ${response.status}`);
  }

  const data = await response.json();
  return data;
};

export interface CSVAnalysisResult {
  row_count: number;
  column_count: number;
  column_names: string[];
  sample_data: Record<string, unknown>[];
  columns_info: Array<{
    name: string;
    dtype: string;
    missing_count: number;
    type: "categorical" | "numeric";
    unique_count: number;
    category_count?: number;
    min?: number | null;
    max?: number | null;
  }>;
}

export const analyzeCSV = async (fileUrl: string, pythonCode?: string): Promise<CSVAnalysisResult> => {
  const body: { file_url: string; python_code?: string } = { file_url: fileUrl };
  if (pythonCode) {
    body.python_code = pythonCode;
  }
  const response = await apiRequest<CSVAnalysisResult>(
    "POST",
    `${BASE}/analyze-csv`,
    body
  );
  if (!response) throw new Error("Failed to analyze CSV");
  return response;
};

